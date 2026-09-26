from time import monotonic
from uuid import UUID

from app.common.exceptions import InvalidCallbackURLError
from app.repositories.interfaces.callback_repository import CallbackAttemptResult, CallbackRepository
from app.services.interfaces.callback_security_service import CallbackSecurityService
from app.services.interfaces.callback_service import CallbackDeliveryAction, CallbackDeliveryDecision, CallbackService
from app.utils.http_api_client import HTTPAPIClient


class DefaultCallbackService(CallbackService):
    def __init__(
        self,
        repository: CallbackRepository,
        security: CallbackSecurityService,
        http_client: HTTPAPIClient,
        max_attempts: int,
        retry_delays_seconds: list[int],
    ) -> None:
        self._repository = repository
        self._security = security
        self._http = http_client
        self._max_attempts = max_attempts
        self._retry_delays = retry_delays_seconds

    async def deliver(self, request_id: UUID) -> CallbackDeliveryDecision:
        claimed = await self._repository.claim(request_id)
        if claimed is None:
            return CallbackDeliveryDecision(CallbackDeliveryAction.COMPLETE, 0)
        request, attempt = claimed
        if request.callback_url is None:
            await self._repository.mark_dead_lettered(request_id)
            return CallbackDeliveryDecision(CallbackDeliveryAction.DEAD_LETTER, attempt)

        started = monotonic()
        status: int | None = None
        error: str | None = None
        try:
            await self._security.validate_destination(request.callback_url)
            plan = None
            if request.plan:
                plan = {
                    "stops": [
                        {
                            "position": stop.position, "venue_id": str(stop.venue_id), "name": stop.name,
                            "area": stop.area, "estimated_cost_inr": stop.estimated_cost_inr,
                        }
                        for stop in request.plan.stops
                    ],
                    "total_cost_inr": request.plan.total_cost_inr,
                    "leftover_budget_inr": request.plan.leftover_budget_inr,
                }
            payload = {
                "id": str(request.id), "status": request.status.value, "plan": plan,
                "failed_constraint": request.failed_constraint.value if request.failed_constraint else None,
                "error_code": request.error_code,
                "completed_at": request.completed_at.isoformat() if request.completed_at else None,
            }
            response = await self._http.post(
                request.callback_url, payload,
                {"X-Request-ID": str(request.id), "X-Callback-Attempt": str(attempt)},
            )
            status = response.status_code
            delivered = 200 <= status < 300
            retryable = status in {408, 429} or status >= 500
        except InvalidCallbackURLError as exc:
            delivered = False
            retryable = False
            error = type(exc).__name__
        except Exception as exc:
            delivered = False
            retryable = True
            error = type(exc).__name__

        exhausted = retryable and attempt >= self._max_attempts
        retry_delay = None
        if retryable and not exhausted:
            retry_delay = self._retry_delays[attempt - 1]
        result = CallbackAttemptResult(
            delivered=delivered, retryable=retryable, http_status=status,
            error_category=error, duration_ms=int((monotonic() - started) * 1000),
            exhausted=exhausted, next_retry_delay_seconds=retry_delay,
        )
        await self._repository.save_result(request_id, attempt, result)
        if exhausted:
            return CallbackDeliveryDecision(CallbackDeliveryAction.DEAD_LETTER, attempt)
        if retryable:
            return CallbackDeliveryDecision(CallbackDeliveryAction.RETRY, attempt)
        return CallbackDeliveryDecision(CallbackDeliveryAction.COMPLETE, attempt)

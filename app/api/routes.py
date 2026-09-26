from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.api.schemas import (
    AsyncAcceptedResponse, AsyncPlanningRequest, HealthResponse, PlanResponse, PlanStopResponse,
    PlanningRequest, RequestListResponse, RequestResponse,
)
from app.common.entities import RequestRecord
from app.common.enums import PlanningStatus, RequestMode
from app.container import ApplicationContainer

router = APIRouter()


def _container(request: Request) -> ApplicationContainer:
    return request.app.state.container


def _response(record: RequestRecord) -> RequestResponse:
    plan = None
    if record.plan:
        plan = PlanResponse(
            stops=[
                PlanStopResponse(
                    position=stop.position, venue_id=stop.venue_id, name=stop.name,
                    area=stop.area, estimated_cost_inr=stop.estimated_cost_inr,
                )
                for stop in record.plan.stops
            ],
            total_cost_inr=record.plan.total_cost_inr,
            leftover_budget_inr=record.plan.leftover_budget_inr,
        )
    return RequestResponse(
        id=record.id, mode=record.mode, status=record.status,
        callback_status=record.callback_status, plan=plan,
        failed_constraint=record.failed_constraint, error_code=record.error_code,
        created_at=record.created_at, completed_at=record.completed_at,
    )


@router.post("/sync", response_model=RequestResponse)
async def create_sync(body: PlanningRequest, request: Request):
    record = await _container(request).request_handler.handle_sync(body)
    response = _response(record)
    if record.status == PlanningStatus.FAILED:
        return JSONResponse(status_code=422, content=response.model_dump(mode="json"))
    return response


@router.post("/async", response_model=AsyncAcceptedResponse, status_code=202)
async def create_async(body: AsyncPlanningRequest, request: Request) -> AsyncAcceptedResponse:
    record = await _container(request).request_handler.handle_async(body)
    return AsyncAcceptedResponse(
        id=record.id, status_url=f"/requests/{record.id}",
        created_at=record.created_at or datetime.now(UTC),
    )


@router.get("/requests/{request_id}", response_model=RequestResponse)
async def get_request(request_id: UUID, request: Request) -> RequestResponse:
    return _response(await _container(request).request_handler.get(request_id))


@router.get("/requests", response_model=RequestListResponse)
async def list_requests(
    request: Request,
    mode: RequestMode,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
) -> RequestListResponse:
    records, next_cursor = await _container(request).request_handler.list(mode, limit, cursor)
    return RequestListResponse(items=[_response(record) for record in records], next_cursor=next_cursor)


@router.get("/healthz", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    return HealthResponse.model_validate(await _container(request).health_handler.check())

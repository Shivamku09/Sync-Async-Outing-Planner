from uuid import UUID

from app.common.entities import Plan, PlanningInput, PlanningOutcome, PlanStop, RequestRecord, Venue
from app.common.enums import FailedConstraint
from app.repositories.interfaces.request_repository import RequestRepository
from app.repositories.interfaces.venue_repository import VenueRepository
from app.services.interfaces.planner_service import PlannerService


class DefaultPlannerService(PlannerService):
    def __init__(self, venue_repository: VenueRepository, request_repository: RequestRepository) -> None:
        self._venues = venue_repository
        self._requests = request_repository

    async def plan(self, planning_input: PlanningInput) -> PlanningOutcome:
        venues = await self._venues.list_active()
        if not venues:
            return PlanningOutcome(failed_constraint=FailedConstraint.LOCATION)

        day_type = "weekend" if planning_input.outing_date.weekday() >= 5 else "weekday"
        by_date = [venue for venue in venues if "all" in venue.open_days or day_type in venue.open_days]
        if not by_date:
            return PlanningOutcome(failed_constraint=FailedConstraint.DATE)

        by_group = [venue for venue in by_date if venue.capacity >= planning_input.group_size]
        if not by_group:
            return PlanningOutcome(failed_constraint=FailedConstraint.GROUP_SIZE)

        by_age = [
            venue for venue in by_group
            if venue.min_age <= planning_input.age_min and venue.max_age >= planning_input.age_max
        ]
        if not by_age:
            return PlanningOutcome(failed_constraint=FailedConstraint.AGE)

        requested_tags = set(planning_input.preferences)

        def rank(venue: Venue) -> tuple[int, int, str]:
            return (-len(requested_tags.intersection(venue.tags)), -(venue.area.lower() == planning_input.location.lower()), str(venue.id))

        remaining = planning_input.budget_inr
        selected: list[Venue] = []
        for venue in sorted(by_age, key=rank):
            if venue.estimated_cost_inr <= remaining:
                selected.append(venue)
                remaining -= venue.estimated_cost_inr
            if len(selected) == 3:
                break
        if not selected:
            return PlanningOutcome(failed_constraint=FailedConstraint.BUDGET)

        stops = tuple(
            PlanStop(index, venue.id, venue.name, venue.area, venue.estimated_cost_inr)
            for index, venue in enumerate(selected, start=1)
        )
        return PlanningOutcome(plan=Plan(stops, planning_input.budget_inr - remaining, remaining))

    async def process_async_request(self, request_id: UUID) -> RequestRecord | None:
        request = await self._requests.claim_for_planning(request_id)
        if request is None:
            return None
        outcome = await self.plan(request.planning_input)
        return await self._requests.complete(request.id, outcome, create_callback_event=True)

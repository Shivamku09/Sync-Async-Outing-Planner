from uuid import UUID

from app.common.entities import Plan, PlanningInput, PlanStop, RequestRecord, Venue
from app.common.enums import FailedConstraint
from app.repositories.postgres.models import RequestRow, VenueRow


def venue_entity(row: VenueRow) -> Venue:
    return Venue(
        id=row.id, name=row.name, area=row.area, tags=frozenset(row.tags),
        estimated_cost_inr=row.estimated_cost_inr, capacity=row.capacity,
        min_age=row.min_age, max_age=row.max_age, open_days=frozenset(row.open_days),
    )


def plan_to_json(plan: Plan) -> dict[str, object]:
    return {
        "stops": [
            {
                "position": stop.position, "venue_id": str(stop.venue_id), "name": stop.name,
                "area": stop.area, "estimated_cost_inr": stop.estimated_cost_inr,
            }
            for stop in plan.stops
        ],
        "total_cost_inr": plan.total_cost_inr,
        "leftover_budget_inr": plan.leftover_budget_inr,
    }


def plan_entity(value: dict[str, object] | None) -> Plan | None:
    if not value:
        return None
    stops = tuple(
        PlanStop(
            position=int(item["position"]), venue_id=UUID(str(item["venue_id"])),
            name=str(item["name"]), area=str(item["area"]),
            estimated_cost_inr=int(item["estimated_cost_inr"]),
        )
        for item in value.get("stops", [])  # type: ignore[union-attr]
    )
    return Plan(
        stops=stops, total_cost_inr=int(value["total_cost_inr"]),
        leftover_budget_inr=int(value["leftover_budget_inr"]),
    )


def request_entity(row: RequestRow) -> RequestRecord:
    return RequestRecord(
        id=row.id, mode=row.mode, status=row.status,
        planning_input=PlanningInput(
            location=row.location_area, outing_date=row.outing_date, group_size=row.group_size,
            age_min=row.age_min, age_max=row.age_max, budget_inr=row.budget_inr,
            preferences=tuple(row.preferences),
        ),
        callback_status=row.callback_status, callback_url=row.callback_url,
        plan=plan_entity(row.result),
        failed_constraint=FailedConstraint(row.failed_constraint) if row.failed_constraint else None,
        error_code=row.error_code, created_at=row.created_at, started_at=row.started_at,
        completed_at=row.completed_at, updated_at=row.updated_at,
    )

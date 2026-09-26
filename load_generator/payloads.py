from datetime import date, timedelta


def planning_payload() -> dict[str, object]:
    target = date.today() + timedelta(days=7)
    return {
        "location": "Central Bengaluru",
        "outing_date": target.isoformat(),
        "group_size": 4,
        "age_min": 20,
        "age_max": 35,
        "budget_inr": 4000,
        "preferences": ["nature", "museum"],
    }

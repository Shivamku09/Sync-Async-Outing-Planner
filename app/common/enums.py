from enum import StrEnum


class RequestMode(StrEnum):
    SYNC = "sync"
    ASYNC = "async"


class PlanningStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class CallbackStatus(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    PENDING = "pending"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
    FAILED = "failed"
    DEAD_LETTERED = "dead_lettered"


class FailedConstraint(StrEnum):
    LOCATION = "location"
    DATE = "date"
    GROUP_SIZE = "group_size"
    AGE = "age"
    BUDGET = "budget"


class OutboxEventType(StrEnum):
    PLAN_REQUESTED = "PLAN_REQUESTED"
    CALLBACK_REQUESTED = "CALLBACK_REQUESTED"


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PUBLISHING = "publishing"
    PUBLISHED = "published"

class ApplicationError(Exception):
    code = "APPLICATION_ERROR"


class RequestNotFoundError(ApplicationError):
    code = "REQUEST_NOT_FOUND"


class InvalidCallbackURLError(ApplicationError):
    code = "INVALID_CALLBACK_URL"


class AsyncBacklogExceededError(ApplicationError):
    code = "ASYNC_BACKLOG_EXCEEDED"


class RepositoryUnavailableError(ApplicationError):
    code = "REPOSITORY_UNAVAILABLE"


class PlanningConstraintError(ApplicationError):
    code = "NO_FEASIBLE_PLAN"

    def __init__(self, request_record: object) -> None:
        super().__init__(self.code)
        self.request_record = request_record

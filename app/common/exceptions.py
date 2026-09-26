class ApplicationError(Exception):
    code = "APPLICATION_ERROR"


class RequestNotFoundError(ApplicationError):
    code = "REQUEST_NOT_FOUND"


class InvalidCallbackURLError(ApplicationError):
    code = "INVALID_CALLBACK_URL"


class AsyncBacklogExceededError(ApplicationError):
    code = "ASYNC_BACKLOG_EXCEEDED"

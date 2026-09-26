class RetryMessageError(Exception):
    def __init__(self, attempt: int) -> None:
        super().__init__(f"message requires retry after attempt {attempt}")
        self.attempt = attempt


class DeadLetterMessageError(Exception):
    pass

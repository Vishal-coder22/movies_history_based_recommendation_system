class UserError(Exception):
    """An input problem the user can fix; rendered as a friendly API error."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

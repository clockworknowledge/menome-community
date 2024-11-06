# backend/exceptions/database_exceptions.py

from fastapi import HTTPException, status

class DatabaseConnectionError(HTTPException):
    def __init__(self, detail: str = "Database connection failed."):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )

class UserNotFoundError(HTTPException):
    def __init__(self, detail: str = "User not found."):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )

class InvalidRoleAssignmentError(Exception):
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(self.detail)
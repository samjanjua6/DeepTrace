"""Auth exceptions."""
from fastapi import HTTPException, status


class InvalidCredentialsError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Email or password is incorrect."},
        )


class AccountLockedError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_423_LOCKED,
            detail={
                "code": "ACCOUNT_LOCKED",
                "message": "Account is temporarily locked after too many failed login attempts.",
            },
        )


class TokenExpiredError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED", "message": "Authentication token has expired."},
        )


class InsufficientPermissionsError(HTTPException):
    def __init__(self, required_role: str = ""):
        detail = {
            "code": "FORBIDDEN",
            "message": (
                f"Insufficient permissions. Required role: {required_role}"
                if required_role
                else "Insufficient permissions."
            ),
        }
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class InvalidMfaCodeError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_MFA_CODE", "message": "Invalid or expired two-factor authentication code."},
        )


class InvalidRefreshTokenError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_REFRESH_TOKEN", "message": "Refresh token is invalid, expired, or revoked."},
        )


class SessionBreachDetectedError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "SESSION_BREACH_DETECTED",
                "message": "Token reuse attempt detected. All active sessions have been terminated under SBP security regulations.",
            },
        )


class OrganizationNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ORGANIZATION_NOT_FOUND", "message": "The specified banking organization was not found."},
        )

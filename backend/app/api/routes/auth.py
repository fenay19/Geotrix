from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ...core.security import create_access_token
from ...services.user_service import user_service
from ...schemas.user_schema import User, UserCreate, ForgotPasswordRequest
from ...dependencies import get_db, get_current_user
from ...config import settings

router = APIRouter()


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.
    - Accepts email and password in the request body.
    - Returns the created user object (without password).
    - Raises 400 if the email is already registered.
    """
    existing = user_service.get_user_by_email(db, email=user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )
    new_user = user_service.create_user(db, user_in=user_in)
    return new_user


@router.post("/login")
def login_for_access_token(
    response: Response,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Login with email and password.
    - Sets a secure HttpOnly JWT access token cookie.
    - Returns a bearer fallback token in the JSON body.
    - Raises 401 for invalid credentials.
    """
    user = user_service.authenticate(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    
    # Set secure HttpOnly cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=not settings.DEBUG,  # True in prod, False in local dev (HTTP)
        samesite="lax",
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
def logout(response: Response):
    """
    Clears the HttpOnly access token cookie.
    """
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
    )
    return {"status": "success", "message": "Successfully logged out"}


@router.get("/me", response_model=User)
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Returns the currently authenticated user's profile details.
    Requires a valid access token cookie or Bearer token in the Authorization header.
    """
    return current_user


@router.post("/forgot-password")
def forgot_password(
    request_in: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Initiate password reset.
    - Always returns a success message to prevent email enumeration.
    """
    user = user_service.get_user_by_email(db, email=request_in.email)
    if user:
        import logging
        auth_logger = logging.getLogger("geotrade.auth")
        auth_logger.info("[AUTH] Password reset link requested for user: %s", request_in.email)
    return {"status": "success", "message": "If an account is registered with this email, a reset link has been sent."}


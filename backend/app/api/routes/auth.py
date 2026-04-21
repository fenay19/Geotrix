from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ...core.security import create_access_token
from ...services.user_service import user_service
from ...schemas.user_schema import User, UserCreate
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
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Login with email and password.
    - Returns a Bearer JWT access token on success.
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
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=User)
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Returns the currently authenticated user's profile details.
    Requires a valid Bearer token in the Authorization header.
    """
    return current_user

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ...schemas.user_schema import User, UserCreate, UserUpdate
from ...services.user_service import user_service
from ...dependencies import get_db, get_current_user, require_admin

router = APIRouter()


def _require_self_or_admin(user_id: int, current_user: User) -> None:
    """Raises 403 unless the caller owns the account or is a superuser."""
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this account.",
        )


@router.get("/", response_model=List[User])
def get_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return user_service.get_users(db, skip=skip, limit=limit)


@router.post("/", response_model=User, status_code=201)
def create_user(user_in: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Admin-only: creates a new user account. Use POST /auth/register for self-registration."""
    db_user = user_service.get_user_by_email(db, email=user_in.email)
    if db_user:
        raise HTTPException(status_code=400, detail="The user with this email already exists.")
    return user_service.create_user(db, user_in)


@router.get("/{user_id}", response_model=User)
def get_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_user = user_service.get_user_by_id(db, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.put("/{user_id}", response_model=User)
def update_user(user_id: int, user_in: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_self_or_admin(user_id, current_user)
    db_user = user_service.update_user(db, user_id=user_id, user_in=user_in)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_self_or_admin(user_id, current_user)
    db_user = user_service.delete_user(db, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return None


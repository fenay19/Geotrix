from sqlalchemy.orm import Session
from typing import List, Optional
from ..repositories.user_repo import UserRepository
from ..schemas.user_schema import UserCreate, UserUpdate
from ..core.security import get_password_hash, verify_password


class UserService:
    def get_users(self, db: Session, skip: int = 0, limit: int = 100):
        repo = UserRepository(db)
        return repo.get_multi(skip=skip, limit=limit)

    def get_user_by_id(self, db: Session, user_id: int):
        repo = UserRepository(db)
        return repo.get_by_id(user_id)

    def get_user_by_email(self, db: Session, email: str):
        repo = UserRepository(db)
        return repo.get_by_email(email)

    def create_user(self, db: Session, user_in: UserCreate):
        repo = UserRepository(db)
        hashed_password = get_password_hash(user_in.password)
        return repo.create(user_in, hashed_password=hashed_password)

    def authenticate(self, db: Session, email: str, password: str):
        user = self.get_user_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def update_user(self, db: Session, user_id: int, user_in: UserUpdate):
        repo = UserRepository(db)
        db_obj = repo.get_by_id(user_id)
        if db_obj:
            return repo.update(db_obj, user_in)
        return None

    def delete_user(self, db: Session, user_id: int):
        repo = UserRepository(db)
        return repo.delete(user_id)


user_service = UserService()

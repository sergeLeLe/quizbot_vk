from dataclasses import dataclass
from hashlib import sha256
from typing import Optional

from app.store.database.gino import db


@dataclass
class Admin:
    id: int
    email: str
    password: Optional[str] = None

    def is_password_valid(self, password: str):
        return self.password == sha256(password.encode()).hexdigest()

    @classmethod
    def from_session(cls, session: Optional[dict]) -> Optional["Admin"]:
        return cls(id=session["admin"]["id"], email=session["admin"]["email"])


# TODO
# Дописать все необходимые поля модели
class AdminModel(db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer(), nullable=False, primary_key=True)
    email = db.Column(db.Unicode(), nullable=False)
    password = db.Column(db.String(100), nullable=False)

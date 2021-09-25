from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB

from app.quiz.models import Theme, Question
from app.store.database.gino import db


@dataclass
class Games:
    id: int
    chat_id: int
    started_at: datetime
    finished_at: datetime
    is_active: bool
    theme_id: Theme
    used_questions: List[Question]


@dataclass
class Users:
    id: int
    first_name: str
    last_name: str


class Score:
    game_id: int
    user_id: int
    count_score: int


class GamesModel(db.Model):
    __tablename__ = "games"

    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    chat_id = db.Column(db.Integer(), nullabe=False)
    started_at = db.Column(db.Datetime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = db.Column(db.Datetime(timezone=True), nullable=False)
    is_active = db.Column(db.Boolean, unique=False, default=True)
    theme_id = db.Column(db.Integer(), db.ForeignKey("themes.id", ondelete="SET NULL"), nullable=False)

    profile = db.Column(JSONB, nullable=False, server_default="{}")
    used_questions = db.ArrayProperty(prop_name="profile")
    # duration

    def __init__(self, **kw):
        super().__init__(**kw)
        self._users = list()

    @property
    def users(self):
        return self._users

    @users.setter
    def users(self, val: Optional[Users]):
        if val:
            self._users.append(val)


class UsersModel(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer(), primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)

    def __init__(self, **kw):
        super().__init__(**kw)
        self._games = list()

    @property
    def games(self):
        return self._games

    @games.setter
    def games(self, val: Optional[Games]):
        if val:
            self._games.append(val)


class ScoreModel(db.Model):
    __tablename__ = "score"

    game_id = db.Column(db.Integer, db.ForeignKey('games.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    count_score = db.Column(db.Integer(), nullabe=False)
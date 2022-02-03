from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB

from app.quiz.models import Theme, Question
from app.store.database.gino import db


@dataclass
class Users:
    id: int
    first_name: str
    last_name: str


@dataclass
class Score:
    game_id: int
    user_id: int
    count_score: int
    #state_answer: bool


@dataclass
class UserWithScore:
    score: Score
    user: Users


@dataclass
class Games:
    id: int
    chat_id: int
    started_at: datetime
    finished_at: Optional[datetime]
    is_active: bool
    state_round: bool
    theme_id: Theme
    used_questions: List[int]
    round_answers: Optional[List[int]]
    users: List[UserWithScore]
    questions: List[Question]


class GamesModel(db.Model):
    __tablename__ = "games"

    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    chat_id = db.Column(db.Integer(), nullable=False)  # возможно уникальным стоит сделать
    started_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = db.Column(db.DateTime(timezone=True), nullable=True)
    is_active = db.Column(db.Boolean, unique=False, default=False)
    theme_id = db.Column(db.Integer(), db.ForeignKey("themes.id", ondelete="SET NULL"), nullable=False)
    state_round = db.Column(db.Boolean, unique=False, default=False)

    profile = db.Column(JSONB, nullable=False, server_default="{}")
    used_questions = db.ArrayProperty(prop_name="profile")
    round_answers = db.ArrayProperty(prop_name="profile")

    def __init__(self, **kw):
        super().__init__(**kw)
        self._users = list()
        self._scores = list()

    @property
    def users(self):
        return self._users

    @users.setter
    def users(self, val: Optional[Users]):
        self._users.append(val)

    @property
    def scores(self):
        return self._scores

    @scores.setter
    def scores(self, val: Optional[Score]):
        self._scores.append(val)


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
        self._games.append(val)


class ScoreModel(db.Model):
    __tablename__ = "score"

    game_id = db.Column(db.Integer, nullable=False, primary_key=True)
    user_id = db.Column(db.Integer,nullable=False, primary_key=True)
    count_score = db.Column(db.Integer(), nullable=False)
    #state_answer = db.Column(db.Boolean, unique=False, default=False)

    game_fk = db.ForeignKeyConstraint(
        ["game_id"], ["games.id"]
    )

    user_fk = db.ForeignKeyConstraint(
        ["user_id"], ["users.id"]
    )
from dataclasses import dataclass
from typing import Optional, List

from app.store.database.gino import db


@dataclass
class Theme:
    id: Optional[int]
    title: str



class ThemeModel(db.Model):
    __tablename__ = "themes"

    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), unique=True, nullable=False)


@dataclass
class Answer:
    title: str
    is_correct: bool


@dataclass
class Question:
    id: Optional[int]
    title: str
    theme_id: int
    answers: list["Answer"]


class AnswerModel(db.Model):
    __tablename__ = "answers"

    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), nullable=False)
    is_correct = db.Column(db.Boolean(), nullable=False)
    question_id = db.Column(
        db.ForeignKey('questions.id', ondelete="CASCADE"), nullable=False
    )


class QuestionModel(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), unique=True, nullable=False)
    theme_id = db.Column(db.Integer(), db.ForeignKey('themes.id', ondelete="CASCADE"), nullable=False)

    def __init__(self, **kw):
        super().__init__(**kw)
        self._answers: List[AnswerModel] = list()

    @property
    def answers(self) -> List[AnswerModel]:
        return self._answers

    @answers.setter
    def answers(self, val: Optional[AnswerModel]):
        self._answers.append(val)




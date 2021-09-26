from datetime import datetime
from typing import Optional

from sqlalchemy import func

from app.base.base_accessor import BaseAccessor
from app.game.models import (
    Games,
    Users,
    Score,
    GamesModel,
    ScoreModel,
    UsersModel
)
from app.quiz.models import Question


class GameAccessor(BaseAccessor):
    async def create_user(self, id_: int, fn: str, ln: str) -> Users:
        user = await UsersModel.create(id=id_, first_name=fn, last_name=ln)
        return Users(id=user.id, first_name=user.first_name, last_name=user.last_name)

    async def create_game(self, chat_id: int, theme_id: int) -> Games:
        game = await GamesModel.create(chat_id=chat_id, theme_id=theme_id, used_questions=[])
        return Games(
            id=game.id,
            chat_id=game.chat_id,
            started_at=game.started_at,
            finished_at=None,
            is_active=game.is_active,
            theme_id=game.theme_id,
            used_questions=game.used_questions
        )

    async def get_game_by_chat_id(self, chat_id:int) -> Optional[Games]:
        game = await GamesModel.query.where(GamesModel.chat_id == chat_id).gino.first()
        return Games(
            id=game.id,
            chat_id=game.chat_id,
            started_at=game.started_at,
            finished_at=None,
            is_active=game.is_active,
            theme_id=game.theme_id,
            used_questions=game.used_questions
        )if game else None

    async def get_last_game(self) -> Optional[Games]:
        game = await GamesModel.query.order_by(GamesModel.finished_at.desc()).gino.first()
        return Games(
            id=game.id,
            chat_id=game.chat_id,
            started_at=game.started_at,
            finished_at=game.finished_at,
            is_active=game.is_active,
            theme_id=game.theme_id,
            used_questions=game.used_questions
        ) if game else None

    async def get_winner(self, chat_id: int) -> Optional[Users]:
        game = await self.get_game_by_chat_id(chat_id=chat_id)
        scores = await self.get_scores_by_game(game_id=game.id)
        user = scores[0]
        for score in scores:
            if score.count_score > user.count_score:
                user = score
        return user

    async def end_game(self, chat_id: int) -> None:
        game = await GamesModel.query.where(GamesModel.chat_id == chat_id).gino.first()
        await game.update(is_active=False).apply()

    async def add_finish(self, chat_id: int, time: datetime) -> None:
        game = await GamesModel.query.where(GamesModel.chat_id == chat_id).gino.first()
        await game.update(finished_at=time).apply()

    async def add_used_questions(self, chat_id: int, questions: list[Question]) -> None:
        questions_list = []
        for question in questions:
            questions_list.append(question.id)
        game = await GamesModel.query.where(GamesModel.chat_id == chat_id).gino.first()
        await game.update(used_questions=questions_list).apply()

    async def create_score(self, game_id: int, user_id: int, count: int) -> Score:
        score = await ScoreModel.create(
            game_id=game_id,
            user_id=user_id,
            count_score=count
        )
        return Score(game_id=score.game_id, user_id=score.user_id, count_score=score.count_score)

    async def get_scores_by_game(self, game_id:int) -> Optional[list[Score]]:
        scores = await (
            GamesModel.outerjoin(ScoreModel, GamesModel.id == ScoreModel.game_id)
                .select()
                .where(ScoreModel.game_id == game_id)
                .gino
                .all()
        )
        return [Score(score.game_id, score.user_id, score.count_score) for score in scores] if scores else None
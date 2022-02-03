from datetime import datetime
from operator import and_
from typing import Optional

from sqlalchemy import func

from app.base.base_accessor import BaseAccessor
from app.game.models import (
    Games,
    Users,
    Score,
    GamesModel,
    ScoreModel,
    UsersModel, UserWithScore
)
from app.quiz.models import Question


class GameAccessorNew(BaseAccessor):
    async def create_users(self, users: list[Users], chat_id: int) -> None:
        """
        Добавляем юзеров в БД
        """
        # пользователи из чата, добавляем только new
        users_id_from_db = [user.id for user in await self._get_users_by_chat_id(chat_id=chat_id)]
        list_dicts_users = [dict(id=user.id,
                                 first_name=user.first_name,
                                 last_name=user.last_name) for user in users if user.id not in users_id_from_db]
        if list_dicts_users:
            await UsersModel.insert().gino.all(*list_dicts_users)

    async def create_score(self, game_id: int, users: list[Users]) -> None:
        """
        Добавляем счета в игру, обновляем очки в объекте с игрой
        """
        list_dicts_scores = [dict(game_id=game_id,
                                  user_id=user.id,
                                  count_score=0) for user in users]
        await ScoreModel.insert().gino.all(*list_dicts_scores)

    async def update_score(self, user: UserWithScore) -> None:
        score = await ScoreModel.query.where(and_(ScoreModel.game_id == user.score.game_id,
                                                  ScoreModel.user_id == user.score.user_id)).gino.first()
        await score.update(count_score=user.score.count_score).apply()

    async def create_game(self, chat_id: int, theme_id: int) -> int:
        """
        Создаем запись игры в БД.
        Возвращаем game_id
        """
        game = await GamesModel.create(is_active=False,
                                       chat_id=chat_id,
                                       theme_id=theme_id,
                                       used_questions=[],
                                       state_round=False,
                                       round_answers=[])
        return game.id

    async def end_game(self, game_id: int) -> None:
        """
        Завершаем игру. Переключаем флаг is_active в game в False.
        """
        game = await GamesModel.query.where(GamesModel.id == game_id).gino.first()
        await game.update(is_active=False, finished_at=datetime.now()).apply()

    async def start_game(self, game_id: int, time: datetime) -> None:
        """
        Выбираем режим игры и запускаем игру is_active=True.
        Добавляем время завершения игры, если выбран режим игры по времени
        Инициализируем round_answers - all False
        """
        game = await GamesModel.query.where(GamesModel.id == game_id).gino.first()
        await game.update(finished_at=time,
                          is_active=True).apply()

    async def drop_game_round_answers(self, game_id: int, value: bool) -> None:
        """
        Во время основной механики необходимо обновлять состояния всех ответов юзеров,
        чтобы понять, когда ответили все юзеры
        """
        game = await GamesModel.query.where(GamesModel.id == game_id).gino.first()
        await game.update(round_answers=[]).apply()

    async def add_in_game_round_answers(self, game_id:int, user_id: int) -> None:
        game = await GamesModel.query.where(GamesModel.id == game_id).gino.first()
        await game.update(round_answers=game.append(user_id)).apply()

    async def set_game_state_round(self, game_id: int, value: bool) -> None:
        """
        Меняем состояние раунда - закончился или нет
        """
        game = await GamesModel.query.where(GamesModel.id == game_id).gino.first()
        await game.update(state_round=value).apply()

    # async def set_user_state_answer(self, game_id: int, user_id: int, value: bool) -> None:
    #     """
    #     Меняем состояние ответа юзера в игре - ответил или нет
    #     """
    #     score = await ScoreModel.query.where(and_(ScoreModel.game_id == game_id,
    #                                               ScoreModel.user_id == user_id)).gino.first()
    #     await score.update(state_answer=value).apply()

    async def get_users_by_game_id(self, game_id: int) -> list[Users]:
        """
        Достаем голый список юзеров по game_id
        """
        users = await (
            GamesModel.outerjoin(ScoreModel).outerjoin(UsersModel)
                .select()
                .where(GamesModel.id == game_id)
                .gino
                .load(
                GamesModel.distinct(GamesModel.id).load(users=UsersModel.distinct(UsersModel.id))
            )
                .all()
        )
        users = users[0]
        return [Users(user.id, user.first_name, user.last_name) for user in users.users] if users else None

    async def _get_users_by_chat_id(self, chat_id: int) -> list[Users]:
        """
        Достаем голый список юзеров по chat_id
        """
        users = await (
            GamesModel.outerjoin(ScoreModel).outerjoin(UsersModel)
                .select()
                .where(GamesModel.chat_id == chat_id)
                .gino
                .load(
                GamesModel.distinct(GamesModel.id).load(users=UsersModel.distinct(UsersModel.id))
            )
                .all()
        )
        users = users[0]
        return [Users(user.id, user.first_name, user.last_name) for user in users.users] if users else None

    async def get_users_with_score_by_game_id(self, game_id: int) -> Optional[list[UserWithScore]]:
        """
        Возвращаем список юзеров из БД по game_id с очками

        Если game_id нет, то возвращаем None
        """
        users = await (
            GamesModel.outerjoin(ScoreModel).outerjoin(UsersModel)
                .select()
                .where(ScoreModel.game_id == game_id)
                .gino
                .load(
                    GamesModel.distinct(GamesModel.id).load(users=UsersModel.distinct(UsersModel.id),
                                                            scores=ScoreModel.distinct(ScoreModel.user_id))
                )
                .all()
        )
        users_with_scores = []
        for score, user in zip(users[0].scores, users[0].users):
            users_with_scores.append(
                UserWithScore(
                    score=Score(
                        game_id=score.game_id,
                        user_id=score.user_id,
                        count_score=score.count_score
                    ),
                    user=Users(
                        id=user.id,
                        first_name=user.first_name,
                        last_name=user.last_name
                    )
                )
            )
        return users_with_scores if users_with_scores else None

    async def get_winner(self, game_id: int) -> Optional[UserWithScore]:
        """
        Получаем победителя по в игре
        """
        users = await self.get_users_with_score_by_game_id(game_id=game_id)
        user_max_score = users[0]
        for user in users:
            if user.score.count_score > user_max_score.score.count_score:
                user_max_score = user
        return user_max_score

    async def get_actual_game_by_chat_id(self, chat_id: int) -> Optional[Games]:
        """
        Достаем последнюю is_active=True игру по chat_id
        Вкладываем в объект игры users со scores, а также questions
        """
        game = await GamesModel\
            .query\
            .where(GamesModel.chat_id == chat_id)\
            .order_by(GamesModel.id.desc())\
            .gino.first()

        if not game or (not game.is_active and game.finished_at):
            return None

        users_with_scores = await self.get_users_with_score_by_game_id(game_id=game.id)
        questions = await self.app.store.quizzes.list_questions(theme_id=game.theme_id)
        print(questions)

        return Games(
            id=game.id,
            chat_id=game.chat_id,
            started_at=game.started_at,
            finished_at=game.finished_at,
            is_active=game.is_active,
            theme_id=game.theme_id,
            used_questions=game.used_questions,
            users=users_with_scores,
            questions=questions,
            state_round=game.state_round,
            round_answers=game.round_answers # game.round_answers
        )

    async def get_last_game(self) -> Optional[Games]:
        """
        Получаем последнюю завершенную игру
        """
        game = await GamesModel.query.order_by(GamesModel.id.desc()).gino.first()
        if not game:
            return None
        users_with_scores = await self.get_users_with_score_by_game_id(game_id=game.id)
        return Games(
            id=game.id,
            chat_id=game.chat_id,
            started_at=game.started_at,
            finished_at=game.finished_at,
            is_active=game.is_active,
            theme_id=game.theme_id,
            used_questions=game.used_questions,
            users=users_with_scores,
            questions=await self.app.store.quizzes.list_questions(game.theme_id),
            state_round=game.state_round,
            round_answers=game.round_answers
        )

    async def add_used_questions(self, game_id: int, questions: list[Question]) -> None:
        """
        Добавляем использованные вопросы в игре
        """
        questions_id = []
        game = await GamesModel.query.where(GamesModel.id == game_id).gino.first()
        questions_id.extend(game.used_questions)
        for question in questions:
            questions_id.append(question.id)
        await game.update(used_questions=questions_id).apply()




class GameAccessor(BaseAccessor):
    async def create_user(self, id_: int, fn: str, ln: str) -> Users:
        user = await UsersModel.create(id=id_, first_name=fn, last_name=ln)
        return Users(id=user.id, first_name=user.first_name, last_name=user.last_name)

    async def get_users_by_chat_id(self, chat_id: int) -> list[Users]:
        users = await (
            GamesModel.outerjoin(ScoreModel).outerjoin(UsersModel)
                .select()
                .where(GamesModel.chat_id == chat_id)
                .gino
                .load(
                    GamesModel.distinct(GamesModel.id).load(users=UsersModel.distinct(UsersModel.id))
                )
                .all()
        )
        users = users[0]
        return [Users(user.id, user.first_name, user.last_name) for user in users.users] if users else None

    async def get_winner(self, game_id: int) -> Optional[Users]:
        game = await self.get_game_by_id(game_id=game_id)
        scores = await self.get_scores_by_game(game_id=game.id)
        user = scores[0]
        for score in scores:
            if score.score.count_score > user.score.count_score:
                user = score
        return user

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

    async def get_game_by_id(self, game_id: int):
        game = await GamesModel \
            .query \
            .where(GamesModel.id == game_id) \
            .gino.first()
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
        game = await GamesModel\
            .query\
            .where(GamesModel.chat_id == chat_id)\
            .order_by(GamesModel.id.desc())\
            .gino.first()
        return Games(
            id=game.id,
            chat_id=game.chat_id,
            started_at=game.started_at,
            finished_at=None,
            is_active=game.is_active,
            theme_id=game.theme_id,
            used_questions=game.used_questions
        )if game and game.is_active else None

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

    async def end_game(self, id: int) -> None:
        game = await GamesModel.query.where(GamesModel.id == id).gino.first()
        await game.update(is_active=False).apply()

    async def add_finish(self, chat_id: int, time: datetime) -> None:
        game = await GamesModel.query.where(GamesModel.chat_id == chat_id).order_by(GamesModel.id.desc()).gino.first()
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

    # объединить с get_users_by_chat_id
    async def get_scores_by_game(self, game_id:int) -> Optional[list[UserWithScore]]:
        scores = await (
            GamesModel.outerjoin(ScoreModel).outerjoin(UsersModel)
                .select()
                .where(ScoreModel.game_id == game_id)
                .gino
                .load(
                    GamesModel.distinct(GamesModel.id).load(users=UsersModel.distinct(UsersModel.id),
                                                            scores=ScoreModel.distinct(ScoreModel.user_id))
                )
                .all()
        )
        result = []
        for score, user in zip(scores[0].scores, scores[0].users):
            print(score, user)
            result.append(
                UserWithScore(
                    score=Score(
                        game_id=score.game_id,
                        user_id=score.user_id,
                        count_score=score.count_score
                    ),
                    user=Users(
                        id=user.id,
                        first_name=user.first_name,
                        last_name=user.last_name
                    )
                )
            )
        return result if scores else None
import asyncio
import typing
from logging import getLogger
from datetime import datetime, timedelta
from enum import Enum

from app.game.models import Games, Users, UserWithScore
from app.quiz.models import Question
from app.store.vk_api.dataclasses import Update, Message

if typing.TYPE_CHECKING:
    from app.web.app import Application


MENU = "/menu"
START = "/start"
STOP = "/stop"
INFO = "/info"

WIN_SCORE = 50


class BotManager:
    def __init__(self, app: "Application"):
        self.app = app
        self.bot = None
        self.logger = getLogger("handler")

    # формируем обработку ответов
    async def handle_updates(self, updates: list[Update]):
        for update in updates:
            await self._logical_processing(update)

    async def _logical_processing(self, update: Update):
        game = await self.app.store.game.get_actual_game_by_chat_id(update.object.chat_id)
        print(game)
        message = f"{MENU} - меню бота"
        if update.object.body == MENU:
            message = f"Доступные команды: %0A" \
                      f"{START} - запуск игровой сессии %0A" \
                      f"{STOP} - завершение игровой сессии %0A" \
                      f"{INFO} - информация о текущей или последней сессии"
        elif update.object.body == START:
            if not game:  # 1 - если игра не запущена
                themes = {theme.id: theme.title for theme in await self.app.store.quizzes.list_themes()}
                text_themes = [str(theme[0]) + ". " + theme[1] for theme in themes.items()]
                message = "Введите номер темы :%0A" + "%0A".join(text_themes)
            else:
                message = f'Игра идет или не началась, введите {INFO} для вывода статуса игры'
        elif update.object.body == STOP:
            if game and game.is_active:  # если запущена, то останавливаем
                message = await self._end_game(game=game)
            else:
                message = f'Игра завершена, введите {INFO} для вывода статуса последней игры'
        elif update.object.body == INFO:
            if game and game.is_active:
                message = await self._print_scores(game=game) + '%0A Текущей игры'
            else:
                last_game = await self.app.store.game.get_last_game()
                message = await self._print_scores(game=last_game) + \
                          '%0A Последней игры' if last_game else 'Ни одной игры пока нет'
        else:
            text = update.object.body.strip('.?! ')
            if not game:
                if text.lower().isdigit():  # 2 принимаем # темы, создаем запись игры, создаем юзеров и очки
                    theme_id = int(text)#.split()[1])
                    themes = {theme.id: theme.title for theme in await self.app.store.quizzes.list_themes()}
                    if theme_id in themes:
                        message = 'Вы выбрали тему: ' + str(theme_id) + ' ' + themes[theme_id]
                        await self._send_message(update, message)
                        game_id = await self.app.store.game.create_game(chat_id=update.object.chat_id,
                                                                        theme_id=theme_id)
                        users = await self.app.store.vk_api.get_chat_users(chat_id=update.object.chat_id)
                        await self.app.store.game.create_users(users=users, chat_id=update.object.chat_id)
                        await self.app.store.game.create_score(game_id=game_id, users=users)
                        message = 'Введите: %0A 0 - Если играем пока есть вопросы ' \
                                  '%0A Количество минут - Играем пока не закончится введенное время'
                    else:
                        message = 'Такой темы нет'
                else:
                    pass
                    #message = 'Введите корретный номер темы. /start для вывода списка тем'
            elif not game.is_active:
                if text.isdigit():  # 3 время или вопросы
                    count_mins = int(text)
                    await self.app.store.game.start_game(game.id,
                                                         datetime.now() + timedelta(minutes=count_mins)
                                                         if count_mins != 0 else None)
                    if count_mins > 0:
                        message = f'Выбран режим игры по времени. Время на игру {count_mins} минут'
                    else:
                        message = 'Выбран режим игры по умолчанию. Пока не закончатся вопросы'

                    message += '%0A %0A Начинаем'
                    await self._send_message(update, message)
                    await self._start_game(update, game)
                    return
                else:
                    message = 'Выберите режим игры'
            elif game.is_active:
                await self._start_game(update, game)
        await self._send_message(update, message)

    async def _get_question(self, game: Games) -> Question:
        question = None
        if not game.state_round: # если раунд не начался
            for q in game.questions:
                if q.id not in game.used_questions: # вытаскивваем вопросы, которых не было
                    question = q
                    await self.app.store.game.add_used_questions(game_id=game.id, questions=[question])
                    break
            # if len(game.used_questions) == len(game.questions):  # закончились вопросы
            #     question = None
        else:  # если раунд идет
            question = [question for question in game.questions if question.id == game.used_questions[-1]][0]
        return question

    async def _start_game(self, update: Update, game: Games):
        question = None
        user = [user for user in game.users if user.user.id == update.object.user_id][0]  # доставем нужного юзера
        user_answer = update.object.body.strip('.?! ')  # ответ юзера
        if not game.state_round:  # если раунд не начался
            for q in game.questions:
                if q.id not in game.used_questions:  # вытаскивваем вопросы, которых не было
                    question = q
                    await self.app.store.game.add_used_questions(game_id=game.id, questions=[question])
                    break
        else:  # если раунд идет
            question = [question for question in game.questions if question.id == game.used_questions[-1]][0]

        if question:
            question_answer = [answer.title for answer in question.answers if answer.is_correct][0] # правильный ответ на вопрос
            if game.state_round and user.score.user_id not in game.round_answers:
                if user_answer == question_answer: # первый ответил правильно
                    user.score.count_score += WIN_SCORE
                    await self.app.store.game.update_score(user=user)
                    await self._finish_round(game_id=game.id)
                    message = 'Игрок ' + user.user.first_name + ' ' + user.user.last_name + ' ответил верно'
                    await self._send_message(update, message)

                    # отправляемм новый вопрос после правильного ответа
                    game = await self.app.store.game.get_actual_game_by_chat_id(update.object.chat_id)
                    question = await self._get_question(game=game)
                    await self._send_question(question=question, update=update)
                else:
                    await self.app.store.game.add_in_game_round_answers(game_id=user.score.game_id,
                                                                        user_id=user.score.user_id)
                    if len(game.round_answers) == len(game.users):  # ответили все неправильно
                        await self._finish_round(game_id=game.id)
                        message = 'Никто не ответил правильно %0A Верный ответ - ' + question_answer
                        await self._send_message(update, message)

                        game = await self.app.store.game.get_actual_game_by_chat_id(update.object.chat_id)
                        question = await self._get_question(game=game)
                        await self._send_question(question=question, update=update)
            else:
                await self.app.store.game.set_game_state_round(game_id=game.id, value=True)
                await self._send_question(question=question, update=update)

        else:
            message = 'Вопросы закончились %0A'
            message += await self._end_game(game=game) # заканчивваем игру
            await self._send_message(update, message)


    async def _send_question(self, question: Question, update: Update):
        message = question.title + '%0A'
        message += '%0A Варианты ответов: %0A- ' + "%0A- ".join([answer.title for answer in question.answers])
        message += '%0A%0A Введите ответ из предложенных'
        await self._send_message(update, message)

    async def _finish_round(self, game_id: int):
        await self.app.store.game.set_game_state_round(game_id=game_id, value=False)
        await self.app.store.game.drop_game_round_answers(game_id=game_id, value=False)

    async def _end_game(self, game: Games):
        await self.app.store.game.end_game(game_id=game.id)  # останавливаем игру
        winner = await self._get_winner_from_bot_manager(game=game)  # определяем победителя
        message = 'Игра завершена %0A' + await self._print_scores(game=game) \
                  + "%0AПобедитель: " + str(winner.user.first_name) + ' ' + str(winner.user.last_name)
        return message

    async def _print_scores(self, game: Games) -> str:
        text_scores = [user.user.first_name + " " + user.user.last_name + " - " + str(user.score.count_score) for user in game.users]
        message = "Рейтинг игроков:%0A" + "%0A".join(text_scores)
        return message

    async def _get_winner_from_bot_manager(self, game: Games) -> UserWithScore:
        users = game.users
        user_max_score = users[0]
        for user in users:
            if user.score.count_score > user_max_score.score.count_score:
                user_max_score = user
        return user_max_score

    async def _send_message(self, update: Update, message: str):
        await self.app.store.vk_api.send_message(
            Message(
                user_id=update.object.user_id,
                text=message,
                peer_id=update.object.peer_id,
                chat_id=update.object.chat_id
            )
        )
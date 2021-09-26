import typing
from logging import getLogger
from datetime import datetime, timedelta

from app.game.models import Games
from app.store.vk_api.dataclasses import Update, Message

if typing.TYPE_CHECKING:
    from app.web.app import Application


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
        game = await self.app.store.game.get_game_by_chat_id(update.object.chat_id)
        print(game)
        themes = {theme.id: theme.title for theme in await self.app.store.quizzes.list_themes()}
        message = "Введите /menu"
        # общая часть
        if update.object.body == "/menu":  # 1
            message = "Доступные команды: %0A" \
                      "/start - запуск игровой сессии %0A" \
                      "/stop - завершение игровой сессии %0A" \
                      "/info - информация о текущей или последней сессии"
        elif update.object.body == "/info":
            if game and game.is_active:
                message = await self._print_scores(game_id=game.id) + '%0A Текущей игры'
            else:
                last_game = await self.app.store.game.get_last_game()
                message = await self._print_scores(game_id=last_game.id) + \
                          '%0A Последней игры' if last_game else 'Ни одной игры пока нет'
        elif update.object.body == "/stop":
            if game and game.is_active:
                await self.app.store.game.end_game(update.object.chat_id)
                winner = await self.app.store.game.get_winner(chat_id=update.object.chat_id)
                message = 'Игра завершена %0A' + await self._print_scores(game_id=game.id) \
                          + "%0AПобедитель: " + str(winner.user_id)
            else:
                message = 'Игра не началась'
        elif update.object.body == "/start":  # 1
            if game and game.is_active:
                message = 'Игра идет, введите /info для вывода статуса'
            else:
                text_themes = [str(theme[0]) + ". " + theme[1] for theme in themes.items()]
                message = "Введите номер темы из предложенных вариантов:%0A" + "%0A".join(text_themes)  # %0A - \n
        else:
            text = update.object.body.strip('.?! ')
            if text.isdigit() and not game:  # 2 принимаем номер темы
                theme_id = int(text)
                if int(text) in themes:
                    message = 'Вы выбрали тему: ' + str(theme_id) + ' ' + themes[theme_id]
                    await self.app.store.game.create_game(chat_id=update.object.chat_id, theme_id=theme_id)
                    await self._send_message(update, message)
                    message = 'Введите: %0A 0 - Если играем пока есть вопросы ' \
                              '%0A Количество минут - Играем пока не закончится введенное время'
                else:
                    message = 'Такой темы нет'
            elif game and not game.finished_at and text.isdigit():  # 3 время или вопросы
                count_mins = int(text)
                mins = 100000 if count_mins == 0 else count_mins  # 100000 - минут
                await self.app.store.game.add_finish(update.object.chat_id, datetime.now() + timedelta(minutes=mins))
                if count_mins > 0:
                    message = f'Выбран режим игры по времени. Время на игру {count_mins} минут'
                else:
                    message = 'Выбран режим игры по умолчанию. Пока не закончатся вопросы'

                message += '%0A %0A Начинаем'
            elif game and game.is_active:
                await self._start_game(update, game)

        await self._send_message(update, message)

    async def _start_game(self, update: Update, game: Games):
        pass

    async def _print_scores(self, game_id: int):
        scores = await self.app.store.game.get_scores_by_game(game_id=game_id)
        text_scores = ["user_id " + str(score.user_id) + " - " + str(score.count_score) for score in scores]
        message = "Рейтинг игроков:%0A" + "%0A".join(text_scores)
        return message

    async def _send_message(self, update: Update, message: str):
        await self.app.store.vk_api.send_message(
            Message(
                user_id=update.object.user_id,
                text=message,
                peer_id=update.object.peer_id,
                chat_id=update.object.chat_id
            )
        )
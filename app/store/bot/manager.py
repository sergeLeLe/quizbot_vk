import typing
from logging import getLogger

from app.store.vk_api.dataclasses import Update, Message

if typing.TYPE_CHECKING:
    from app.web.app import Application


class BotManager:
    def __init__(self, app: "Application"):
        self.app = app
        self.bot = None
        self.logger = getLogger("handler")
        self.theme: str = ''
        self.time: str = '' # '' - пока есть вопросы, not '' - задаем время

    # формируем обработку ответов
    async def handle_updates(self, updates: list[Update]):
        for update in updates:
            await self._logical_processing(update)

    async def _logical_processing(self, update: Update):
        themes = {theme.id: theme.title for theme in await self.app.store.quizzes.list_themes()}
        message = "Введите /start для запуска игровой сессии"
        if update.object.body == "/start":
            text_themes = [str(theme[0]) + ". " + theme[1] for theme in themes.items()]
            message = "Введите номер темы из предложенных вариантов:%0A" + "%0A".join(text_themes)  # %0A - \n
        elif update.object.body.strip('.?! ').isdigit() and not self.theme:
            self.theme = themes.get(int(update.object.body.strip('.?! ')))
            message = 'Вы выбрали тему: ' + self.theme
            await self._send_message(update, message)
            message = 'Введите: %0A 0 - Если играем пока есть вопросы ' \
                      '%0A Количество минут - Играем пока не закончится введенное время'
        elif update.object.body.strip('.?! ').isdigit() and self.theme:
            self.time = update.object.body.strip('.?! ')
            if self.time != '0':
                message = f'Выбран режим игры по времени. Время на игру {self.time} минут'
            else:
                message = 'Выбран режим игры по умолчанию'
        await self._send_message(update, message)

    async def _send_message(self, update: Update, message: str):
        await self.app.store.vk_api.send_message(
            Message(
                user_id=update.object.user_id,
                text=message,
            )
        )
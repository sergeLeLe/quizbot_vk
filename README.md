Чат-бот, работающий с VK API.

Функционал:
	- Авторизация по cookie
	- Методы добавления вопросов и ответов в БД (PostgreSQL)
	- Интеграция с VK API по LongPolling
	- Игровая механика чат-бота
	
Стэк: 
	- Python 3 
	- Aiohttp 
	- Asyncio
	- PostgreSQL
	- Gino
	- Apispec
	- Alembic
	- Marshmellow
	- Aiohttp-session.

Запуск:
1. Добавить свой файл config.yaml
2. Необходимо прописать переменные окружения для путей конфига и интерпретатора 
(CONFIGPATH, PYTHONPATH)
3. Применить миграции


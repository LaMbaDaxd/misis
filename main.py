import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config.settings import TELEGRAM_BOT_TOKEN, DATABASE_PATH
from database.manager import add_habit
from database.manager import init_db
from bot.handlers import router



# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def main():
    # Проверка обязательных настроек
    if not TELEGRAM_BOT_TOKEN:
        logger.critical("TELEGRAM_BOT_TOKEN не задан в .env")
        raise RuntimeError("TELEGRAM_BOT_TOKEN не найден в настройках")

    if not DATABASE_PATH:
        logger.critical("DATABASE_PATH не задан в .env")
        raise RuntimeError("DATABASE_PATH не найден в настройках")

    try:
        # Инициализация БД
        logger.info(f"Инициализация базы данных: {DATABASE_PATH}")
        init_db()
        logger.info("База данных инициализирована успешно")

        # Создание бота и диспетчера
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        dp = Dispatcher(storage=MemoryStorage())

        # Подключение роутеров
        dp.include_router(router)
        logger.info("Роутеры подключены успешно")

        # Запуск polling
        logger.info("Запуск бота (polling)...")
        await dp.start_polling(bot)

    except Exception as e:
        logger.exception(f"Критическая ошибка при запуске бота: {e}")
        raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.critical(f"Невосстановимая ошибка: {e}")

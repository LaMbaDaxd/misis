from pathlib import Path
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
DATABASE_PATH = os.getenv('DATABASE_PATH', str(BASE_DIR / 'habit_tracker.db'))
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Настройки напоминаний / поведения бота
DAILY_REMINDER_HOUR = int(os.getenv('DAILY_REMINDER_HOUR', '20'))  # 20 = 20:00

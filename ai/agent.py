import os
import logging
from config.settings import OPENAI_API_KEY

logger = logging.getLogger(__name__)

# Опционально используем OpenAI. Если ключ не задан — используем простую подсказочную логику.
try:
    import openai
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    logger.warning(f"Не удалось инициализировать OpenAI: {e}")
    client = None

async def suggest_improvement(habit_name: str, recent_stats: dict | None = None) -> str:
    """Вернуть рекомендацию по улучшению привычки.

    Если есть OPENAI_API_KEY, обращаемся к OpenAI; иначе — возвращаем простую рекомендацию.
    """
    prompt = f"Дай короткий дружелюбный совет как улучшить привычку: {habit_name}."
    if recent_stats:
        prompt += f" Статистика: {recent_stats}."

    if client is not None and OPENAI_API_KEY:
        try:
            response = client.chat.completions.create(
                model='gpt-3.5-turbo',
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=120,
            )
            text = response.choices[0].message.content.strip()
            return text
        except openai.RateLimitError:
            return "Превышен лимит запросов к OpenAI. Попробуйте позже."
        except openai.AuthenticationError:
            return "Ошибка аутентификации OpenAI. Проверьте API-ключ."
        except Exception as e:
            logger.error(f"Ошибка OpenAI API: {e}")
            return f"Не удалось получить рекомендацию от OpenAI: {e}"

    # Простая локальная логика
    advice = f"Подумай, как конкретнее сформулировать: вместо '{habit_name}' — скажи точное действие, и начни с малого."
    if recent_stats:
        advice += " Также попробуй разбить цель на ежедневные маленькие шаги и отмечать даже половинчатое выполнение."
    return advice

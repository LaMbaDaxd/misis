import asyncio
from typing import Optional

from openai import OpenAI, OpenAIError 

from config.settings import OPENROUTER_API_KEY, OPENROUTER_MODEL


_client: Optional[OpenAI] = None


def _get_client() -> Optional[OpenAI]:
    """Создаём (или возвращаем) клиента OpenRouter (через OpenAI SDK)."""
    global _client

    if not OPENROUTER_API_KEY:
        print("OPENROUTER_API_KEY не задан")
        return None

    if _client is None:
        print("Создаём клиента OpenRouter")
        _client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
            default_headers={
                "HTTP-Referer": "https://your-bot-url.com", 
                "X-Title": "Habit Tracker Bot",              
            }
        )

    return _client


def _call_openrouter_sync(prompt: str, selected_habit: str) -> str:
    """Синхронный запрос к OpenRouter через OpenAI SDK с учётом выбранной привычки."""

    client = _get_client()
    if client is None:
        return (
            "Сейчас ИИ (OpenRouter) не настроен — не найден API-ключ.\n"
            "Проверь файл .env (OPENROUTER_API_KEY) и перезапусти бота."
        )

    try:
        completion = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты дружелюбный помощник по формированию полезных привычек. "
                        "Отвечай по-русски, коротко и по делу. "
                        f"Пользователь выбрал привычку: '{selected_habit}'. "
                        "Дай 3–5 конкретных советов, как улучшить выполнение этой привычки. "
                        "Избегай общих фраз, фокусируйся на практических действиях. "
                        "Формат: нумерованный список из 3–5 пунктов."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            max_tokens=200,
            temperature=0.8,
        )

        message = completion.choices[0].message.content
        if not message:
            return f"Попробуй улучшить привычку '{selected_habit}' — начни с малого! 🙂"

        return message.strip()
    

    except OpenAIError as e:
        text = str(e)
        print("OpenRouterError:", repr(e))

        if "401" in text or "Unauthorized" in text:
            return (
                "Ошибка авторизации в OpenRouter (код 401).\n"
                "Проверь, что OPENROUTER_API_KEY в .env указан правильно и ключ не отозван."
            )
        if "403" in text or "Forbidden" in text:
            return (
                "Доступ к модели OpenRouter запрещён (код 403).\n"
                "Проверь, доступна ли эта модель в твоём аккаунте или выбери другую."
            )
        if "429" in text or "Too Many Requests" in text:
            return (
                "Слишком много запросов к OpenRouter за короткое время (код 429).\n"
                "Подожди немного и попробуй снова."
            )

        return (
            "OpenRouter вернул ошибку.\n"
            "Попробуй ещё раз немного позже."
        )

    except Exception as e:
        # Любая другая ошибка (сеть и т.п.)
        print("Неизвестная ошибка OpenRouter:", repr(e))
        return (
            "Не удалось получить ответ от ИИ (OpenRouter).\n"
            "Попробуй позже или просто выбери одну маленькую цель на сегодня."
        )

async def ask_ai(prompt: str, selected_habit: str) -> str:
    """Асинхронная обёртка над запросом к OpenRouter с учётом выбранной привычки."""
    return await asyncio.to_thread(_call_openrouter_sync, prompt, selected_habit)
from __future__ import annotations

from datetime import date
from typing import Set, Optional

from aiogram import Router, F
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,  # Добавлен импорт CallbackQuery
)

from ai.agent import ask_ai

from database.manager import (
    get_or_create_user,
    add_habit,
    list_habits,
    add_entry,
    get_stats,
)

router = Router()

# Простенькое "состояние" в памяти процесса
_pending_add_habit: Set[int] = set()
_pending_mark_habit: Set[int] = set()
_pending_ai_advice: Set[int] = set()  # Новое состояние для ожидания выбора привычки для совета

# ===================== Клавиатура =====================

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Основное меню бота."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="➕ Добавить привычку"),
                KeyboardButton(text="📋 Мои привычки"),
            ],
            [
                KeyboardButton(text="✅ Отметить выполнение"),
                KeyboardButton(text="📊 Статистика"),
            ],
            [KeyboardButton(text="💡 Совет от ИИ")],
        ],
        resize_keyboard=True,
    )

# ===================== Старт / help =====================

@router.message(F.text == "/start")
async def cmd_start(message: Message) -> None:
    """Приветствие и регистрация пользователя в БД."""
    user = get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    text = (
        f"Привет, {user.first_name or 'друг'}! 👋\n\n"
        "Я трекер привычек. Помогу тебе формировать полезные привычки и "
        "отслеживать прогресс каждый день.\n\n"
        "Выбери действие в меню ниже 👇"
    )
    await message.answer(text, reply_markup=main_menu_keyboard())

@router.message(F.text == "/help")
async def cmd_help(message: Message) -> None:
    text = (
        "Я могу:\n"
        "• добавлять привычки\n"
        "• показывать твой список привычек\n"
        "• отмечать выполнение\n"
        "• показывать простую статистику\n"
        "• давать совет от ИИ 💡\n\n"
        "Используй кнопки внизу экрана."
    )
    await message.answer(text, reply_markup=main_menu_keyboard())

# ===================== Добавить привычку =====================

@router.message(F.text == "➕ Добавить привычку")
async def add_habit_start(message: Message) -> None:
    """Шаг 1: просим ввести название привычки."""
    _pending_add_habit.add(message.from_user.id)

    await message.answer(
        "Напиши название новой привычки одной строкой.\n\n"
        "Например: <b>Пить стакан воды утром</b>\n"
        "Чтобы отменить — отправь /cancel.",
        parse_mode="HTML",
    )

# ===================== Мои привычки =====================

@router.message(F.text == "📋 Мои привычки")
async def show_habits(message: Message) -> None:
    """Показать список привычек пользователя."""
    habits = list_habits(message.from_user.id)

    if not habits:
        await message.answer(
            "У тебя пока нет ни одной привычки.\n"
            "Нажми «➕ Добавить привычку», чтобы начать 🙂",
            reply_markup=main_menu_keyboard(),
        )
        return

    text_lines = ["Твои привычки:\n"]
    for h in habits:
        text_lines.append(f"{h.id}. {h.name} (период: {h.period})")

    await message.answer(
        "\n".join(text_lines),
        reply_markup=main_menu_keyboard(),
    )

# ===================== Отметить выполнение =====================

@router.message(F.text == "✅ Отметить выполнение")
async def mark_habit_start(message: Message) -> None:
    """Просим пользователя выбрать ID привычки для отметки."""
    habits = list_habits(message.from_user.id)

    if not habits:
        await message.answer(
            "Сначала добавь хотя бы одну привычку 🙂",
            reply_markup=main_menu_keyboard(),
        )
        return

    _pending_mark_habit.add(message.from_user.id)

    text_lines = ["Напиши номер привычки, которую ты сегодня выполнил:\n"]
    for h in habits:
        text_lines.append(f"{h.id}. {h.name}")

    text_lines.append("\nЧтобы отменить — отправь /cancel.")
    await message.answer("\n".join(text_lines))

# ===================== Статистика =====================

@router.message(F.text == "📊 Статистика")
async def show_stats(message: Message) -> None:
    """Простая статистика по привычкам."""
    habits = list_habits(message.from_user.id)
    if not habits:
        await message.answer(
            "Пока нет привычек — показывать нечего 🙂",
            reply_markup=main_menu_keyboard(),
        )
        return

    stats = get_stats(message.from_user.id)

    lines = ["📊 Статистика по привычкам:\n"]
    for h in habits:
        s = stats.get(h.id, {"total": 0, "done": 0})
        lines.append(f"{h.name}: {s['done']} из {s['total']} выполнений")

    await message.answer(
        "\n".join(lines),
        reply_markup=main_menu_keyboard(),
    )

# ===================== Совет от ИИ =====================

@router.message(F.text == "💡 Совет от ИИ")
async def ai_advice_start(message: Message) -> None:
    """Начинаем процесс получения совета: показываем список привычек для выбора."""
    habits = list_habits(message.from_user.id)

    if not habits:
        await message.answer(
            "Сначала добавь хотя бы одну привычку, чтобы я мог дать полезный совет 🙂",
            reply_markup=main_menu_keyboard(),
        )
        return

    # Сохраняем состояние
    _pending_ai_advice.add(message.from_user.id)

    # Формируем клавиатуру с кнопками для каждой привычки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for habit in habits:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=habit.name,
                callback_data=f"ai_advice_{habit.id}"
            )
        ])

    keyboard.inline_keyboard.append([
        InlineKeyboardButton(
            text="Отмена",
            callback_data="ai_advice_cancel"
        )
    ])

    await message.answer(
        "Выбери привычку, по которой хочешь получить совет:",
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("ai_advice_"))
async def handle_ai_advice_choice(callback: CallbackQuery) -> None:
    """Обрабатываем выбор привычки для получения совета."""
    user_id = callback.from_user.id
    data = callback.data

    # Если нажали "Отмена"
    if data == "ai_advice_cancel":
        await callback.message.edit_text("Выбор привычки отменён.")
        _pending_ai_advice.discard(user_id)
        await callback.answer()
        return

    if user_id not in _pending_ai_advice:
        await callback.answer("Запрос устарел. Начни заново через меню.")
        return

    # Извлекаем ID привычки из callback_data
    try:
        habit_id = int(data.split("_")[-1])
    except ValueError:
        await callback.answer("Некорректный выбор привычки.")
        return

    # Получаем информацию о привычке
    habits = list_habits(user_id)
    habit = next((h for h in habits if h.id == habit_id), None)

    if not habit:
        await callback.answer("Привычка не найдена.")
        return

    # Убираем состояние
    _pending_ai_advice.discard(user_id)

    # Удаляем кнопки (редактируем сообщение)
    await callback.message.edit_text(f"Выбрана привычка: {habit.name}\n\nИИ генерирует совет...")

    # Получаем совет от ИИ
    try:
        advice = await ask_ai(
            prompt=f"Дай совет по привычке: {habit.name}",
            selected_habit=habit.name
        )
        
        # Отправляем результат пользователю
        await callback.message.answer(
            f"💡 Совет от ИИ по привычке <b>«{habit.name}»</b>:\n\n"
            f"{advice}\n\n"
            f"Удачи в формировании привычки! 💪",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )
        
        # Отправляем ответное уведомление (убирает "часики" на кнопке)
        await callback.answer()
        
    except Exception as e:
        print(f"Ошибка при получении совета от ИИ: {e}")
        await callback.message.answer(
            "Произошла ошибка при получении совета от ИИ. Попробуйте позже.",
            reply_markup=main_menu_keyboard()
        )
        await callback.answer()
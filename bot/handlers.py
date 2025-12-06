from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from ai.agent import ask_ai
from database.manager import (
    get_or_create_user,
    add_habit,
    list_habits,
    add_entry,
    get_stats,
)

router = Router()


class AddHabitStates(StatesGroup):
    """Состояния для пошагового добавления привычки."""
    waiting_for_name = State()
    waiting_for_period = State()


class MarkHabitStates(StatesGroup):
    """Состояния для отметки выполнения привычки."""
    waiting_for_choice = State()


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с основными действиями."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить привычку"), KeyboardButton(text="📋 Мои привычки")],
            [KeyboardButton(text="✅ Отметить выполнение"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="💡 Совет от ИИ")],
        ],
        resize_keyboard=True,
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Обработка /start: регистрируем пользователя и показываем меню."""
    get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    await state.clear()
    await message.answer(
        "Привет! Я бот-трекер привычек.\n"
        "Я помогу записывать привычки, отмечать выполнение и иногда подскажу, что можно улучшить.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Краткая справка по возможностям бота."""
    await message.answer(
        "Я помогаю отслеживать привычки.\n\n"
        "Доступные действия:\n"
        "• /start — перезапустить бота и показать меню\n"
        "• /help — показать эту справку\n"
        "• /done — отметить выполнение привычки за сегодня\n"
        "• /stats — показать простую статистику\n\n"
        "Или используйте кнопки меню:\n"
        "• ➕ Добавить привычку\n"
        "• 📋 Мои привычки\n"
        "• ✅ Отметить выполнение\n"
        "• 📊 Статистика\n"
        "• 💡 Совет от ИИ",
        reply_markup=main_menu_keyboard(),
    )


# ===================== Добавление привычки =====================

@router.message(F.text == "➕ Добавить привычку")
async def start_add_habit(message: Message, state: FSMContext) -> None:
    """Запускаем сценарий добавления новой привычки."""
    await state.set_state(AddHabitStates.waiting_for_name)
    await message.answer("Какую привычку хотите отслеживать? Напишите её кратко, в одну строку.")


@router.message(AddHabitStates.waiting_for_name)
async def process_habit_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Пожалуйста, напишите название привычки текстом.")
        return

    await state.update_data(name=name)
    await state.set_state(AddHabitStates.waiting_for_period)
    await message.answer(
        "Как часто вы хотите выполнять эту привычку?\n"
        "Например: каждый день, 3 раза в неделю, по будням и т.п.",
    )


@router.message(AddHabitStates.waiting_for_period)
async def process_habit_period(message: Message, state: FSMContext) -> None:
    period = (message.text or "").strip()
    if not period:
        await message.answer("Опишите периодичность текстом, например: каждый день.")
        return

    data = await state.get_data()
    name = data.get("name")
    if not name:
        await message.answer(
            "Что-то пошло не так, давайте начнём сначала — выберите «Добавить привычку» в меню."
        )
        await state.clear()
        return

    add_habit(
        user_id=message.from_user.id,
        name=name,
        period=period,
    )
    await state.clear()
    await message.answer(
        "Готово! Я добавил привычку:\n\n"
        f"• {name}\n"
        f"Периодичность: {period}\n\n"
        "Теперь вы можете добавлять ещё привычки, отмечать выполнение или посмотреть список.",
        reply_markup=main_menu_keyboard(),
    )


# ===================== Список привычек =====================

@router.message(F.text == "📋 Мои привычки")
async def show_habits(message: Message) -> None:
    """Печатаем список привычек пользователя."""
    habits = list_habits(message.from_user.id)
    if not habits:
        await message.answer(
            "У вас пока нет сохранённых привычек.\n"
            "Нажмите «➕ Добавить привычку», чтобы создать первую!",
            reply_markup=main_menu_keyboard(),
        )
        return

    lines = ["Ваши привычки:"]
    for h in habits:
        lines.append(f"• {h.name} — {h.period}")
    await message.answer("\n".join(lines), reply_markup=main_menu_keyboard())


# ===================== Отметка выполнения =====================

@router.message(F.text == "✅ Отметить выполнение")
@router.message(Command("done"))
async def start_mark_done(message: Message, state: FSMContext) -> None:
    """Начинаем сценарий отметки выполнения привычки за сегодня."""
    habits = list_habits(message.from_user.id)
    if not habits:
        await message.answer(
            "У вас пока нет привычек, которые можно отметить.\n"
            "Сначала добавьте хотя бы одну привычку.",
            reply_markup=main_menu_keyboard(),
        )
        return

    # Сохраняем список id привычек в состояние, чтобы потом по номеру найти нужную
    habit_ids = [h.id for h in habits]
    await state.update_data(habit_ids=habit_ids)
    await state.set_state(MarkHabitStates.waiting_for_choice)

    lines = ["Выберите номер привычки, которую вы выполнили сегодня:"]
    for i, h in enumerate(habits, start=1):
        lines.append(f"{i}. {h.name} — {h.period}")
    lines.append("\nОтправьте номер (например, 1).")

    await message.answer("\n".join(lines), reply_markup=main_menu_keyboard())


@router.message(MarkHabitStates.waiting_for_choice)
async def process_mark_choice(message: Message, state: FSMContext) -> None:
    """Обрабатываем номер привычки, которую нужно отметить как выполненную."""
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("Пожалуйста, отправьте номер привычки (целое число).")
        return

    index = int(text)
    data = await state.get_data()
    habit_ids = data.get("habit_ids") or []

    if not habit_ids or index < 1 or index > len(habit_ids):
        await message.answer(
            "Неверный номер привычки.\n"
            "Попробуйте снова через «✅ Отметить выполнение».",
            reply_markup=main_menu_keyboard(),
        )
        await state.clear()
        return

    # Определяем id привычки по номеру
    habit_id = habit_ids[index - 1]

    # Чтобы вывести название в ответе, снова получим список привычек
    habits = list_habits(message.from_user.id)
    habit = next((h for h in habits if h.id == habit_id), None)

    add_entry(habit_id=habit_id)

    await state.clear()

    if habit is not None:
        await message.answer(
            f"Отметил выполнение привычки «{habit.name}» за сегодня 🎉",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await message.answer(
            "Отметка выполнения сохранена.",
            reply_markup=main_menu_keyboard(),
        )


# ===================== Статистика =====================

@router.message(F.text == "📊 Статистика")
@router.message(Command("stats"))
async def show_stats(message: Message) -> None:
    """Показываем простую статистику по привычкам пользователя."""
    habits = list_habits(message.from_user.id)
    if not habits:
        await message.answer(
            "У вас пока нет привычек, поэтому статистика отсутствует.\n"
            "Добавьте привычку и начните отмечать выполнение.",
            reply_markup=main_menu_keyboard(),
        )
        return

    stats = get_stats(message.from_user.id)

    lines = ["Ваша статистика по привычкам:\n"]
    for h in habits:
        st = stats.get(h.id, {"total": 0, "done": 0})
        total = st.get("total", 0)
        done = st.get("done", 0)
        lines.append(f"• {h.name} — отметок: {done}")

    await message.answer("\n".join(lines), reply_markup=main_menu_keyboard())


# ===================== Совет от ИИ =====================

@router.message(F.text == "💡 Совет от ИИ")
async def ai_advice(message: Message) -> None:
    """Получаем короткий совет от ИИ (или заглушку, если ИИ недоступен)."""
    user_text = (
        "Дай короткий совет по формированию полезных привычек для пользователя Telegram. "
        "Ответь по-дружески и по-русски."
    )
    reply = await ask_ai(user_text)
    await message.answer(reply, reply_markup=main_menu_keyboard())


# ===================== Обработчик по умолчанию =====================

@router.message()
async def fallback(message: Message) -> None:
    """Обработчик по умолчанию на произвольный текст."""
    await message.answer(
        "Я пока понимаю только команды из меню и /help.\n"
        "Попробуйте выбрать действие с клавиатуры ниже 🙂",
        reply_markup=main_menu_keyboard(),
    )

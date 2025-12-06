from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from ai.agent import ask_ai
from database.manager import get_or_create_user, add_habit, list_habits

router = Router()


class AddHabitStates(StatesGroup):
    """Состояния для пошагового добавления привычки."""
    waiting_for_name = State()
    waiting_for_period = State()


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с основными действиями."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить привычку")],
            [KeyboardButton(text="📋 Мои привычки")],
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
        "Я помогу записывать привычки и иногда подскажу, что можно улучшить.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Краткая справка по возможностям бота."""
    await message.answer(
        "Я помогаю отслеживать привычки.\n\n"
        "Доступные действия:\n"
        "• /start — перезапустить бота и показать меню\n"
        "• Добавить привычку — создать новую привычку\n"
        "• Мои привычки — показать список\n"
        "• Совет от ИИ — получить короткую рекомендацию",
        reply_markup=main_menu_keyboard(),
    )


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
        "Теперь вы можете добавлять ещё привычки или посмотреть список.",
        reply_markup=main_menu_keyboard(),
    )


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


@router.message(F.text == "💡 Совет от ИИ")
async def ai_advice(message: Message) -> None:
    """Получаем короткий совет от ИИ (или заглушку, если ИИ недоступен)."""
    user_text = (
        "Дай короткий совет по формированию привычек для пользователя Telegram. "
        "У него могут быть как полезные, так и вредные привычки."
    )
    reply = await ask_ai(user_text)
    await message.answer(reply, reply_markup=main_menu_keyboard())


@router.message()
async def fallback(message: Message) -> None:
    """Обработчик по умолчанию на произвольный текст."""
    await message.answer(
        "Я пока понимаю только команды из меню и /help.\n"
        "Попробуйте выбрать действие с клавиатуры ниже 🙂",
        reply_markup=main_menu_keyboard(),
    )

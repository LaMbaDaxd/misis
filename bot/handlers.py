from aiogram import types, Dispatcher
from database import Database

db = Database()

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    db.add_user(user_id, username, first_name)
    await message.answer(f"Привет, {first_name}! Я бот для отслеживания привычек.")

@dp.message_handler(commands=['add_habit'])
async def add_habit(message: types.Message):
    args = message.text.split()[1:]  # Пример: /add_habit бег ежедневно 7
    if len(args) != 3:
        await message.answer("Формат: /add_habit <название> <частота> <цель>")
        return

    habit_name, frequency, goal = args
    user_id = message.from_user.id
    db.add_habit(user_id, habit_name, frequency, int(goal))
    await message.answer(f"Привычка '{habit_name}' добавлена!")

@dp.message_handler(commands=['my_habits'])
async def my_habits(message: types.Message):
    user_id = message.from_user.id
    habits = db.get_habits(user_id)
    if not habits:
        await message.answer("У вас пока нет привычек.")
        return

    response = "Ваши привычки:\n"
    for habit in habits:
        response += f"- {habit[0]} ({habit[1]}) | Прогресс: {habit[3]}/{habit[2]}\n"
    await message.answer(response)

@dp.message_handler(commands=['done'])
async def done_habit(message: types.Message):
    habit_name = message.text.split()[1]
    user_id = message.from_user.id
    db.update_habit_progress(user_id, habit_name)
    await message.answer(f"Прогресс привычки '{habit_name}' обновлён!")

@dp.message_handler(commands=['delete_habit'])
async def delete_habit(message: types.Message):
    habit_name = message.text.split()[1]
    user_id = message.from_user.id
    db.delete_habit(user_id, habit_name)
    await message.answer(f"Привычка '{habit_name}' удалена.")

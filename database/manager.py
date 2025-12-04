import sqlite3
import os

# Путь к БДsqlite3 имя_файла.db
DB_PATH = "database.db"

def init_db():
    """Инициализирует базу данных — создаёт таблицу habits, если её нет."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            period TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT NOT NULL,
        email TEXT NOT NULL
    )
''')

    conn.commit()
    conn.close()
    print("Таблица habits создана/проверена.")

def add_habit(user_id: int, name: str, period: str) -> int:
    """Добавляет привычку в БД и возвращает её ID."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO habits (user_id, name, period, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)',
            (user_id, name, period)
        )
        conn.commit()
        habit_id = cur.lastrowid
        return habit_id
    except sqlite3.Error as e:
        print(f"Ошибка при добавлении привычки: {e}")
        raise
    finally:
        if conn:
            conn.close()

def list_habits() -> list:
    """Возвращает список всех привычек из БД."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT * FROM habits')
    habits = cur.fetchall()
    conn.close()
    return habits

if __name__ == "__main__":
    # Запуск инициализации БД при запуске скрипта
    init_db()
    print("База данных готова.")

    # Пример добавления привычки (можно убрать или закомментировать)
    # habit_id = add_habit(1, "Читать книгу", "ежедневно")
    # print(f"Добавлена привычка с ID: {habit_id}")

    # Пример вывода списка привычек
    habits = list_habits()
    print("Список привычек:")
    for habit in habits:
        print(habit)




def add_user(user_id: int, username: str, email: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO users (user_id, username, email) VALUES (?, ?, ?)',
        (user_id, username, email)
    )
    conn.commit()
    conn.close()
    return user_id

def remove_habit(habit_id: int) -> bool:
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0  # Возвращает True, если строка удалена


def add_entry(user_id: int, habit_id: int, completed: bool, date: str) -> bool:
    """
    Добавляет новую запись о выполнении привычки.
    
    :param user_id: ID пользователя
    :param habit_id: ID привычки
    :param completed: Выполнена ли привычка (True/False)
    :param date: Дата выполнения (в формате YYYY-MM-DD)
    :return: True, если запись добавлена, False — в случае ошибки
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO entries (user_id, habit_id, completed, date) VALUES (?, ?, ?, ?)",
            (user_id, habit_id, completed, date)
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Ошибка при добавлении записи: {e}")
        return False
    finally:
        conn.close()

def get_stats(user_id: int) -> dict:
    """
    Получает статистику выполнения привычек для пользователя.
    
    :param user_id: ID пользователя
    :return: Словарь с данными о статистике
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Получаем общее количество записей и выполненных привычек
        cursor.execute(
            "SELECT COUNT(*), SUM(completed) FROM entries WHERE user_id = ?",
            (user_id,)
        )
        total, completed = cursor.fetchone()
        
        # Рассчитываем процент выполнения
        completion_rate = (completed / total) * 100 if total > 0 else 0
        
        return {
            "total_entries": total,
            "completed_entries": completed,
            "completion_rate": round(completion_rate, 2)
        }
    except sqlite3.Error as e:
        print(f"Ошибка при получении статистики: {e}")
        return {}
    finally:
        conn.close()

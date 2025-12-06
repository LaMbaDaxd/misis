import sqlite3
from datetime import datetime, date
from typing import List, Dict, Any

from config.settings import DATABASE_PATH
from models.user import User
from models.habit import Habit

DB_PATH = DATABASE_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    first_name  TEXT,
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS habits (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    name       TEXT NOT NULL,
    period     TEXT NOT NULL,          -- например: daily / weekly / custom
    created_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS entries (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id   INTEGER NOT NULL,
    date       TEXT NOT NULL,
    done       INTEGER NOT NULL DEFAULT 1,
    note       TEXT,
    created_at TEXT,
    FOREIGN KEY (habit_id) REFERENCES habits(id)
);
"""


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    """Создаёт файл базы данных и таблицы, если их ещё нет."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def get_or_create_user(user_id: int, username: str | None, first_name: str | None) -> User:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, username, first_name FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = cur.fetchone()
        if row:
            return User(user_id=row[0], username=row[1], first_name=row[2])

        created_at = datetime.utcnow().isoformat()
        cur.execute(
            "INSERT INTO users (user_id, username, first_name, created_at) VALUES (?, ?, ?, ?)",
            (user_id, username, first_name, created_at),
        )
        conn.commit()
        return User(user_id=user_id, username=username, first_name=first_name)
    finally:
        conn.close()


def add_habit(user_id: int, name: str, period: str) -> Habit:
    """Добавляет новую привычку пользователю."""
    conn = get_connection()
    try:
        created_at = datetime.utcnow().isoformat()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO habits (user_id, name, period, created_at) VALUES (?, ?, ?, ?)",
            (user_id, name, period, created_at),
        )
        habit_id = cur.lastrowid
        conn.commit()
        return Habit(id=habit_id, user_id=user_id, name=name, period=period)
    finally:
        conn.close()


def list_habits(user_id: int) -> List[Habit]:
    """Возвращает список привычек пользователя."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, user_id, name, period FROM habits WHERE user_id = ? ORDER BY id",
            (user_id,),
        )
        rows = cur.fetchall()
        return [Habit(id=row[0], user_id=row[1], name=row[2], period=row[3]) for row in rows]
    finally:
        conn.close()


def add_entry(
    habit_id: int,
    on_date: date | None = None,
    done: bool = True,
    note: str | None = None,
) -> None:
    """Добавляет отметку выполнения привычки."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        if on_date is None:
            on_date = date.today()
        created_at = datetime.utcnow().isoformat()
        cur.execute(
            "INSERT INTO entries (habit_id, date, done, note, created_at) VALUES (?, ?, ?, ?, ?)",
            (habit_id, on_date.isoformat(), int(done), note, created_at),
        )
        conn.commit()
    finally:
        conn.close()


def get_stats(user_id: int) -> Dict[int, Dict[str, Any]]:
    """
    Простая статистика: по каждой привычке — сколько всего записей и сколько выполнений.
    Возвращает словарь {habit_id: {"total": ..., "done": ...}}
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM habits WHERE user_id = ?", (user_id,))
        habits = cur.fetchall()
        out: Dict[int, Dict[str, Any]] = {}
        for (hid,) in habits:
            cur.execute("SELECT COUNT(*) FROM entries WHERE habit_id = ?", (hid,))
            total = cur.fetchone()[0] or 0
            cur.execute("SELECT COUNT(*) FROM entries WHERE habit_id = ? AND done = 1", (hid,))
            done = cur.fetchone()[0] or 0
            out[hid] = {"total": total, "done": done}
        return out
    finally:
        conn.close()

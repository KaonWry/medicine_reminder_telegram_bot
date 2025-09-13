import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "reminders.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            time TEXT NOT NULL,
            triggered_today INTEGER DEFAULT 0
        )
        """
    )


if __name__ == "__main__":
    init_db()

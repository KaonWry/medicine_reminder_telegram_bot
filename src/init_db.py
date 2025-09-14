import sqlite3
import os

# Always create DB in /src
db_dir = os.path.dirname(__file__)
DB_PATH = os.path.join(db_dir, "reminders.db")


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
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()

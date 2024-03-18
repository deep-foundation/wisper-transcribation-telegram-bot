import asyncio
import sqlite3
import threading

user_cache = {}
db_lock = threading.Lock()
db_name = "users.db"

def create_database():
    with db_lock:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                user_id INTEGER UNIQUE,
                email TEXT,
                max_minutes INTEGER DEFAULT 0,
                used_minutes INTEGER DEFAULT 0,
                userPassword TEXT,
                auth_token TEXT
            )
        """)
        conn.commit()
        conn.close()


def get_user_email(user_id):
    if user_id in user_cache:
        return user_cache[user_id]

    with db_lock, sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users WHERE user_id = ?", (user_id,))
        email = cursor.fetchone()

    if email:
        user_cache[user_id] = email[0]
        return email[0]
    return None


def add_user(user_id, email):
    with db_lock, sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (user_id, email) VALUES (?, ?)", (user_id, email))
        conn.commit()

    user_cache[user_id] = email


def check_user_in_db(user_id):
    with db_lock, sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

    return user is not None


async def async_add_user(user_id, email):
    await asyncio.to_thread(add_user, user_id, email)


async def async_get_user_email(user_id):
    return await asyncio.to_thread(get_user_email, user_id)


def update_minutes(user_id, max_minutes=None, used_minutes=None):
    with db_lock, sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        if max_minutes is not None:
            cursor.execute("UPDATE users SET max_minutes = ? WHERE user_id = ?", (max_minutes, user_id))
        if used_minutes is not None:
            cursor.execute("UPDATE users SET used_minutes = ? WHERE user_id = ?", (used_minutes, user_id))
        conn.commit()


def get_user_minutes(user_id):
    with db_lock, sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT max_minutes, used_minutes FROM users WHERE user_id = ?", (user_id,))
        data = cursor.fetchone()

    return data if data else (0, 0)


async def async_update_minutes(user_id, max_minutes=None, used_minutes=None):
    await asyncio.to_thread(update_minutes, user_id, max_minutes, used_minutes)


async def async_get_user_minutes(user_id):
    return await asyncio.to_thread(get_user_minutes, user_id)


def check_token_in_db(user_id):
    with db_lock, sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT auth_token FROM users WHERE user_id = ?", (user_id,))
        token = cursor.fetchone()

    return token[0] if token else None


def write_token_to_db(user_id, token):
    with db_lock, sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET auth_token = ? WHERE user_id = ?", (token, user_id))
        conn.commit()


def add_user_password(user_id, password):
    with db_lock, sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET userPassword = ? WHERE user_id = ?", (password, user_id))
        conn.commit()


def get_user_password(user_id):
    with db_lock, sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT userPassword FROM users WHERE user_id = ?", (user_id,))
        password = cursor.fetchone()

    return password[0] if password else None


if __name__ == '__main__':
    create_database()

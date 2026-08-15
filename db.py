"""Простой синхронный слой работы с SQLite (для такого масштаба бота — достаточно)."""
import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.environ.get("DB_PATH", "data/bot.db")


@contextmanager
def get_conn():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            name TEXT,
            city TEXT,
            mode TEXT,
            avatar_file_id TEXT,
            avatar_type TEXT,
            profile_complete INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS swipes (
            from_id INTEGER,
            to_id INTEGER,
            action TEXT CHECK(action IN ('like','dislike')),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (from_id, to_id)
        );

        CREATE TABLE IF NOT EXISTS active_chats (
            user_id INTEGER PRIMARY KEY,
            partner_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS friend_requests (
            from_id INTEGER,
            to_id INTEGER,
            status TEXT DEFAULT 'pending',
            PRIMARY KEY (from_id, to_id)
        );
        """)


def upsert_user(user_id: int, username: str | None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO users (user_id, username) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET username=excluded.username",
            (user_id, username),
        )


def set_field(user_id: int, field: str, value):
    assert field in ("name", "city", "mode", "avatar_file_id", "avatar_type", "profile_complete")
    with get_conn() as conn:
        conn.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (value, user_id))


def get_user(user_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else None


def is_profile_complete(user_id: int) -> bool:
    u = get_user(user_id)
    return bool(u and u["profile_complete"])


def record_swipe(from_id: int, to_id: int, action: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO swipes (from_id, to_id, action) VALUES (?, ?, ?) "
            "ON CONFLICT(from_id, to_id) DO UPDATE SET action=excluded.action",
            (from_id, to_id, action),
        )


def has_mutual_like(user_a: int, user_b: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM swipes WHERE from_id=? AND to_id=? AND action='like'",
            (user_b, user_a),
        ).fetchone()
        return row is not None


def reset_swipes(user_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM swipes WHERE from_id=?", (user_id,))


def get_candidates(user_id: int):
    """Все анкеты, которых пользователь ещё не оценивал (исключая себя)."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM users
            WHERE user_id != ?
              AND profile_complete = 1
              AND user_id NOT IN (SELECT to_id FROM swipes WHERE from_id=?)
            """,
            (user_id, user_id),
        ).fetchall()
        return [dict(r) for r in rows]


def get_likers(user_id: int):
    """Те, кто лайкнул user_id, но user_id их ещё не оценивал (не свайпал)."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT u.* FROM users u
            JOIN swipes s ON s.from_id = u.user_id
            WHERE s.to_id = ? AND s.action = 'like'
              AND u.user_id NOT IN (SELECT to_id FROM swipes WHERE from_id=?)
            """,
            (user_id, user_id),
        ).fetchall()
        return [dict(r) for r in rows]


def set_active_chat(user_a: int, user_b: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO active_chats (user_id, partner_id) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET partner_id=excluded.partner_id",
            (user_a, user_b),
        )
        conn.execute(
            "INSERT INTO active_chats (user_id, partner_id) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET partner_id=excluded.partner_id",
            (user_b, user_a),
        )


def get_active_chat_partner(user_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT partner_id FROM active_chats WHERE user_id=?", (user_id,)
        ).fetchone()
        return row["partner_id"] if row else None


def end_chat(user_id: int):
    partner_id = get_active_chat_partner(user_id)
    with get_conn() as conn:
        conn.execute("DELETE FROM active_chats WHERE user_id=?", (user_id,))
        if partner_id:
            conn.execute("DELETE FROM active_chats WHERE user_id=?", (partner_id,))
    return partner_id


def create_friend_request(from_id: int, to_id: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO friend_requests (from_id, to_id) VALUES (?, ?) "
            "ON CONFLICT(from_id, to_id) DO UPDATE SET status='pending'",
            (from_id, to_id),
        )


def accept_friend_request(from_id: int, to_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE friend_requests SET status='accepted' WHERE from_id=? AND to_id=?",
            (from_id, to_id),
      )

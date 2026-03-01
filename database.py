# -*- coding: utf-8 -*-
"""SQLite база данных для To-Do бота."""

import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).parent / "todo.db"
TODAY = date.today().isoformat()


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            recurring INTEGER NOT NULL DEFAULT 0,
            done_date TEXT
        )
    """)
    for col in ("recurring", "done_date"):
        try:
            conn.execute(f"ALTER TABLE tasks ADD COLUMN {col} " + (
                "INTEGER NOT NULL DEFAULT 0" if col == "recurring" else "TEXT"
            ))
        except sqlite3.OperationalError:
            pass
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)"
    )
    conn.execute("""
        CREATE TABLE IF NOT EXISTS completion_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_id INTEGER NOT NULL,
            completed_date TEXT NOT NULL
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_log_user ON completion_log(user_id)"
    )
    conn.commit()
    conn.close()


def add_task(user_id: int, text: str, recurring: int = 0) -> int:
    """Добавляет задачу. recurring: 0 = один раз, 1 = каждый день. Возвращает id."""
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO tasks (user_id, text, done, recurring) VALUES (?, ?, 0, ?)",
        (user_id, text.strip(), 1 if recurring else 0)
    )
    task_id = cur.lastrowid
    conn.commit()
    conn.close()
    return task_id


def get_tasks(user_id: int, done_only: bool = False):
    """Список задач. У ежедневных done = (done_date == сегодня)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, text, done, created_at, recurring, done_date FROM tasks WHERE user_id = ? ORDER BY id",
        (user_id,)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("recurring"):
            d["done"] = 1 if (d.get("done_date") or "")[:10] == TODAY else 0
        result.append(d)
    if done_only:
        result = [t for t in result if t["done"]]
    else:
        result.sort(key=lambda t: (0 if t["done"] else 1, t["id"]))
    return result


def set_done(user_id: int, task_id: int) -> bool:
    """Отмечает задачу выполненной. Ежедневная — обновляет done_date на сегодня и пишет в лог."""
    conn = get_connection()
    row = conn.execute(
        "SELECT id, recurring FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, user_id)
    ).fetchone()
    if not row:
        conn.close()
        return False
    recurring = row["recurring"]
    if recurring:
        conn.execute(
            "UPDATE tasks SET done_date = ? WHERE id = ? AND user_id = ?",
            (TODAY, task_id, user_id)
        )
        conn.execute(
            "INSERT INTO completion_log (user_id, task_id, completed_date) VALUES (?, ?, ?)",
            (user_id, task_id, TODAY)
        )
    else:
        conn.execute(
            "UPDATE tasks SET done = 1 WHERE id = ? AND user_id = ?",
            (task_id, user_id)
        )
        conn.execute(
            "INSERT INTO completion_log (user_id, task_id, completed_date) VALUES (?, ?, ?)",
            (user_id, task_id, TODAY)
        )
    conn.commit()
    conn.close()
    return True


def _get_completion_dates(user_id: int) -> list:
    """Уникальные даты, когда пользователь что-то отмечал выполненным (по убыванию)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT completed_date FROM completion_log WHERE user_id = ? ORDER BY completed_date DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [r["completed_date"][:10] for r in rows]


def get_stats(user_id: int) -> dict:
    """Статистика: активные дни, серия, всего выполнено."""
    dates = _get_completion_dates(user_id)
    if not dates:
        return {"active_days": 0, "current_streak": 0, "longest_streak": 0, "total_completions": 0}
    conn = get_connection()
    total = conn.execute(
        "SELECT COUNT(*) AS n FROM completion_log WHERE user_id = ?", (user_id,)
    ).fetchone()["n"]
    conn.close()
    from datetime import datetime, timedelta
    today = date.today().isoformat()
    sorted_dates = sorted(set(dates), reverse=True)
    current_streak = 0
    d = date.today()
    for _ in range(400):
        s = d.isoformat()
        if s in sorted_dates or s in dates:
            current_streak += 1
            d -= timedelta(days=1)
        else:
            break
    longest = 0
    run = 0
    prev = None
    for d_str in sorted_dates:
        try:
            d = datetime.strptime(d_str[:10], "%Y-%m-%d").date()
        except Exception:
            continue
        if prev is None or (prev - d).days == 1:
            run += 1
        else:
            run = 1
        prev = d
        longest = max(longest, run)
    return {
        "active_days": len(set(dates)),
        "current_streak": current_streak,
        "longest_streak": longest,
        "total_completions": total,
    }


def delete_task(user_id: int, task_id: int) -> bool:
    """Удаляет задачу. Возвращает True, если задача найдена."""
    conn = get_connection()
    cur = conn.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, user_id)
    )
    ok = cur.rowcount > 0
    conn.commit()
    conn.close()
    return ok


def get_task_by_id(user_id: int, task_id: int):
    """Возвращает одну задачу по id или None (с полями recurring, done по правилам)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT id, text, done, created_at, recurring, done_date FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, user_id)
    ).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    if d.get("recurring"):
        d["done"] = 1 if (d.get("done_date") or "")[:10] == TODAY else 0
    return d

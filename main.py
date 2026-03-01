# -*- coding: utf-8 -*-
"""Telegram To-Do бот с SQLite."""

import os
import logging
from pathlib import Path

# Подгрузка .env из папки бота (токен не вводить в терминале)
def _load_dotenv(path: Path) -> bool:
    """Читает .env. Возвращает True, если файл найден и прочитан."""
    try:
        if not path.exists():
            return False
        text = path.read_text(encoding="utf-8-sig")
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip().lstrip("\ufeff")
            value = value.strip().strip("'\"")
            if key:
                os.environ.setdefault(key, value)
        return True
    except Exception:
        return False

_SCRIPT_DIR = Path(__file__).resolve().parent
_env_path = _SCRIPT_DIR / ".env"
if not _load_dotenv(_env_path):
    _load_dotenv(Path.cwd() / ".env")

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import database as db

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Токен: из .env или из переменной окружения BOT_TOKEN
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Постоянная клавиатура
MAIN_MENU_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📋 Мой список"), KeyboardButton("➕ Новая задача")],
        [KeyboardButton("📊 Статистика")],
    ],
    resize_keyboard=True,
)


def format_tasks(tasks: list, show_date: bool = True) -> str:
    """Секции «В работе» и «Сделано»; ежедневные помечены 🔄."""
    if not tasks:
        return ""
    todo = [t for t in tasks if not t["done"]]
    done = [t for t in tasks if t["done"]]
    lines = []
    def line(t):
        recur = " 🔄" if t.get("recurring") else ""
        date_str = f" · {t['created_at'][:10]}" if show_date and t.get("created_at") else ""
        return f"  {t['id']}. {t['text']}{recur}{date_str}"
    if todo:
        lines.append("📌 В работе")
        lines.append("")
        for t in todo:
            lines.append(line(t))
        lines.append("")
    if done:
        lines.append("✅ Сделано")
        lines.append("")
        for t in done:
            lines.append(line(t))
    return "\n".join(lines).strip()


def build_list_keyboard(tasks: list, max_tasks: int = 25):
    """Инлайн-кнопки: у каждой задачи — Готово / Удалить, внизу — Обновить."""
    if not tasks:
        return None
    rows = []
    for t in tasks[:max_tasks]:
        task_id = t["id"]
        if t["done"]:
            rows.append([
                InlineKeyboardButton("🗑", callback_data=f"del:{task_id}"),
            ])
        else:
            rows.append([
                InlineKeyboardButton("✅ Сделано", callback_data=f"done:{task_id}"),
                InlineKeyboardButton("🗑", callback_data=f"del:{task_id}"),
            ])
    rows.append([InlineKeyboardButton("🔄 Обновить список", callback_data="refresh")])
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = update.effective_user.first_name or "друг"
    await update.message.reply_text(
        f"Привет, {name}! 👋\n\n"
        "Список дел: одноразовые задачи и ежедневные (обновляются каждый день).\n\n"
        "📋 Мой список — задачи и отметки\n"
        "➕ Новая задача — добавить (один раз или каждый день)\n"
        "📊 Статистика — дни и серии",
        reply_markup=MAIN_MENU_KEYBOARD,
    )


async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text(
            "Напиши задачу после команды, например:\n/add Купить молоко",
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        return
    text = " ".join(context.args)
    task_id = db.add_task(user_id, text, recurring=0)
    await update.message.reply_text(
        f"✨ Добавлено (одноразово):\n{text}",
        reply_markup=MAIN_MENU_KEYBOARD,
    )


async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    tasks = db.get_tasks(user_id)
    if not tasks:
        await update.message.reply_text(
            "Здесь пока пусто ✨\n\nНажми «➕ Новая задача» и добавь первое дело.",
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        return
    text = format_tasks(tasks)
    keyboard = build_list_keyboard(tasks)
    total = len(tasks)
    done_count = sum(1 for t in tasks if t["done"])
    header = f"📋 Твои задачи ({done_count}/{total} сделано)\n\n"
    await update.message.reply_text(header + text, reply_markup=keyboard)


async def done_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Напиши номер задачи, например: /done 2")
        return
    task_id = int(context.args[0])
    if db.set_done(user_id, task_id):
        await update.message.reply_text(f"✅ Отлично! Задача #{task_id} в «Сделано».", reply_markup=MAIN_MENU_KEYBOARD)
    else:
        await update.message.reply_text("Такой задачи нет или она уже выполнена 🤔")


async def delete_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Напиши номер задачи, например: /delete 2")
        return
    task_id = int(context.args[0])
    if db.delete_task(user_id, task_id):
        await update.message.reply_text(f"🗑 Удалено.", reply_markup=MAIN_MENU_KEYBOARD)
    else:
        await update.message.reply_text("Такой задачи нет 🤔")


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает статистику: дни, серия, всего выполнено."""
    user_id = update.effective_user.id
    s = db.get_stats(user_id)
    if s["active_days"] == 0:
        msg = (
            "📊 Статистика\n\n"
            "Пока пусто. Отмечай задачи выполненными — здесь появятся дни и серии."
        )
    else:
        msg = (
            "📊 Статистика\n\n"
            f"Дней с выполнением: {s['active_days']}\n"
            f"Текущая серия (дней подряд): {s['current_streak']}\n"
            f"Лучшая серия: {s['longest_streak']}\n"
            f"Всего отметок «сделано»: {s['total_completions']}"
        )
    await update.message.reply_text(msg, reply_markup=MAIN_MENU_KEYBOARD)


async def _send_list(update_or_msg, user_id: int, reply_fn):
    """Отправляет список задач (или пустое состояние)."""
    tasks = db.get_tasks(user_id)
    if not tasks:
        await reply_fn(
            "Здесь пока пусто ✨\n\nНажми «➕ Новая задача» и добавь первое дело.",
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        return
    body = format_tasks(tasks)
    header = f"📋 Твои задачи ({sum(1 for t in tasks if t['done'])}/{len(tasks)} сделано)\n\n"
    await reply_fn(header + body, reply_markup=build_list_keyboard(tasks))


async def menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка кнопок меню: Мой список / Новая задача."""
    user_id = update.effective_user.id
    text = (update.message.text or "").strip()

    if context.user_data.get("waiting_add"):
        context.user_data["waiting_add"] = False
        if text == "📋 Мой список":
            await _send_list(update, user_id, update.message.reply_text)
            return
        if text == "➕ Новая задача":
            context.user_data["waiting_add"] = True
            await update.message.reply_text(
                "Напиши задачу одним сообщением 👇",
                reply_markup=MAIN_MENU_KEYBOARD,
            )
            return
        if text == "📊 Статистика":
            await show_stats(update, context)
            return
        if not text:
            await update.message.reply_text(
                "Текст пустой — нажми «➕ Новая задача» и введи дело.",
                reply_markup=MAIN_MENU_KEYBOARD,
            )
            return
        context.user_data["pending_task"] = text
        await update.message.reply_text(
            "Один раз или повторять каждый день?",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Один раз", callback_data="addtask:0"),
                    InlineKeyboardButton("🔄 Каждый день", callback_data="addtask:1"),
                ],
            ]),
        )
        return

    if text == "📋 Мой список":
        await _send_list(update, user_id, update.message.reply_text)
        return
    if text == "➕ Новая задача":
        context.user_data["waiting_add"] = True
        await update.message.reply_text(
            "Напиши задачу одним сообщением 👇",
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        return
    if text == "📊 Статистика":
        await show_stats(update, context)
        return

    await update.message.reply_text(
        "Используй кнопки ниже 👇 или команды /add и /list.",
        reply_markup=MAIN_MENU_KEYBOARD,
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка инлайн-кнопок: Сделано / Удалить / Обновить / выбор типа задачи."""
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data or ""

    if data in ("addtask:0", "addtask:1"):
        recurring = 1 if data == "addtask:1" else 0
        pending = context.user_data.pop("pending_task", None)
        if not pending:
            await query.answer("Уже добавлено или отменено", show_alert=True)
            return
        db.add_task(user_id, pending, recurring=recurring)
        label = "каждый день 🔄" if recurring else "одноразово"
        await query.answer("Добавлено!")
        try:
            await query.edit_message_text(
                f"✨ Добавлено ({label}):\n{pending}",
                reply_markup=MAIN_MENU_KEYBOARD,
            )
        except Exception:
            pass
        return

    if data == "refresh":
        await query.answer("Обновлено")
        tasks = db.get_tasks(user_id)
        if not tasks:
            try:
                await query.edit_message_text(
                    "Здесь пока пусто ✨\n\nНажми «➕ Новая задача» и добавь первое дело.",
                    reply_markup=MAIN_MENU_KEYBOARD,
                )
            except Exception:
                pass
            return
        header = f"📋 Твои задачи ({sum(1 for t in tasks if t['done'])}/{len(tasks)} сделано)\n\n"
        text = header + format_tasks(tasks)
        try:
            await query.edit_message_text(text=text, reply_markup=build_list_keyboard(tasks))
        except Exception:
            pass
        return

    if ":" not in data:
        await query.answer()
        return
    action, task_id_str = data.split(":", 1)
    if not task_id_str.isdigit():
        await query.answer()
        return
    task_id = int(task_id_str)
    if action == "done":
        if db.set_done(user_id, task_id):
            await query.answer("✅ В «Сделано»!")
        else:
            await query.answer("Задача не найдена или уже выполнена", show_alert=True)
    elif action == "del":
        if db.delete_task(user_id, task_id):
            await query.answer("Удалено 🗑")
        else:
            await query.answer("Задача не найдена", show_alert=True)
    else:
        await query.answer()
        return

    tasks = db.get_tasks(user_id)
    if not tasks:
        try:
            await query.edit_message_text(
                "Здесь пока пусто ✨\n\nНажми «➕ Новая задача» и добавь первое дело.",
                reply_markup=MAIN_MENU_KEYBOARD,
            )
        except Exception:
            pass
        return
    header = f"📋 Твои задачи ({sum(1 for t in tasks if t['done'])}/{len(tasks)} сделано)\n\n"
    try:
        await query.edit_message_text(
            text=header + format_tasks(tasks),
            reply_markup=build_list_keyboard(tasks),
        )
    except Exception:
        pass


def main() -> None:
    global BOT_TOKEN
    if not BOT_TOKEN:
        # Запас: файл token.txt в папке с ботом (одна строка — токен)
        _token_file = _SCRIPT_DIR / "token.txt"
        try:
            if _token_file.exists():
                BOT_TOKEN = _token_file.read_text(encoding="utf-8-sig").strip().strip("'\"")
        except Exception:
            pass
    if not BOT_TOKEN:
        logger.error(
            "BOT_TOKEN не найден. В папке %s создай файл token.txt с одной строкой — твой токен от @BotFather (или .env с строкой BOT_TOKEN=токен).",
            _SCRIPT_DIR,
        )
        return
    db.init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_task))
    app.add_handler(CommandHandler("list", list_tasks))
    app.add_handler(CommandHandler("done", done_task))
    app.add_handler(CommandHandler("delete", delete_task))
    app.add_handler(CommandHandler("stats", show_stats))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, menu_button),
    )
    app.add_handler(CallbackQueryHandler(button_callback))
    logger.info("Бот запущен.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

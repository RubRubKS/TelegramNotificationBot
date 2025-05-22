import json
import requests
from datetime import datetime, timedelta
from telegram import Bot
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackContext
)

TELEGRAM_BOT_TOKEN = "7751616332:AAHdlxK6eamRULFYslqCos8RKZFBGxmZ_zU"

def load_deadlines():
    try:
        response = requests.get("https://localhost:8080/api/v1/deadlines/{user_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Ошибка API: {e}")
        return []

async def check_deadlines(context: ContextTypes.DEFAULT_TYPE):

    deadlines = load_deadlines()
    if not deadlines:
        return

    now = datetime.now().date()
    for task in deadlines:
        due_date_str = task.get("dueDate")
        if not due_date_str:
            continue

        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            time_left = due_date - now

            if timedelta(days=0) <= time_left <= timedelta(days=1):
                chat_id = task["chat_id"]
                message = (
                    f"🔔 **Дедлайн!**\n"
                    f"📌 {task['subject']}\n"
                    f"📅 {due_date.strftime('%d.%m.%Y')} ({time_left.days} дн.)\n"
                    f"🔹 {task['description']}\n"
                    f"🔸 Важность: {task['importance']}\n"
                )
                await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
        except Exception as e:
            print(f"Ошибка в задаче {task.get('id')}: {e}")

async def check_all_deadlines(context: ContextTypes.DEFAULT_TYPE, chat_id: int = None):

    deadlines = load_deadlines()
    if not deadlines:
        return "Нет активных дедлайнов."

    now = datetime.now().date()
    messages = []

    for task in deadlines:
        if chat_id is not None and task.get("chat_id") != chat_id:
            continue

        due_date_str = task.get("dueDate")
        if not due_date_str:
            continue

        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            time_left = due_date - now

            status = ""
            if time_left < timedelta(days=0):
                status = "❌ ПРОСРОЧЕНО"
            elif timedelta(days=0) <= time_left <= timedelta(days=1):
                status = "🔥 СРОЧНО (сегодня-завтра)"
            elif timedelta(days=1) < time_left <= timedelta(days=3):
                status = "⚠️ Скоро (2-3 дня)"
            else:
                status = "✅ Впереди"

            message = (
                f"{status}\n"
                f"📌 {task['subject']}\n"
                f"📅 {due_date.strftime('%d.%m.%Y')} ({time_left.days} дн.)\n"
                f"🔹 {task['description']}\n"
                f"🔸 Важность: {task['importance']}\n"
                f"—————————————"
            )
            messages.append(message)
        except Exception as e:
            print(f"Ошибка в задаче {task.get('id')}: {e}")

    if not messages:
        return "Нет дедлайнов для отображения."

    return "\n\n".join(messages)

async def deadlines_command(update: Update, context: CallbackContext):
    await check_all_deadlines(context, update.effective_chat.id)

async def periodic_check(context: CallbackContext):
    deadlines = load_deadlines()
    if not deadlines:
        return
    chat_ids = {task["chat_id"] for task in deadlines if "chat_id" in task}

    for chat_id in chat_ids:
        await check_all_deadlines(context, chat_id)

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Привет! Я бот для отслеживания дедлайнов.\n"
        "Используй /deadlines чтобы проверить все свои дедлайны."
    )

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("deadlines", deadlines_command))
    app.job_queue.run_repeating(periodic_check, interval=3600, first=10)
    app.run_polling()

if __name__ == "__main__":
    main()
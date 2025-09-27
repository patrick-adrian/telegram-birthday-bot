import logging
import sqlite3
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from dotenv import load_dotenv
import os
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# --- Setup logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Database Setup ---
conn = sqlite3.connect("birthdays.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS birthdays (
    username TEXT PRIMARY KEY,
    date TEXT
)
""")
conn.commit()

# --- Bot Commands ---
async def add_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /add_birthday @username YYYY-MM-DD")
        return
    username, date_str = context.args
    try:
        datetime.strptime(date_str, "%Y-%m-%d")  # validate format
        cursor.execute("REPLACE INTO birthdays VALUES (?, ?)", (username, date_str))
        conn.commit()
        await update.message.reply_text(f"🎂 Birthday for {username} set to {date_str}")
    except ValueError:
        await update.message.reply_text("Invalid date format. Use YYYY-MM-DD.")

async def list_birthdays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT username, date FROM birthdays")
    rows = cursor.fetchall()
    if not rows:
        await update.message.reply_text("No birthdays set.")
    else:
        msg = "🎉 Saved birthdays:\n" + "\n".join([f"{u}: {d}" for u, d in rows])
        await update.message.reply_text(msg)

async def remove_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /remove_birthday @username")
        return
    username = context.args[0]
    cursor.execute("DELETE FROM birthdays WHERE username=?", (username,))
    conn.commit()
    await update.message.reply_text(f"Removed birthday for {username}.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type in ["group", "supergroup"]:
        cursor.execute("CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY)")
        cursor.execute("INSERT OR IGNORE INTO chats VALUES (?)", (chat.id,))
        conn.commit()
        await update.message.reply_text("👋 Birthday bot active in this group!")
    else:
        await update.message.reply_text("Hi! Use me in private chat to add birthdays.")

# --- Birthday Checker ---
async def check_birthdays(application: Application):
    today = datetime.now().strftime("%m-%d")
    cursor.execute("SELECT username, date FROM birthdays")
    birthdays = cursor.fetchall()
    if not birthdays:
        return

    cursor.execute("SELECT id FROM chats")
    chats = cursor.fetchall()

    for username, date_str in birthdays:
        if datetime.strptime(date_str, "%Y-%m-%d").strftime("%m-%d") == today:
            for (chat_id,) in chats:
                await application.bot.send_message(
                    chat_id=chat_id,
                    text=f"🎂 Happy Birthday {username}! 🎉"
                )

# --- Main ---
def main():
    app = Application.builder().token(TOKEN).build()

    # Register commands
    app.add_handler(CommandHandler("add_birthday", add_birthday))
    app.add_handler(CommandHandler("list_birthdays", list_birthdays))
    app.add_handler(CommandHandler("remove_birthday", remove_birthday))
    app.add_handler(CommandHandler("start", start))


    # Scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: app.create_task(check_birthdays(app)),
                      trigger="cron", hour=0, minute=0)
    scheduler.start()

    logger.info("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()

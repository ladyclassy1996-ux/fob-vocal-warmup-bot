import sqlite3
from datetime import datetime, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.environ["BOT_TOKEN"]
DB_FILE = "warmup.db"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS completions (
            user_id INTEGER,
            username TEXT,
            full_name TEXT,
            date TEXT,
            PRIMARY KEY (user_id, date)
        )
    """)

    conn.commit()
    conn.close()


def today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ I COMPLETED TODAY'S WARM-UP",
                callback_data="completed"
            )
        ]
    ]

    await update.message.reply_text(
        "🎤 Welcome to the FOB 15-Minute Vocal Warm-Up Challenge!\n\n"
        "Complete your 15-minute vocal warm-up every day, "
        "then press the button below to check in.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def completed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    date = today()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO completions
        (user_id, username, full_name, date)
        VALUES (?, ?, ?, ?)
    """, (
        user.id,
        user.username or "",
        user.full_name,
        date
    ))

    conn.commit()
    conn.close()

    await query.edit_message_text(
        f"✅ {user.full_name} has checked in for today's "
        f"15-minute vocal warm-up!\n\n"
        f"📅 {date}\n"
        f"🎤 Keep singing!"
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM completions WHERE user_id = ?",
        (user.id,)
    )

    count = cursor.fetchone()[0]
    conn.close()

    await update.message.reply_text(
        f"📊 YOUR VOCAL WARM-UP STATS\n\n"
        f"🎤 Days completed: {count}\n"
        f"🔥 Keep building your streak!"
    )


def main():
    init_db()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(
        CallbackQueryHandler(completed, pattern="^completed$")
    )

    print("FOB Vocal Warm-Up Bot is running...")

    application.run_polling()


if name == "main":
    main()

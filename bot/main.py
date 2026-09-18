"""
SlydAI Bot - Main Entry Point
"""

import asyncio
import logging
import sys
import os
import threading

from flask import Flask

from telegram import BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import BOT_TOKEN
from database import db
from handlers import (
    cmd_start,
    cmd_admin,
    cmd_stats,
    cmd_help,
    cmd_cancel,
    handle_text,
    handle_callback,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# ── Health Check Server ───────────────────────────────────────────────────────

health_app = Flask(__name__)


@health_app.route("/")
def home():
    return "SlydAI Bot is running!", 200


@health_app.route("/health")
def health():
    return "OK", 200


def run_health_server():
    port = int(os.environ.get("PORT", 10000))

    health_app.run(
        host="0.0.0.0",
        port=port
    )


# ── Bot Setup ─────────────────────────────────────────────────────────────────

async def post_init(application: Application):
    """Runs after bot initializes — connect DB and set commands."""
    await db.connect()
    logger.info("✅ Database connected")

    commands = [
        BotCommand("start", "Botni ishga tushirish"),
        BotCommand("stats", "Mening statistikam"),
        BotCommand("help", "Yordam va qo'llanma"),
        BotCommand("cancel", "Jarayonni bekor qilish"),
    ]

    await application.bot.set_my_commands(commands)
    logger.info("✅ Bot commands set")

    me = await application.bot.get_me()
    logger.info("🤖 Bot started: @%s (%s)", me.username, me.first_name)


async def post_shutdown(application: Application):
    """Runs on shutdown — close DB."""
    await db.disconnect()
    logger.info("🔴 Database disconnected")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN not set in .env file!")
        sys.exit(1)

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # ── Command Handlers ──────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("cancel", cmd_cancel))

    # ── Callback Query Handler ────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(handle_callback))

    # ── Text Message Handler ──────────────────────────────────────────────────
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    logger.info("🚀 SlydAI Bot starting in polling mode...")

    app.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )


# ── Start Bot + Health Server ─────────────────────────────────────────────────

if __name__ == "__main__":

    # Render uchun HTTP serverni alohida thread'da ishga tushiramiz
    threading.Thread(
        target=run_health_server,
        daemon=True
    ).start()

    # Telegram botni ishga tushiramiz
    main()
"""
SlydAI Bot - Telegram Handlers
"""

import logging
from pathlib import Path
from typing import Optional

from telegram import Update, InputMediaPhoto, InputFile
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction

import messages as msg
import keyboards as kb
from ai_engine import generate_slides, format_all_slides, get_theme_preview_path
from pptx_engine import generate_pptx_file
from config import (
    CATEGORIES, THEME_DISPLAY_NAMES, PROMPTS_DIR,
    STATE_IDLE, STATE_CHOOSE_CATEGORY, STATE_CHOOSE_THEME,
    STATE_CHOOSE_SLIDES, STATE_ENTER_TOPIC, STATE_GENERATING,
)
from database import db

logger = logging.getLogger(__name__)

# ── Helper: safe_send ─────────────────────────────────────────────────────────

async def _safe_send(update: Update, text: str, **kwargs) -> None:
    """Send MarkdownV2 message, falling back to plain text on parse error."""
    try:
        if update.message:
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2, **kwargs)
        elif update.callback_query:
            await update.callback_query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2, **kwargs)
    except Exception:
        plain = text.replace("\\", "").replace("*", "").replace("_", "").replace("`", "")
        if update.message:
            await update.message.reply_text(plain, **kwargs)
        elif update.callback_query:
            await update.callback_query.message.reply_text(plain, **kwargs)


async def _safe_edit(update: Update, text: str, **kwargs) -> None:
    """Edit current message text safely."""
    try:
        await update.callback_query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN_V2, **kwargs
        )
    except Exception as e:
        logger.warning("edit_message_text failed: %s", e)
        await _safe_send(update, text, **kwargs)


# ── User Init ─────────────────────────────────────────────────────────────────

async def _init_user(update: Update) -> dict:
    tg_user = update.effective_user
    user = await db.get_or_create_user(tg_user)
    return user


def _get_session(context: ContextTypes.DEFAULT_TYPE) -> dict:
    if "session" not in context.user_data:
        context.user_data["session"] = {}
    return context.user_data["session"]


def _clear_session(context: ContextTypes.DEFAULT_TYPE):
    context.user_data["session"] = {}


# ── /start ────────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _init_user(update)
    _clear_session(context)

    # Check if truly new (joined_at == last_seen within 2 seconds)
    is_new = user.get("total_generations", 0) == 0

    text = msg.welcome_message(update.effective_user.first_name, is_new)
    await _safe_send(update, text, reply_markup=kb.main_menu_keyboard())


# ── /stats ────────────────────────────────────────────────────────────────────

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _init_user(update)
    stats = await db.get_user_stats(update.effective_user.id)
    text = msg.stats_message(stats, update.effective_user.first_name)
    await _safe_send(update, text)


# ── /help ─────────────────────────────────────────────────────────────────────

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _safe_send(update, msg.help_message())


# ── /cancel ───────────────────────────────────────────────────────────────────

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _clear_session(context)
    await _safe_send(
        update,
        "🏠 *Bekor qilindi\\. Asosiy menyu:*",
        reply_markup=kb.main_menu_keyboard(),
    )


# ── Text Message Handler ──────────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    session = _get_session(context)
    state = session.get("state", STATE_IDLE)

    if text == "🎨 Yangi Slayd Yaratish":
        await _start_generation_flow(update, context)

    elif text == "📊 Mening Statistikam":
        await cmd_stats(update, context)

    elif text == "ℹ️ Yordam":
        await cmd_help(update, context)

    elif state == STATE_ENTER_TOPIC:
        await _handle_topic_input(update, context, text)

    else:
        await _safe_send(
            update,
            "🏠 Asosiy menyu:",
            reply_markup=kb.main_menu_keyboard(),
        )


async def _start_generation_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check limit then show category picker."""
    await _init_user(update)
    allowed, used = await db.can_generate(update.effective_user.id)

    if not allowed:
        await _safe_send(
            update,
            msg.limit_reached_message(used),
            reply_markup=kb.limit_reached_keyboard(),
        )
        return

    _clear_session(context)
    session = _get_session(context)
    session["state"] = STATE_CHOOSE_CATEGORY

    await _safe_send(
        update,
        msg.choose_category_message(),
        reply_markup=kb.category_keyboard(),
    )


async def _handle_topic_input(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str):
    """Handle user's typed presentation topic."""
    if len(topic.strip()) < 5:
        await _safe_send(update, "⚠️ Iltimos, mavzuni to'liqroq yozing \\(kamida 5 belgi\\)\\.")
        return
    if len(topic) > 500:
        await _safe_send(update, "⚠️ Mavzu juda uzun\\. Iltimos 500 belgidan kam yozing\\.")
        return

    session = _get_session(context)
    session["topic"] = topic.strip()
    session["state"] = STATE_CHOOSE_SLIDES  # reuse state for confirmation

    theme_id = session.get("theme_id", "aurora")
    slide_count = session.get("slide_count", 10)
    theme_display = THEME_DISPLAY_NAMES.get(theme_id, theme_id)

    await _safe_send(
        update,
        msg.confirm_topic_message(topic, theme_display, slide_count),
        reply_markup=kb.confirm_topic_keyboard(),
    )


# ── Callback Query Handler ────────────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    session = _get_session(context)

    # ── Cancel ───────────────────────────────────────────────────────────────
    if data == "cancel":
        _clear_session(context)
        await query.edit_message_text("❌ Bekor qilindi\\.", parse_mode=ParseMode.MARKDOWN_V2)
        await _safe_send(update, "🏠 *Asosiy menyu:*", reply_markup=kb.main_menu_keyboard())
        return

    # ── Back to Category ──────────────────────────────────────────────────────
    if data == "back:category":
        session["state"] = STATE_CHOOSE_CATEGORY
        await _safe_edit(update, msg.choose_category_message(), reply_markup=kb.category_keyboard())
        return

    # ── Category Selected ─────────────────────────────────────────────────────
    if data.startswith("cat:"):
        category_name = data[4:]
        session["category"] = category_name
        session["state"] = STATE_CHOOSE_THEME
        await _safe_edit(
            update,
            msg.choose_theme_message(category_name),
            reply_markup=kb.theme_keyboard(category_name),
        )
        return

    # ── Theme Selected → show preview ─────────────────────────────────────────
    if data.startswith("theme:"):
        theme_id = data[6:]
        session["theme_id"] = theme_id
        session["preview_index"] = 0
        session["state"] = STATE_CHOOSE_THEME
        await _send_theme_preview(update, context, theme_id, 0)
        return

    # ── Preview Navigation ────────────────────────────────────────────────────
    if data.startswith("prev_img:") or data.startswith("next_img:"):
        parts = data.split(":")
        direction = parts[0]
        theme_id = parts[1]
        current = int(parts[2])
        new_index = current - 1 if direction == "prev_img" else current + 1
        session["preview_index"] = new_index
        await _send_theme_preview(update, context, theme_id, new_index)
        return

    # ── Back to Themes ────────────────────────────────────────────────────────
    if data.startswith("back_themes:"):
        category = session.get("category", "🚀 Pitch Decks")
        await _safe_edit(
            update,
            msg.choose_theme_message(category),
            reply_markup=kb.theme_keyboard(category),
        )
        return

    # ── Confirm Theme → Choose Slides ─────────────────────────────────────────
    if data.startswith("confirm_theme:"):
        theme_id = data[14:]
        session["theme_id"] = theme_id
        session["state"] = STATE_CHOOSE_SLIDES
        theme_display = THEME_DISPLAY_NAMES.get(theme_id, theme_id)
        await _safe_send(
            update,
            msg.choose_slides_message(theme_display),
            reply_markup=kb.slide_count_keyboard(),
        )
        return

    # ── Slide Count Selected ──────────────────────────────────────────────────
    if data.startswith("slides:"):
        slide_count = int(data[7:])
        session["slide_count"] = slide_count
        session["state"] = STATE_ENTER_TOPIC
        theme_id = session.get("theme_id", "aurora")
        theme_display = THEME_DISPLAY_NAMES.get(theme_id, theme_id)
        await _safe_edit(
            update,
            msg.enter_topic_message(theme_display, slide_count),
        )
        return

    # ── Back to Theme ─────────────────────────────────────────────────────────
    if data == "back:theme":
        category = session.get("category", "🚀 Pitch Decks")
        await _safe_edit(
            update,
            msg.choose_theme_message(category),
            reply_markup=kb.theme_keyboard(category),
        )
        return

    # ── Confirm Generate ──────────────────────────────────────────────────────
    if data == "confirm_generate":
        await _run_generation(update, context)
        return

    # ── Change Topic ──────────────────────────────────────────────────────────
    if data == "change_topic":
        theme_id = session.get("theme_id", "aurora")
        slide_count = session.get("slide_count", 10)
        theme_display = THEME_DISPLAY_NAMES.get(theme_id, theme_id)
        session["state"] = STATE_ENTER_TOPIC
        await _safe_edit(
            update,
            msg.enter_topic_message(theme_display, slide_count),
        )
        return

    # ── New Generation ────────────────────────────────────────────────────────
    if data in ("new_generation", "main_menu"):
        _clear_session(context)
        await _safe_send(update, "🏠 *Asosiy menyu:*", reply_markup=kb.main_menu_keyboard())
        return

    # ── Stats ─────────────────────────────────────────────────────────────────
    if data == "my_stats":
        stats = await db.get_user_stats(update.effective_user.id)
        text = msg.stats_message(stats, update.effective_user.first_name)
        await _safe_send(update, text)
        return

    # ── noop ──────────────────────────────────────────────────────────────────
    if data == "noop":
        return


# ── Theme Preview Sender ──────────────────────────────────────────────────────

async def _send_theme_preview(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    theme_id: str,
    image_index: int,
):
    """Send or update theme preview image with navigation buttons."""
    query = update.callback_query
    previews_dir = PROMPTS_DIR / theme_id / "previews"
    images = sorted(previews_dir.glob("*.webp")) if previews_dir.exists() else []
    total = len(images)

    theme_display = THEME_DISPLAY_NAMES.get(theme_id, theme_id.replace("-", " ").title())
    caption = msg.theme_preview_message(theme_id, theme_display)
    keyboard = kb.theme_preview_keyboard(theme_id, image_index, max(total, 1))

    if total == 0:
        # No preview images — just show text
        try:
            await query.edit_message_text(
                caption + "\n\n_\\(Preview mavjud emas\\)_",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard,
            )
        except Exception:
            await query.message.reply_text(
                caption,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard,
            )
        return

    idx = min(image_index, total - 1)
    image_path = images[idx]

    try:
        with open(image_path, "rb") as img_file:
            try:
                await query.edit_message_media(
                    media=InputMediaPhoto(
                        media=img_file,
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN_V2,
                    ),
                    reply_markup=keyboard,
                )
            except Exception:
                # If editing fails (e.g. original was text), send new photo
                img_file.seek(0)
                await query.message.reply_photo(
                    photo=img_file,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=keyboard,
                )
    except Exception as e:
        logger.error("Preview send error: %s", e)
        await _safe_send(update, caption, reply_markup=keyboard)


# ── Generation Runner ─────────────────────────────────────────────────────────

async def _run_generation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The core: check limit, generate slides, send results."""
    query = update.callback_query
    tg_user = update.effective_user
    session = _get_session(context)

    topic = session.get("topic", "")
    theme_id = session.get("theme_id", "aurora")
    slide_count = session.get("slide_count", 10)
    theme_display = THEME_DISPLAY_NAMES.get(theme_id, theme_id)

    # Final limit check
    allowed, used = await db.can_generate(tg_user.id)
    if not allowed:
        await _safe_send(
            update,
            msg.limit_reached_message(used),
            reply_markup=kb.limit_reached_keyboard(),
        )
        return

    # Show generating message
    session["state"] = STATE_GENERATING
    await _safe_edit(update, msg.generating_message(topic, slide_count))

    # Typing action
    await context.bot.send_chat_action(
        chat_id=tg_user.id,
        action=ChatAction.TYPING,
    )

    try:
        slides, raw = await generate_slides(topic, theme_id, slide_count)

        # Record in DB
        await db.record_generation(tg_user.id, topic, theme_id, len(slides))

        # Action: Upload document
        await context.bot.send_chat_action(
            chat_id=tg_user.id,
            action=ChatAction.UPLOAD_DOCUMENT,
        )

        # Generate styled PPTX file
        pptx_path = await generate_pptx_file(slides, theme_id, topic)

        # Get updated stats
        stats = await db.get_user_stats(tg_user.id)

        # Send PPTX Document
        caption = (
            f"🎉 *Prezentatsiya tayyor\\!*\n\n"
            f"📌 *Mavzu:* _{msg._escape(topic)}_\n"
            f"🎨 *Tema:* *{msg._escape(theme_display)}*\n"
            f"📑 *Slaydlar:* *{len(slides)} ta*\n\n"
            f"📊 _Bugungi limit: {stats['used_today']}/{stats['remaining_today'] + stats['used_today']} "
            f"\\(qolgan: {stats['remaining_today']}\\)_"
        )

        with open(pptx_path, "rb") as doc_f:
            await context.bot.send_document(
                chat_id=tg_user.id,
                document=doc_f,
                filename=pptx_path.name,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=kb.after_generation_keyboard(),
            )

        _clear_session(context)

    except Exception as e:
        logger.exception("Generation error: %s", e)
        await _safe_send(
            update,
            msg.error_message(str(e)),
            reply_markup=kb.main_menu_keyboard(),
        )
        _clear_session(context)

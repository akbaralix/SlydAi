"""
SlydAI Bot - Keyboard / Button Builders
"""

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from config import CATEGORIES, THEME_DISPLAY_NAMES, MIN_SLIDES, MAX_SLIDES


# ── Main Menu ─────────────────────────────────────────────────────────────────

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("🎨 Yangi Slayd Yaratish")],
        [KeyboardButton("📊 Mening Statistikam"), KeyboardButton("ℹ️ Yordam")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


# ── Category Selection ────────────────────────────────────────────────────────

def category_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for category_name in CATEGORIES:
        theme_count = len(CATEGORIES[category_name])
        buttons.append([
            InlineKeyboardButton(
                f"{category_name} ({theme_count})",
                callback_data=f"cat:{category_name}",
            )
        ])
    buttons.append([InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)


# ── Theme Selection ───────────────────────────────────────────────────────────

def theme_keyboard(category_name: str) -> InlineKeyboardMarkup:
    themes = CATEGORIES.get(category_name, [])
    buttons = []
    row = []
    for i, theme_id in enumerate(themes):
        display = THEME_DISPLAY_NAMES.get(theme_id, theme_id.replace("-", " ").title())
        row.append(InlineKeyboardButton(display, callback_data=f"theme:{theme_id}"))
        if len(row) == 2 or i == len(themes) - 1:
            buttons.append(row)
            row = []
    buttons.append([InlineKeyboardButton("◀️ Orqaga", callback_data="back:category")])
    buttons.append([InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)


# ── Theme Preview Navigation ──────────────────────────────────────────────────

def theme_preview_keyboard(theme_id: str, current_img: int, total_imgs: int) -> InlineKeyboardMarkup:
    nav_row = []
    if current_img > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"prev_img:{theme_id}:{current_img}"))
    nav_row.append(InlineKeyboardButton(f"🖼 {current_img + 1}/{total_imgs}", callback_data="noop"))
    if current_img < total_imgs - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"next_img:{theme_id}:{current_img}"))

    buttons = [
        nav_row,
        [InlineKeyboardButton("✅ Bu Temani Tanlash", callback_data=f"confirm_theme:{theme_id}")],
        [InlineKeyboardButton("◀️ Temalar ro'yxati", callback_data=f"back_themes:{theme_id}")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


# ── Slide Count Selection ─────────────────────────────────────────────────────

def slide_count_keyboard() -> InlineKeyboardMarkup:
    counts = [5, 7, 10, 12, 15, 20]
    buttons = []
    row = []
    for i, count in enumerate(counts):
        label = f"📑 {count} ta"
        row.append(InlineKeyboardButton(label, callback_data=f"slides:{count}"))
        if len(row) == 3 or i == len(counts) - 1:
            buttons.append(row)
            row = []
    buttons.append([InlineKeyboardButton("◀️ Orqaga", callback_data="back:theme")])
    buttons.append([InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)


# ── Confirm Topic ─────────────────────────────────────────────────────────────

def confirm_topic_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Yaratishni Boshlash!", callback_data="confirm_generate")],
        [InlineKeyboardButton("✏️ Mavzuni O'zgartirish", callback_data="change_topic")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")],
    ])


# ── Generation Complete ───────────────────────────────────────────────────────

def after_generation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Yangi Slayd Yaratish", callback_data="new_generation")],
        [InlineKeyboardButton("📤 Asosiy Menyu", callback_data="main_menu")],
    ])


# ── Limit Reached ─────────────────────────────────────────────────────────────

def limit_reached_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Statistikam", callback_data="my_stats")],
        [InlineKeyboardButton("🏠 Asosiy Menyu", callback_data="main_menu")],
    ])

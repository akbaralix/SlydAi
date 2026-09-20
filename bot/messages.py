"""
SlydAI Bot - Message Templates (Uzbek UI)
"""

from config import DAILY_LIMIT, MAX_SLIDES


def welcome_message(first_name: str, is_new: bool) -> str:
    if is_new:
        return (
            f"🎉 *Xush kelibsiz, {first_name}!*\n\n"
            f"Men *SlydAI* — sun'iy intellekt yordamida professional "
            f"prezentatsiyalar yaratuvchi botman\\.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"✨ *Nima qila olaman?*\n"
            f"• 81 ta professional dizayn temasi\n"
            f"• NUXTA AI bilan slayd generatsiyasi\n"
            f"• Kunlik {DAILY_LIMIT} ta bepul generatsiya\n"
            f"• Maksimal {MAX_SLIDES} ta slayd\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Boshlash uchun quyidagi tugmani bosing 👇"
        )
    return (
        f"👋 *Qaytib keldingiz, {first_name}\\!*\n\n"
        f"Nima yaratamiz bugun? 👇"
    )


def stats_message(stats: dict, first_name: str) -> str:
    joined = stats.get("joined_at")
    joined_str = joined.strftime("%d.%m.%Y") if joined else "—"
    return (
        f"📊 *{first_name} — Sizning Statistikangiz*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 Ro'yxatdan o'tgan: `{joined_str}`\n"
        f"🎞 Jami generatsiyalar: `{stats['total_generations']}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ *Bugungi limit:*\n"
        f"  Ishlatilgan: `{stats['used_today']}` / `{DAILY_LIMIT}`\n"
        f"  Qolgan: `{stats['remaining_today']}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )


def help_message() -> str:
    return (
        f"ℹ️ *SlydAI — Yordam Markazi*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"*Qanday ishlaydi?*\n\n"
        f"1️⃣ *\"🎨 Yangi Slayd Yaratish\"* tugmasini bosing\n"
        f"2️⃣ Prezentatsiya kategoriyasini tanlang\n"
        f"3️⃣ Dizayn temasini tanlang \\(preview bilan\\)\n"
        f"4️⃣ Slaydlar sonini tanlang\n"
        f"5️⃣ Prezentatsiya mavzusini yozing\n"
        f"6️⃣ AI slaydlarni yaratadi\\!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"*Limitlar:*\n"
        f"• Kunlik {DAILY_LIMIT} ta generatsiya \\(bepul\\)\n"
        f"• Maksimal {MAX_SLIDES} ta slayd\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"*Buyruqlar:*\n"
        f"/start — Boshidan boshlash\n"
        f"/stats — Statistika\n"
        f"/help — Yordam\n"
        f"/cancel — Jarayonni bekor qilish"
    )


def limit_reached_message(used: int) -> str:
    return (
        f"⛔ *Kunlik limit tugadi\\!*\n\n"
        f"Siz bugun `{used}/{DAILY_LIMIT}` generatsiyadan foydalandingiz\\.\n\n"
        f"⏰ Limit har kuni *00:00 UTC* da yangilanadi\\.\n\n"
        f"Ertaga qaytib keling\\! 🌅"
    )


def choose_category_message() -> str:
    return (
        f"🗂 *Kategoriya Tanlang*\n\n"
        f"Har bir kategoriyada turli stil va maqsaddagi "
        f"professional dizayn temalari mavjud\\.\n\n"
        f"👇 Kerakli kategoriyani tanlang:"
    )


def choose_theme_message(category: str) -> str:
    return (
        f"🎨 *{_escape(category)} — Tema Tanlang*\n\n"
        f"Har bir temani bosganingizda preview rasm ko'rsatiladi\\.\n"
        f"Yoqqan temani tasdiqlashingiz mumkin\\."
    )


def theme_preview_message(theme_id: str, display_name: str, description: str = "") -> str:
    desc = _escape(description[:200]) if description else ""
    return (
        f"🎨 *{_escape(display_name)}*\n\n"
        f"{desc}\n\n"
        f"👆 Preview rasmlarni o'ng/chap siljiting\n"
        f"✅ Yoqsa — *\"Bu Temani Tanlash\"* tugmasini bosing"
    )


def choose_slides_message(theme_display: str) -> str:
    return (
        f"📑 *Slaydlar Sonini Tanlang*\n\n"
        f"Tema: *{_escape(theme_display)}*\n\n"
        f"Nechta slayd kerak?\n"
        f"\\(Min: 5, Max: {MAX_SLIDES}\\)"
    )


def enter_topic_message(theme_display: str, slide_count: int) -> str:
    return (
        f"✍️ *Prezentatsiya Mavzusini Yozing*\n\n"
        f"Tema: *{_escape(theme_display)}*\n"
        f"Slaydlar: *{slide_count} ta*\n\n"
        f"Mavzuni qanchalik batafsil yozsangiz, "
        f"shunchalik sifatli natija olasiz\\.\n\n"
        f"*Masalan:*\n"
        f"• \"Sun'iy intellektning tibbiyotdagi ahamiyati\"\n"
        f"• \"Startup uchun investor pitch: FinTech sohasida\"\n"
        f"• \"O'zbekistonda turizm rivojlanishi 2024\\-2030\"\n\n"
        f"👇 Mavzuni yozing:"
    )


def confirm_topic_message(topic: str, theme_display: str, slide_count: int) -> str:
    return (
        f"✅ *Tasdiqlash*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 Mavzu: *{_escape(topic)}*\n"
        f"🎨 Tema: *{_escape(theme_display)}*\n"
        f"📑 Slaydlar: *{slide_count} ta*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Hamma narsa to'g'rimi? Yaratishni boshlaymizmi?"
    )


def generating_message(topic: str, slide_count: int) -> str:
    return (
        f"⏳ *Slaydlar Yaratilmoqda\\.\\.\\.*\n\n"
        f"📌 Mavzu: _{_escape(topic)}_\n"
        f"📑 Slaydlar: *{slide_count} ta*\n\n"
        f"🤖 SLYD AI ishlamoqda\\.\\.\\.\n"
        f"Bu 15\\-40 soniya vaqt olishi mumkin\\. Iltimos kuting\\."
    )


def generation_complete_message(topic: str, theme_display: str, slide_count: int) -> str:
    return (
        f"✅ *Tayyor\\!*\n\n"
        f"📌 Mavzu: _{_escape(topic)}_\n"
        f"🎨 Tema: *{_escape(theme_display)}*\n"
        f"📑 Jami slaydlar: *{slide_count} ta*\n\n"
        f"Yuqoridagi slaydlarni ko'rib chiqing\\!"
    )


def error_message(detail: str = "") -> str:
    msg = (
        f"❌ *Xatolik yuz berdi*\n\n"
        f"Generatsiyada muammo chiqdi\\. "
        f"Iltimos bir oz kutib qaytadan urinib ko'ring\\."
    )
    if detail:
        msg += f"\n\n`{_escape(detail[:100])}`"
    return msg


def admin_dashboard_message(stats: dict) -> str:
    top_themes_str = ""
    for i, t in enumerate(stats.get("top_themes", []), 1):
        top_themes_str += f"  {i}\\. `{_escape(t['_id'])}`: *{t['count']} marta*\n"
    if not top_themes_str:
        top_themes_str = "  _Hozircha ma'lumot yo'q_\n"

    return (
        f"👑 *SlydAI — Boshqaruv Paneli \\(Admin\\)*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 *Foydalanuvchilar:*\n"
        f"  • Jami a'zolar: *{stats['total_users']} ta*\n"
        f"  • Bugun qo'shilgan: *+{stats['users_today']} ta*\n"
        f"  • 7 kun ichida: *+{stats['users_week']} ta*\n"
        f"  • 30 kun ichida: *+{stats['users_month']} ta*\n"
        f"  • Faol \\(bugun\\): *{stats['active_today']} kishi*\n"
        f"  • Bloklanganlar: *{stats['blocked_users']} ta*\n\n"
        f"🎞 *Prezentatsiyalar \\(Generatsiyalar\\):*\n"
        f"  • Jami yaratilgan: *{stats['total_gens']} ta*\n"
        f"  • Bugun: *+{stats['gens_today']} ta*\n"
        f"  • 7 kun ichida: *+{stats['gens_week']} ta*\n"
        f"  • 30 kun ichida: *+{stats['gens_month']} ta*\n"
        f"  • O'rtacha slayd soni: *{stats['avg_slides']} ta*\n\n"
        f"🔥 *Eng mashhur temalar:*\n"
        f"{top_themes_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Quyidagi bo'limlardan birini tanlang 👇"
    )


def admin_user_info_message(user: dict, stats: dict) -> str:
    joined = user.get("joined_at")
    joined_str = joined.strftime("%d.%m.%Y %H:%M") if joined else "—"
    last_seen = user.get("last_seen")
    last_seen_str = last_seen.strftime("%d.%m.%Y %H:%M") if last_seen else "—"
    is_blocked = "🔴 Bloklangan" if user.get("is_blocked", False) else "🟢 Faol"

    username = f"@{user.get('username')}" if user.get("username") else "Mavjud emas"
    full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()

    return (
        f"👤 *Foydalanuvchi ma'lumotlari:*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: `{user.get('telegram_id')}`\n"
        f"🏷 Ism: *{_escape(full_name)}*\n"
        f"🔗 Username: {_escape(username)}\n"
        f"🛡 Holat: {is_blocked}\n"
        f"🎁 Qo'shimcha limit: `+{user.get('bonus_limit', 0)}`\n"
        f"📅 Ro'yxatdan o'tgan: `{joined_str}`\n"
        f"🕒 Oxirgi faollik: `{last_seen_str}`\n\n"
        f"📊 *Generatsiya statistikasi:*\n"
        f"• Jami yaratgan: *{user.get('total_generations', 0)} ta*\n"
        f"• Bugungi foydalanish: *{stats.get('used_today', 0)} ta*\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )


def _escape(text: str) -> str:
    """Escape MarkdownV2 special chars."""
    import re
    escape_chars = r"\_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", str(text))

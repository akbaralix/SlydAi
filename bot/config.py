"""
SlydAI Bot - Configuration & Constants
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Core Credentials ──────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/slydai")

# ── Limits ────────────────────────────────────────────────────────────────────
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", 2))
MAX_SLIDES = 20
MIN_SLIDES = 3

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
PROMPTS_DIR = BASE_DIR.parent / "themes" / "presentation-design-prompts" / "prompts"

# ── Conversation States ───────────────────────────────────────────────────────
(
    STATE_IDLE,
    STATE_CHOOSE_CATEGORY,
    STATE_CHOOSE_THEME,
    STATE_CHOOSE_SLIDES,
    STATE_ENTER_TOPIC,
    STATE_GENERATING,
) = range(6)

# ── Theme Categories ──────────────────────────────────────────────────────────
CATEGORIES = {
    "🚀 Pitch Decks": [
        "aurora", "demo-day", "hearth", "holo", "keynote-minimal",
        "midnight-pitch", "monolith", "runway", "spark", "term-sheet", "traction",
    ],
    "💼 Business & Strategy": [
        "atlas", "benchmark", "boardroom", "chevron", "harvey",
        "memo", "metro", "operator", "qbr", "six-pager", "whiteboard",
    ],
    "📊 Consulting": [
        "accenture-style", "bain-style", "bcg-style", "deloitte-style",
        "ey-style", "kpmg-style", "mckinsey-style", "pwc-style",
    ],
    "📣 Marketing & Brand": [
        "billboard", "bubblegum", "memphis", "outrun", "polaroid", "sorbet",
    ],
    "💻 Tech & Product": [
        "arcade", "circuit", "drafting-room", "mainframe", "telemetry", "wireframe",
    ],
    "🎨 Creative & Portfolio": [
        "art-deco", "atelier", "basel", "cinema", "collage", "coquette",
        "dark-academia", "logline", "lookbook", "manuscript", "marquee",
        "oat", "one-sheet", "origami", "passepartout", "scrapbook", "y2k",
    ],
    "📚 Education & Research": [
        "atrium", "chalkboard", "expedition", "field-notes", "herbarium",
        "level-up", "notebook", "observatory", "seminar", "syllabus",
        "ted-style", "trailhead", "wildflower",
    ],
    "💰 Finance": [
        "broadsheet", "ledger", "letterhead", "pitch-book", "ticker",
    ],
    "🎉 Events & Seasonal": [
        "christmas", "halloween", "quiz-night", "varsity",
    ],
}

# ── Theme Display Names ───────────────────────────────────────────────────────
THEME_DISPLAY_NAMES = {
    "aurora": "✨ Aurora",
    "demo-day": "🎯 Demo Day",
    "hearth": "🔥 Hearth",
    "holo": "🌈 Holo",
    "keynote-minimal": "🍎 Keynote Minimal",
    "midnight-pitch": "🌙 Midnight Pitch",
    "monolith": "⬛ Monolith",
    "runway": "✈️ Runway",
    "spark": "⚡ Spark",
    "term-sheet": "📋 Term Sheet",
    "traction": "📈 Traction",
    "atlas": "🗺️ Atlas",
    "benchmark": "📏 Benchmark",
    "boardroom": "🏛️ Boardroom",
    "chevron": "〉Chevron",
    "harvey": "⚖️ Harvey",
    "memo": "📝 Memo",
    "metro": "🚇 Metro",
    "operator": "🔧 Operator",
    "qbr": "📊 QBR",
    "six-pager": "📄 Six-Pager",
    "whiteboard": "🖊️ Whiteboard",
    "accenture-style": "🔷 Accenture Style",
    "bain-style": "🔴 Bain Style",
    "bcg-style": "🟢 BCG Style",
    "deloitte-style": "🟡 Deloitte Style",
    "ey-style": "🟠 EY Style",
    "kpmg-style": "🔵 KPMG Style",
    "mckinsey-style": "⚫ McKinsey Style",
    "pwc-style": "🟤 PwC Style",
    "billboard": "📌 Billboard",
    "bubblegum": "🍬 Bubblegum",
    "memphis": "🎸 Memphis",
    "outrun": "🌅 Outrun",
    "polaroid": "📸 Polaroid",
    "sorbet": "🍧 Sorbet",
    "arcade": "🎮 Arcade",
    "circuit": "⚡ Circuit",
    "drafting-room": "📐 Drafting Room",
    "mainframe": "🖥️ Mainframe",
    "telemetry": "📡 Telemetry",
    "wireframe": "🔲 Wireframe",
    "art-deco": "🏺 Art Deco",
    "atelier": "🖌️ Atelier",
    "basel": "🎭 Basel",
    "cinema": "🎬 Cinema",
    "collage": "🗃️ Collage",
    "coquette": "🎀 Coquette",
    "dark-academia": "📖 Dark Academia",
    "logline": "✍️ Logline",
    "lookbook": "👗 Lookbook",
    "manuscript": "📜 Manuscript",
    "marquee": "🎪 Marquee",
    "oat": "🌾 Oat",
    "one-sheet": "1️⃣ One Sheet",
    "origami": "🦢 Origami",
    "passepartout": "🖼️ Passepartout",
    "scrapbook": "✂️ Scrapbook",
    "y2k": "💿 Y2K",
    "atrium": "🏛️ Atrium",
    "chalkboard": "📋 Chalkboard",
    "expedition": "🧭 Expedition",
    "field-notes": "📔 Field Notes",
    "herbarium": "🌿 Herbarium",
    "level-up": "🎯 Level Up",
    "notebook": "📓 Notebook",
    "observatory": "🔭 Observatory",
    "seminar": "🎓 Seminar",
    "syllabus": "📚 Syllabus",
    "ted-style": "🎤 TED Style",
    "trailhead": "🥾 Trailhead",
    "wildflower": "🌸 Wildflower",
    "broadsheet": "📰 Broadsheet",
    "ledger": "📒 Ledger",
    "letterhead": "🗒️ Letterhead",
    "pitch-book": "📙 Pitch Book",
    "ticker": "📈 Ticker",
    "christmas": "🎄 Christmas",
    "halloween": "🎃 Halloween",
    "quiz-night": "❓ Quiz Night",
    "varsity": "🏆 Varsity",
}

# ── Gemini Model ──────────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-3.5-flash"

"""
SlydAI Bot - AI Slide Generation Engine (Gemini)
"""

import logging
import re
from pathlib import Path
from typing import Optional

import google.generativeai as genai

from config import GEMINI_API_KEY, GEMINI_MODEL, PROMPTS_DIR, MAX_SLIDES

logger = logging.getLogger(__name__)

# ── Gemini Init ───────────────────────────────────────────────────────────────
genai.configure(api_key=GEMINI_API_KEY)


def _load_theme_prompt(theme_id: str) -> str:
    """Read the PROMPT.md for the given theme slug."""
    prompt_path = PROMPTS_DIR / theme_id / "PROMPT.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8").strip()
    return f"Create a presentation in the '{theme_id}' theme."


def _build_system_instruction(theme_id: str) -> str:
    theme_prompt = _load_theme_prompt(theme_id)
    return f"""You are SlydAI — an expert presentation designer, industry analyst, and professional content writer.
Your goal is to create rich, meaningful, in-depth, and well-structured slide decks that strictly adhere to the chosen theme design and the user's topic.

DESIGN THEME RULES (Follow every detail):
{theme_prompt}

LANGUAGE REQUIREMENT:
- Write 100% in the exact language of the user's topic (if Uzbek, write rich and natural Uzbek; if Russian, Russian; if English, English).

CONTENT & DEPTH REQUIREMENTS:
- Do NOT write brief, empty or generic 2-word bullet points.
- Provide deep, meaningful, educational, and high-value points.
- Each bullet point must be informative, containing clear explanations, concrete facts, examples, data points, or strategic insights (15-30 words per point).
- Slide 1: Powerful Main Title and a rich, captivating Subtitle.
- Slide 2: Comprehensive Agenda / Table of Contents outlining the whole presentation journey.
- Middle Slides: Logical breakdown of the topic with structured arguments, analysis, benefits, step-by-step methodologies, and examples.
- Final Slide: Strong Conclusion, Key Takeaways, Actionable Next Steps or Call-to-Action.

OUTPUT FORMAT RULES (Strictly raw text format):
- Return ONLY raw slide data in the exact format below — no markdown code fences, no extra preamble.
- Format for each slide:
=== SLIDE N ===
TITLE: <Specific, punchy, professional title>
SUBTITLE: <Insightful context or subtitle>
CONTENT:
• <In-depth, detailed, meaningful bullet point 1>
• <In-depth, detailed, meaningful bullet point 2>
• <In-depth, detailed, meaningful bullet point 3>
• <In-depth, detailed, meaningful bullet point 4>
SPEAKER_NOTES: <2-3 sentences of deep speaker insight explaining this slide>

(Separate each slide with a blank line)"""


def _build_user_prompt(topic: str, slide_count: int) -> str:
    return (
        f"Generate a comprehensive, high-quality, professional presentation with exactly {slide_count} slides.\n\n"
        f"PRESENTATION TOPIC: {topic}\n\n"
        f"INSTRUCTIONS:\n"
        f"1. Language: Write in the EXACT language of '{topic}'.\n"
        f"2. Detail: Provide rich, substantive, full sentences and meaningful explanations in all bullets.\n"
        f"3. Structure: Slide 1 = Title/Cover, Slide 2 = Agenda, Slides 3 to {slide_count-1} = Deep Topic Exploration, Slide {slide_count} = Summary & Actionable Conclusion."
    )


def _parse_slides(raw: str) -> list[dict]:
    """Parse Gemini output into a list of slide dicts."""
    slides = []
    blocks = re.split(r"===\s*SLIDE\s*\d+\s*===", raw, flags=re.IGNORECASE)

    for i, block in enumerate(blocks):
        block = block.strip()
        if not block:
            continue

        def extract(field: str, text: str) -> str:
            match = re.search(
                rf"^{field}:\s*(.*?)(?=\n[A-Z_]+:|$)",
                text,
                re.IGNORECASE | re.MULTILINE | re.DOTALL,
            )
            return match.group(1).strip() if match else ""

        title = extract("TITLE", block)
        subtitle = extract("SUBTITLE", block)
        content = extract("CONTENT", block)
        notes = extract("SPEAKER_NOTES", block)

        # Clean content bullets
        content_lines = [
            line.strip().lstrip("•-*0123456789.) ").strip()
            for line in content.splitlines()
            if line.strip() and not line.strip().startswith(("SPEAKER", "SUBTITLE", "TITLE"))
        ]

        slides.append({
            "index": i,
            "title": title or f"Slide {i}",
            "subtitle": subtitle,
            "bullets": [b for b in content_lines if len(b) > 2],
            "notes": notes,
        })

    return slides


def _format_slide_text(slide: dict, theme_id: str, total: int) -> str:
    """Format a single slide as pretty Telegram message."""
    idx = slide["index"]
    title = slide["title"]
    subtitle = slide.get("subtitle", "")
    bullets = slide.get("bullets", [])
    notes = slide.get("notes", "")

    lines = [
        f"━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🎞 *Slide {idx} / {total}*",
        f"━━━━━━━━━━━━━━━━━━━━━━━━",
        f"*{_escape_md(title)}*",
    ]

    if subtitle:
        lines.append(f"_{_escape_md(subtitle)}_")

    if bullets:
        lines.append("")
        for b in bullets:
            lines.append(f"• {_escape_md(b)}")

    if notes:
        lines.append("")
        lines.append(f"💬 _{_escape_md(notes)}_")

    return "\n".join(lines)


def _escape_md(text: str) -> str:
    """Escape MarkdownV2 special characters."""
    escape_chars = r"\_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)


async def generate_slides(
    topic: str,
    theme_id: str,
    slide_count: int,
) -> tuple[list[dict], str]:
    """
    Generate slides using Gemini.
    Returns: (slides_list, raw_text)
    """
    if slide_count > MAX_SLIDES:
        slide_count = MAX_SLIDES

    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=_build_system_instruction(theme_id),
        generation_config=genai.GenerationConfig(
            temperature=0.8,
            top_p=0.95,
            max_output_tokens=8192,
        ),
    )

    user_prompt = _build_user_prompt(topic, slide_count)

    logger.info("🤖 Generating %d slides | theme=%s | topic=%s", slide_count, theme_id, topic)

    response = await model.generate_content_async(user_prompt)
    raw = response.text

    slides = _parse_slides(raw)

    if not slides:
        logger.warning("⚠️ Slide parsing failed — returning raw text")
        slides = [{"index": 1, "title": topic, "subtitle": "", "bullets": [raw[:500]], "notes": ""}]

    return slides, raw


def format_all_slides(slides: list[dict], theme_id: str) -> list[str]:
    """Format all slides as Telegram message strings."""
    total = len(slides)
    return [_format_slide_text(s, theme_id, total) for s in slides]


def get_theme_preview_path(theme_id: str, image_index: int = 0) -> Optional[Path]:
    """Return path to preview image for a theme."""
    previews_dir = PROMPTS_DIR / theme_id / "previews"
    if not previews_dir.exists():
        return None
    images = sorted(previews_dir.glob("*.webp"))
    if not images:
        return None
    index = min(image_index, len(images) - 1)
    return images[index]

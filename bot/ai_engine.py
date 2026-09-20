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


def _clean_text(text: str) -> str:
    """Strip HTML tags (e.g. <span>, <div>, CSS styles) and unescape HTML entities."""
    if not text:
        return ""
    # Strip HTML tags
    cleaned = re.sub(r"<[^>]+>", "", text)
    # Replace common HTML entities
    cleaned = cleaned.replace("&amp;", "&").replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'").replace("&nbsp;", " ")
    return cleaned.strip()


def _build_system_instruction(theme_id: str, topic: str = "") -> str:
    theme_prompt = _load_theme_prompt(theme_id)
    return f"""You are SlydAI — a world-class executive presentation designer, senior strategy consultant, and university-level subject matter expert.
Your mission is to generate deeply informative, professional, comprehensive, and intellectually rich presentation slide decks.

CHOSEN DESIGN THEME CONTEXT:
{theme_prompt}

CRITICAL RULES FOR CONTENT DEPTH & QUALITY:
1. LANGUAGE:
   - Output 100% in the EXACT language of the user's topic (e.g. if Uzbek, write in rich, fluent, grammatically flawless Uzbek; if Russian, professional Russian; if English, executive English).

2. DEPTH & SUBSTANCE (VERY IMPORTANT):
   - NEVER generate generic, superficial, short, or hollow bullet points.
   - Every single slide must provide concrete, high-value, educational, or strategic insights.
   - Each bullet point MUST have a bold lead title/concept followed by a detailed, 2-3 sentence factual explanation (30 to 60 words per bullet point) containing specific methodologies, practical examples, metrics, or causal explanations.
   - STRICTLY PROHIBITED: DO NOT output any HTML tags (e.g. NO <span style="...">, NO <div>, NO <font>), and NO CSS styling in the text. Output pure, clean plain text only. Use only markdown **Bold Keyword** for lead keywords.

3. SLIDE DECK ARCHITECTURE:
   - Slide 1 (Cover): TITLE MUST BE STRICTLY AND EXACTLY THE GIVEN USER TOPIC (do not add extra words or change it). SUBTITLE: An insightful, inspiring subtitle explaining the core essence.
   - Slide 2 (Agenda / Reja): A comprehensive, structured breakdown of the presentation's core pillars with descriptive titles.
   - Content Slides (Slides 3 to N-1): Deep dive into fundamental concepts, analytical comparisons, practical implementations, statistics/data points, challenges and strategic solutions.
   - Final Slide (Conclusion / Action Plan): Definitive conclusions, strategic takeaways, and clear 3-step actionable recommendations.

4. EXACT OUTPUT FORMAT (Raw text format only — no markdown backticks ```, no HTML, no preamble):
=== SLIDE 1 ===
TITLE: {topic if topic else "<User Topic>"}
SUBTITLE: <Insightful Subtitle>
CONTENT:
• **<Key Concept 1>:** <In-depth detailed explanation with facts, metrics, and insights (30-60 words)>
• **<Key Concept 2>:** <In-depth detailed explanation with facts, metrics, and insights (30-60 words)>
• **<Key Concept 3>:** <In-depth detailed explanation with facts, metrics, and insights (30-60 words)>
SPEAKER_NOTES: <3-4 sentences of deep presenter commentary explaining the core message of this slide>

=== SLIDE 2 ===
TITLE: <Agenda Title>
SUBTITLE: <Agenda Subtitle>
CONTENT:
• **01. <Pillar 1>:** <Brief summary of what this section covers>
• **02. <Pillar 2>:** <Brief summary of what this section covers>
• **03. <Pillar 3>:** <Brief summary of what this section covers>
• **04. <Pillar 4>:** <Brief summary of what this section covers>
SPEAKER_NOTES: <Presenter overview for the agenda>

(Repeat for all remaining slides up to the requested slide count)"""


def _build_user_prompt(topic: str, slide_count: int) -> str:
    return (
        f"Generate an extensive, highly informative, professional presentation deck with EXACTLY {slide_count} slides.\n\n"
        f"PRESENTATION TOPIC: {topic}\n\n"
        f"REQUIREMENTS:\n"
        f"1. Slide 1 (Cover) TITLE: Must be EXACTLY '{topic}'. Do not alter or add words to the main title.\n"
        f"2. Language: Write 100% in the language of '{topic}'.\n"
        f"3. Content Volume & Richness: Provide deep, analytical, highly informative text in every bullet point. Each bullet must follow the format '• **<Lead Title>:** <Detailed 30-60 words explanation>'.\n"
        f"4. No HTML tags: NEVER include <span style=...>, <div>, or any HTML tags.\n"
        f"5. Exactly {slide_count} slides from Cover (Slide 1) to Strategic Conclusion (Slide {slide_count})."
    )


def _parse_slides(raw: str, topic: str = "") -> list[dict]:
    """Parse Gemini output into a list of slide dicts with structured bullets."""
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

        title = _clean_text(extract("TITLE", block))
        subtitle = _clean_text(extract("SUBTITLE", block))
        content = extract("CONTENT", block)
        notes = _clean_text(extract("SPEAKER_NOTES", block))

        # Ensure Slide 1 title is strictly the user topic if available
        if len(slides) == 0 and topic:
            title = _clean_text(topic)

        # Clean content bullets
        raw_lines = [
            _clean_text(line.strip().lstrip("•-*0123456789.) ").strip())
            for line in content.splitlines()
            if line.strip() and not line.strip().startswith(("SPEAKER", "SUBTITLE", "TITLE"))
        ]

        bullets = []
        structured_bullets = []
        for line in raw_lines:
            if len(line) < 3:
                continue
            bullets.append(line)
            
            # Parse lead (bold header) and body
            # Matches **Lead:** Body or Lead: Body
            m_bold = re.match(r"^\*\*(.*?)\*\*:?\s*(.*)$", line)
            if m_bold:
                lead = _clean_text(m_bold.group(1).strip())
                body = _clean_text(m_bold.group(2).strip())
            else:
                m_colon = re.match(r"^([^:]{3,40}):\s+(.*)$", line)
                if m_colon:
                    lead = _clean_text(m_colon.group(1).strip())
                    body = _clean_text(m_colon.group(2).strip())
                else:
                    lead = ""
                    body = _clean_text(line)

            structured_bullets.append({
                "raw": line,
                "lead": lead,
                "body": body if body else lead,
            })

        slides.append({
            "index": len(slides) + 1,
            "title": title or f"Slide {len(slides) + 1}",
            "subtitle": subtitle,
            "bullets": bullets,
            "structured_bullets": structured_bullets,
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
        system_instruction=_build_system_instruction(theme_id, topic),
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

    slides = _parse_slides(raw, topic)

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

"""
SlydAI Bot - PPTX Slide Deck Generator
Generates native PowerPoint (.pptx) files styled dynamically according to the selected theme palette, fonts, and diverse layouts.
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Optional

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

from config import PROMPTS_DIR

logger = logging.getLogger(__name__)

TEMP_PPTX_DIR = Path(__file__).parent / "temp_pptx"
TEMP_PPTX_DIR.mkdir(parents=True, exist_ok=True)


def parse_theme_specs(theme_id: str) -> dict:
    """Extract palette, fonts, and style details from theme README.md or PROMPT.md."""
    readme_path = PROMPTS_DIR / theme_id / "README.md"
    prompt_path = PROMPTS_DIR / theme_id / "PROMPT.md"
    
    specs = {
        "theme_id": theme_id,
        "bg": "#0B0B16",
        "surface": "#15152A",
        "border": "#2A2A45",
        "primary": "#7C5CFF",
        "heading_color": "#F4F3FF",
        "body_color": "#C3C0DE",
        "muted_color": "#807CA6",
        "heading_font": "Sora",
        "body_font": "Inter",
        "is_dark": True,
        "gradient": "",
    }

    content = ""
    if readme_path.exists():
        content += readme_path.read_text(encoding="utf-8")
    if prompt_path.exists():
        content += "\n" + prompt_path.read_text(encoding="utf-8")

    if not content:
        return specs

    # Mode check
    if re.search(r"Mode:\s*Light", content, re.IGNORECASE) or ("#FFFFFF" in content.upper() and "Background: white" in content):
        specs["is_dark"] = False
        specs["bg"] = "#FFFFFF"
        specs["surface"] = "#F8FAFC"
        specs["border"] = "#E2E8F0"
        specs["heading_color"] = "#0F172A"
        specs["body_color"] = "#334155"
        specs["muted_color"] = "#64748B"

    # Extract Palette table if present
    for role, key in [
        ("Background", "bg"),
        ("Surface / panel", "surface"),
        ("Border", "border"),
        ("Primary accent", "primary"),
        ("Heading text", "heading_color"),
        ("Body text", "body_color"),
        ("Muted text", "muted_color"),
    ]:
        m = re.search(rf"\|\s*{re.escape(role)}\s*\|\s*`?(#[0-9A-Fa-f]{{3,8}})`?\s*\|", content, re.IGNORECASE)
        if m and m.group(1):
            specs[key] = m.group(1).strip()

    # Extract Fonts
    hf_match = re.search(r"-\s*\*\*([^*\n\r]+)\*\*\s*\(heading", content, re.IGNORECASE)
    if hf_match and hf_match.group(1):
        specs["heading_font"] = hf_match.group(1).strip()
    else:
        hf2 = re.search(r"headlines in ['\"]?([A-Za-z\s]+)['\"]?", content, re.IGNORECASE)
        if hf2 and hf2.group(1):
            specs["heading_font"] = hf2.group(1).strip()

    bf_match = re.search(r"-\s*\*\*([^*\n\r]+)\*\*\s*\((?:supporting|body)", content, re.IGNORECASE)
    if bf_match and bf_match.group(1):
        specs["body_font"] = bf_match.group(1).strip()
    else:
        bf2 = re.search(r"body (?:and labels )?in ['\"]?([A-Za-z\s]+)['\"]?", content, re.IGNORECASE)
        if bf2 and bf2.group(1):
            specs["body_font"] = bf2.group(1).strip()

    # Determine gradient accents
    if "aurora" in theme_id:
        specs["gradient"] = "linear-gradient(135deg, #7C5CFF 0%, #36E0D0 50%, #FF7AC6 100%)"
    elif "midnight" in theme_id:
        specs["gradient"] = "linear-gradient(135deg, #2E6BFF 0%, #22D3EE 100%)"
    elif "spark" in theme_id or "holo" in theme_id:
        specs["gradient"] = "linear-gradient(135deg, #FF5E3A 0%, #FF2A6D 50%, #9B51E0 100%)"
    elif specs.get("primary"):
        specs["gradient"] = f"linear-gradient(135deg, {specs['primary']} 0%, {specs['primary']}AA 100%)"

    return specs


def _hex_to_rgb(hex_str: str) -> RGBColor:
    """Convert hex string (e.g. '#0B0B16' or '0B0B16') to RGBColor."""
    hex_clean = hex_str.lstrip("#")
    if len(hex_clean) == 3:
        hex_clean = "".join([c * 2 for c in hex_clean])
    if len(hex_clean) < 6:
        return RGBColor(30, 41, 59)
    try:
        r = int(hex_clean[0:2], 16)
        g = int(hex_clean[2:4], 16)
        b = int(hex_clean[4:6], 16)
        return RGBColor(r, g, b)
    except Exception:
        return RGBColor(30, 41, 59)


def create_presentation_file(slides: list[dict], theme_id: str, topic: str = "") -> Path:
    """Create a fully styled .pptx presentation file based on theme specs with dynamic layouts."""
    theme_specs = parse_theme_specs(theme_id)
    
    prs = Presentation()
    # 16:9 widescreen dimensions (13.333 x 7.5 inches)
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_slide_layout = prs.slide_layouts[6]

    bg_rgb = _hex_to_rgb(theme_specs.get("bg", "#0B0B16"))
    surface_rgb = _hex_to_rgb(theme_specs.get("surface", "#15152A"))
    border_rgb = _hex_to_rgb(theme_specs.get("border", "#2A2A45"))
    primary_rgb = _hex_to_rgb(theme_specs.get("primary", "#7C5CFF"))
    heading_rgb = _hex_to_rgb(theme_specs.get("heading_color", "#F4F3FF"))
    body_rgb = _hex_to_rgb(theme_specs.get("body_color", "#C3C0DE"))
    muted_rgb = _hex_to_rgb(theme_specs.get("muted_color", "#807CA6"))

    heading_font = theme_specs.get("heading_font", "Sora")
    body_font = theme_specs.get("body_font", "Inter")

    total_slides = len(slides)

    for slide_data in slides:
        idx = slide_data.get("index", 1)
        title = slide_data.get("title", f"Slide {idx}")
        subtitle = slide_data.get("subtitle", "")
        bullets = slide_data.get("bullets", [])

        slide = prs.slides.add_slide(blank_slide_layout)

        # 1. Background fill
        bg_shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5)
        )
        bg_shape.fill.solid()
        bg_shape.fill.fore_color.rgb = bg_rgb
        bg_shape.line.fill.background()

        # Accent top bar across all slides for unity
        top_bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.08)
        )
        top_bar.fill.solid()
        top_bar.fill.fore_color.rgb = primary_rgb
        top_bar.line.fill.background()

        # Is Cover Slide (Slide 1)
        if idx == 1:
            # Badge pill
            badge = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE, Inches(4.4), Inches(1.3), Inches(4.533), Inches(0.5)
            )
            badge.fill.solid()
            badge.fill.fore_color.rgb = surface_rgb
            badge.line.color.rgb = border_rgb
            badge.line.width = Pt(1)
            tf_badge = badge.text_frame
            tf_badge.text = f"SLYDAI  •  {theme_id.upper()}"
            p_badge = tf_badge.paragraphs[0]
            p_badge.alignment = PP_ALIGN.CENTER
            p_badge.font.name = body_font
            p_badge.font.size = Pt(12)
            p_badge.font.bold = True
            p_badge.font.color.rgb = primary_rgb

            # Title & Subtitle Card
            main_card = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.2), Inches(2.1), Inches(10.933), Inches(3.8)
            )
            main_card.fill.solid()
            main_card.fill.fore_color.rgb = surface_rgb
            main_card.line.color.rgb = border_rgb
            main_card.line.width = Pt(1)

            tf = main_card.text_frame
            tf.word_wrap = True

            p_title = tf.paragraphs[0]
            p_title.text = title
            p_title.alignment = PP_ALIGN.CENTER
            p_title.font.name = heading_font
            p_title.font.size = Pt(40)
            p_title.font.bold = True
            p_title.font.color.rgb = heading_rgb

            if subtitle:
                p_sub = tf.add_paragraph()
                p_sub.text = subtitle
                p_sub.alignment = PP_ALIGN.CENTER
                p_sub.font.name = body_font
                p_sub.font.size = Pt(18)
                p_sub.font.color.rgb = body_rgb
                p_sub.space_before = Pt(16)

            # Accent line
            line = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.666), Inches(6.2), Inches(2.0), Inches(0.08)
            )
            line.fill.solid()
            line.fill.fore_color.rgb = primary_rgb
            line.line.fill.background()

        # Is Agenda Slide (Slide 2)
        elif idx == 2:
            tag = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.6), Inches(2.6), Inches(0.38)
            )
            tag.fill.solid()
            tag.fill.fore_color.rgb = surface_rgb
            tag.line.color.rgb = border_rgb
            tag.line.width = Pt(1)
            tf_t = tag.text_frame
            tf_t.text = "REJA VA TARKIB"
            p_t = tf_t.paragraphs[0]
            p_t.alignment = PP_ALIGN.CENTER
            p_t.font.name = body_font
            p_t.font.size = Pt(10)
            p_t.font.bold = True
            p_t.font.color.rgb = primary_rgb

            # Title
            tx_title = slide.shapes.add_textbox(Inches(0.8), Inches(1.1), Inches(11.733), Inches(0.8))
            tf = tx_title.text_frame
            tf.word_wrap = True
            p_title = tf.paragraphs[0]
            p_title.text = title
            p_title.font.name = heading_font
            p_title.font.size = Pt(30)
            p_title.font.bold = True
            p_title.font.color.rgb = heading_rgb

            # Agenda list in numbered horizontal cards
            agenda_items = bullets[:5] if bullets else ["Kirish", "Asosiy tahlil", "Imkoniyatlar", "Xulosa"]
            for a_i, a_text in enumerate(agenda_items):
                top_pos = 2.1 + a_i * 0.95
                card = slide.shapes.add_shape(
                    MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(top_pos), Inches(11.733), Inches(0.8)
                )
                card.fill.solid()
                card.fill.fore_color.rgb = surface_rgb
                card.line.color.rgb = border_rgb
                card.line.width = Pt(1)

                card_tf = card.text_frame
                card_tf.word_wrap = True
                card_p = card_tf.paragraphs[0]
                card_p.text = f"0{a_i+1}   |   {a_text}"
                card_p.font.name = body_font
                card_p.font.size = Pt(16)
                card_p.font.bold = True
                card_p.font.color.rgb = body_rgb

        # Is Closing / Summary Slide
        elif idx == total_slides:
            badge = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE, Inches(4.4), Inches(0.8), Inches(4.533), Inches(0.45)
            )
            badge.fill.solid()
            badge.fill.fore_color.rgb = surface_rgb
            badge.line.color.rgb = border_rgb
            badge.line.width = Pt(1)
            tf_b = badge.text_frame
            tf_b.text = "XULOSA & AMALIY TAVSIYALAR"
            p_b = tf_b.paragraphs[0]
            p_b.alignment = PP_ALIGN.CENTER
            p_b.font.name = body_font
            p_b.font.size = Pt(11)
            p_b.font.bold = True
            p_b.font.color.rgb = primary_rgb

            tx_box = slide.shapes.add_textbox(Inches(1.2), Inches(1.4), Inches(10.933), Inches(1.4))
            tf = tx_box.text_frame
            tf.word_wrap = True
            p_title = tf.paragraphs[0]
            p_title.text = title
            p_title.alignment = PP_ALIGN.CENTER
            p_title.font.name = heading_font
            p_title.font.size = Pt(34)
            p_title.font.bold = True
            p_title.font.color.rgb = heading_rgb

            if subtitle:
                p_sub = tf.add_paragraph()
                p_sub.text = subtitle
                p_sub.alignment = PP_ALIGN.CENTER
                p_sub.font.name = body_font
                p_sub.font.size = Pt(16)
                p_sub.font.color.rgb = body_rgb
                p_sub.space_before = Pt(6)

            card_count = min(len(bullets), 3)
            if card_count > 0:
                card_width = (10.933 - (0.35 * (card_count - 1))) / card_count
                for c_i, b_text in enumerate(bullets[:3]):
                    left_pos = 1.2 + c_i * (card_width + 0.35)
                    card = slide.shapes.add_shape(
                        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left_pos), Inches(3.2), Inches(card_width), Inches(3.2)
                    )
                    card.fill.solid()
                    card.fill.fore_color.rgb = surface_rgb
                    card.line.color.rgb = border_rgb
                    card.line.width = Pt(1)

                    card_tf = card.text_frame
                    card_tf.word_wrap = True
                    p_num = card_tf.paragraphs[0]
                    p_num.text = f"Qadam 0{c_i+1}"
                    p_num.font.name = body_font
                    p_num.font.size = Pt(12)
                    p_num.font.bold = True
                    p_num.font.color.rgb = primary_rgb
                    p_num.space_after = Pt(10)

                    card_p = card_tf.add_paragraph()
                    card_p.text = b_text
                    card_p.font.name = body_font
                    card_p.font.size = Pt(14)
                    card_p.font.color.rgb = body_rgb

        # Varied Content Slides
        else:
            # Tag
            tag = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.6), Inches(2.4), Inches(0.38)
            )
            tag.fill.solid()
            tag.fill.fore_color.rgb = surface_rgb
            tag.line.color.rgb = border_rgb
            tag.line.width = Pt(1)
            tf_t = tag.text_frame
            tf_t.text = f"SLAYD {idx:02d} / {total_slides:02d}"
            p_t = tf_t.paragraphs[0]
            p_t.alignment = PP_ALIGN.CENTER
            p_t.font.name = body_font
            p_t.font.size = Pt(10)
            p_t.font.bold = True
            p_t.font.color.rgb = primary_rgb

            # Title & Subtitle
            tx_title = slide.shapes.add_textbox(Inches(0.8), Inches(1.05), Inches(11.733), Inches(1.2))
            tf = tx_title.text_frame
            tf.word_wrap = True
            p_title = tf.paragraphs[0]
            p_title.text = title
            p_title.font.name = heading_font
            p_title.font.size = Pt(28)
            p_title.font.bold = True
            p_title.font.color.rgb = heading_rgb

            if subtitle:
                p_sub = tf.add_paragraph()
                p_sub.text = subtitle
                p_sub.font.name = body_font
                p_sub.font.size = Pt(15)
                p_sub.font.color.rgb = muted_rgb
                p_sub.space_before = Pt(4)

            # Alternate layouts: Even index vs Odd index for visual variety
            if idx % 2 == 0:
                # 2-Column Split Cards
                left_col_bullets = bullets[:2]
                right_col_bullets = bullets[2:4] if len(bullets) > 2 else []

                # Left Box
                col_w = Inches(5.7)
                col_h = Inches(4.3)
                
                card_left = slide.shapes.add_shape(
                    MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(2.35), col_w, col_h
                )
                card_left.fill.solid()
                card_left.fill.fore_color.rgb = surface_rgb
                card_left.line.color.rgb = border_rgb
                card_left.line.width = Pt(1)
                
                tf_l = card_left.text_frame
                tf_l.word_wrap = True
                p_lh = tf_l.paragraphs[0]
                p_lh.text = "Asosiy tushunchalar"
                p_lh.font.name = body_font
                p_lh.font.size = Pt(14)
                p_lh.font.bold = True
                p_lh.font.color.rgb = primary_rgb
                p_lh.space_after = Pt(12)

                for lb in left_col_bullets:
                    p_item = tf_l.add_paragraph()
                    p_item.text = f"• {lb}"
                    p_item.font.name = body_font
                    p_item.font.size = Pt(14)
                    p_item.font.color.rgb = body_rgb
                    p_item.space_after = Pt(10)

                # Right Box
                card_right = slide.shapes.add_shape(
                    MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.833), Inches(2.35), col_w, col_h
                )
                card_right.fill.solid()
                card_right.fill.fore_color.rgb = surface_rgb
                card_right.line.color.rgb = border_rgb
                card_right.line.width = Pt(1)
                
                tf_r = card_right.text_frame
                tf_r.word_wrap = True
                p_rh = tf_r.paragraphs[0]
                p_rh.text = "Amaliy tahlil va ahamiyati"
                p_rh.font.name = body_font
                p_rh.font.size = Pt(14)
                p_rh.font.bold = True
                p_rh.font.color.rgb = primary_rgb
                p_rh.space_after = Pt(12)

                r_items = right_col_bullets if right_col_bullets else left_col_bullets
                for rb in r_items:
                    p_item = tf_r.add_paragraph()
                    p_item.text = f"• {rb}"
                    p_item.font.name = body_font
                    p_item.font.size = Pt(14)
                    p_item.font.color.rgb = body_rgb
                    p_item.space_after = Pt(10)
            else:
                # 3 or 4 Horizontal Row Cards with Accent Icon Box
                b_count = min(len(bullets), 4)
                row_h = 4.2 / max(b_count, 1)
                for b_i, b_text in enumerate(bullets[:4]):
                    top_pos = 2.35 + b_i * row_h
                    card = slide.shapes.add_shape(
                        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(top_pos), Inches(11.733), Inches(row_h - 0.15)
                    )
                    card.fill.solid()
                    card.fill.fore_color.rgb = surface_rgb
                    card.line.color.rgb = border_rgb
                    card.line.width = Pt(1)

                    card_tf = card.text_frame
                    card_tf.word_wrap = True
                    card_p = card_tf.paragraphs[0]
                    card_p.text = f"✦   {b_text}"
                    card_p.font.name = body_font
                    card_p.font.size = Pt(14)
                    card_p.font.color.rgb = body_rgb

        # Slide Footer on all slides
        footer_tx = slide.shapes.add_textbox(Inches(0.8), Inches(6.9), Inches(11.733), Inches(0.4))
        f_tf = footer_tx.text_frame
        f_p = f_tf.paragraphs[0]
        f_p.text = f"SlydAI • {theme_id.upper()}                             {idx} / {total_slides}"
        f_p.font.name = body_font
        f_p.font.size = Pt(10)
        f_p.font.color.rgb = muted_rgb

    # Save presentation file
    safe_topic = "".join([c if c.isalnum() else "_" for c in topic])[:25] or "presentation"
    filename = f"SlydAI_{safe_topic}_{theme_id}.pptx"
    out_path = TEMP_PPTX_DIR / filename
    prs.save(str(out_path))
    return out_path


async def generate_pptx_file(slides: list[dict], theme_id: str, topic: str = "") -> Path:
    """Async wrapper to build PPTX file in executor."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, create_presentation_file, slides, theme_id, topic)

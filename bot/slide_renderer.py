"""
SlydAI Bot - Slide HTML/Image Renderer Engine
Generates styled HTML based on the theme design prompt and converts to high-resolution PNG images.
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Optional
from html2image import Html2Image
from config import PROMPTS_DIR

logger = logging.getLogger(__name__)

TEMP_SLIDES_DIR = Path(__file__).parent / "temp_slides"
TEMP_SLIDES_DIR.mkdir(parents=True, exist_ok=True)

hti = Html2Image(output_path=str(TEMP_SLIDES_DIR), size=(1280, 720))


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


def generate_slide_html(slide: dict, theme_specs: dict, total_slides: int, topic: str = "") -> str:
    """Generate modern, polished 16:9 1280x720 HTML for a single slide."""
    idx = slide["index"]
    title = slide.get("title", f"Slide {idx}")
    subtitle = slide.get("subtitle", "")
    bullets = slide.get("bullets", [])

    bg = theme_specs["bg"]
    surface = theme_specs["surface"]
    border = theme_specs["border"]
    primary = theme_specs["primary"]
    h_color = theme_specs["heading_color"]
    b_color = theme_specs["body_color"]
    m_color = theme_specs["muted_color"]
    h_font = theme_specs["heading_font"].replace(" ", "+")
    b_font = theme_specs["body_font"].replace(" ", "+")
    h_font_name = theme_specs["heading_font"]
    b_font_name = theme_specs["body_font"]
    grad = theme_specs.get("gradient") or primary

    fonts_url = f"https://fonts.googleapis.com/css2?family={h_font}:wght@600;700;800&family={b_font}:wght@400;500;600&display=swap"

    is_cover = (idx == 1)
    is_last = (idx == total_slides)

    glow_orb = ""
    if theme_specs.get("is_dark"):
        glow_orb = f"""
        <div style="position:absolute; width:550px; height:550px; border-radius:50%; background:{primary}; filter:blur(150px); opacity:0.18; top:-120px; right:-120px; pointer-events:none;"></div>
        <div style="position:absolute; width:450px; height:450px; border-radius:50%; background:{primary}; filter:blur(140px); opacity:0.12; bottom:-120px; left:-60px; pointer-events:none;"></div>
        """

    content_html = ""

    if is_cover:
        content_html = f"""
        <div style="flex:1; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; padding:40px 70px; z-index:2;">
            <div style="display:inline-block; padding:8px 22px; border-radius:30px; background:{surface}; border:1px solid {border}; color:{primary}; font-size:14px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; margin-bottom:28px;">
                SLYDAI PRESENTATION
            </div>
            <h1 style="font-family:'{h_font_name}', sans-serif; font-size:52px; font-weight:800; line-height:1.2; color:{h_color}; margin:0 0 20px 0; max-width:1000px;">
                {title}
            </h1>
            {f'<p style="font-size:22px; color:{b_color}; line-height:1.5; margin:0 0 32px 0; max-width:850px;">{subtitle}</p>' if subtitle else ''}
            <div style="width:90px; height:5px; background:{grad}; border-radius:3px; margin-top:8px;"></div>
        </div>
        """
    elif is_last:
        cards_last = ""
        for b in bullets[:3]:
            cards_last += f"""
                <div style="flex:1; background:{surface}; border:1px solid {border}; border-radius:14px; padding:22px; text-align:left;">
                    <div style="width:10px; height:10px; border-radius:50%; background:{primary}; margin-bottom:12px;"></div>
                    <p style="margin:0; font-size:16px; color:{b_color}; line-height:1.5; font-weight:500;">{b}</p>
                </div>
            """
        content_html = f"""
        <div style="flex:1; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; padding:40px 70px; z-index:2;">
            <div style="display:inline-block; padding:8px 22px; border-radius:30px; background:{surface}; border:1px solid {border}; color:{primary}; font-size:14px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; margin-bottom:24px;">
                XULOSA & KEYINGI QADAMLAR
            </div>
            <h1 style="font-family:'{h_font_name}', sans-serif; font-size:48px; font-weight:800; line-height:1.2; color:{h_color}; margin:0 0 20px 0; max-width:950px;">
                {title}
            </h1>
            {f'<p style="font-size:20px; color:{b_color}; line-height:1.5; margin:0 0 25px 0; max-width:800px;">{subtitle}</p>' if subtitle else ''}
            <div style="display:flex; gap:20px; margin-top:20px; width:100%; max-width:850px;">
                {cards_last}
            </div>
        </div>
        """
    else:
        if len(bullets) <= 2:
            cards_html = ""
            for b in bullets:
                cards_html += f"""
                <div style="background:{surface}; border:1px solid {border}; border-radius:16px; padding:26px 30px; margin-bottom:16px; display:flex; align-items:flex-start; gap:16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
                    <div style="min-width:28px; height:28px; border-radius:8px; background:{primary}22; border:1px solid {primary}55; display:flex; align-items:center; justify-content:center; color:{primary}; font-weight:bold; font-size:14px; margin-top:2px;">✦</div>
                    <div style="font-size:19px; color:{b_color}; line-height:1.6; font-weight:500;">{b}</div>
                </div>
                """
        else:
            cards_html = "<div style='display:grid; grid-template-columns:1fr 1fr; gap:18px;'>"
            for b in bullets[:4]:
                cards_html += f"""
                <div style="background:{surface}; border:1px solid {border}; border-radius:14px; padding:22px 24px; display:flex; align-items:flex-start; gap:14px; box-shadow: 0 4px 15px rgba(0,0,0,0.06);">
                    <div style="min-width:24px; height:24px; border-radius:6px; background:{primary}25; border:1px solid {primary}60; display:flex; align-items:center; justify-content:center; color:{primary}; font-weight:bold; font-size:12px; margin-top:2px;">✦</div>
                    <div style="font-size:17px; color:{b_color}; line-height:1.5; font-weight:500;">{b}</div>
                </div>
                """
            cards_html += "</div>"

        content_html = f"""
        <div style="flex:1; display:flex; flex-direction:column; padding:50px 70px 30px 70px; z-index:2;">
            <div style="margin-bottom:28px;">
                <div style="display:inline-block; padding:5px 14px; border-radius:20px; background:{surface}; border:1px solid {border}; color:{primary}; font-size:12px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; margin-bottom:12px;">
                    SLIDE {idx:02d} / {total_slides:02d}
                </div>
                <h2 style="font-family:'{h_font_name}', sans-serif; font-size:36px; font-weight:700; line-height:1.25; color:{h_color}; margin:0 0 8px 0;">
                    {title}
                </h2>
                {f'<p style="font-size:18px; color:{m_color}; margin:0; font-weight:500;">{subtitle}</p>' if subtitle else ''}
            </div>

            <div style="flex:1; display:flex; flex-direction:column; justify-content:center;">
                {cards_html}
            </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <link href="{fonts_url}" rel="stylesheet">
    <style>
        * {{
            box-sizing: border-box;
            -webkit-font-smoothing: antialiased;
        }}
        body {{
            margin: 0;
            padding: 0;
            width: 1280px;
            height: 720px;
            background-color: {bg};
            font-family: '{b_font_name}', sans-serif;
            overflow: hidden;
            display: flex;
            position: relative;
        }}
    </style>
</head>
<body>
    {glow_orb}
    <div style="width:100%; height:100%; display:flex; flex-direction:column; justify-content:space-between; position:relative; z-index:2;">
        {content_html}
        
        <div style="padding:15px 70px 25px 70px; display:flex; justify-content:space-between; align-items:center; border-top:1px solid {border}50; margin:0 30px;">
            <div style="font-size:12px; color:{m_color}; font-weight:600; letter-spacing:1px; text-transform:uppercase;">
                SlydAI • {theme_specs.get('theme_id', '').upper()}
            </div>
            <div style="font-size:12px; color:{m_color}; font-weight:600;">
                {idx} / {total_slides}
            </div>
        </div>
    </div>
</body>
</html>"""
    return html


async def render_slide_image(slide: dict, theme_id: str, total_slides: int, topic: str = "") -> Optional[Path]:
    """Render a single slide to PNG image file in background thread."""
    theme_specs = parse_theme_specs(theme_id)
    html_content = generate_slide_html(slide, theme_specs, total_slides, topic)
    
    idx = slide["index"]
    file_name = f"slide_{theme_id}_{idx}_{abs(hash(topic)) % 10000}.png"
    out_path = TEMP_SLIDES_DIR / file_name

    def _sync_render():
        try:
            hti.screenshot(html_str=html_content, save_as=file_name)
            return out_path if out_path.exists() else None
        except Exception as e:
            logger.error("Screenshot render failed for slide %d: %s", idx, e)
            return None

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sync_render)

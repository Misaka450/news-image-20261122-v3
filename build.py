#!/usr/bin/env python3
"""
The World in One Day — Sunday 22 November 2026
Broadsheet card-grid renderer strictly implementing /root/makefun/ni/v3/SPEC.md.
Pure Python + Pillow (no external images, no generative models).
Canvas: 4000x4000 (all logical 1000x1000 SPEC px dimensions scaled x4).
"""

from __future__ import annotations

import hashlib
import math
import os
from collections import Counter
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Scale & Canvas Constants (SPEC 1000x1000 logical -> 4000x4000 physical)
# ---------------------------------------------------------------------------
SCALE = 4
LOGICAL_W = 1000
LOGICAL_H = 1000
CANVAS_W = LOGICAL_W * SCALE  # 4000
CANVAS_H = LOGICAL_H * SCALE  # 4000
MAX_PNG_BYTES = 8 * 1024 * 1024  # 8 MB cap per SPEC

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_MAIN = os.path.join(SCRIPT_DIR, "entry.png")
OUT_PREVIEW = os.path.join(SCRIPT_DIR, "preview-300.png")

# ---------------------------------------------------------------------------
# Fonts (TeX Gyre Termes editorial serif + TeX Gyre Heros crisp sans)
# ---------------------------------------------------------------------------
FONT_SERIF_BOLD = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyretermes-bold.otf"
FONT_SERIF_REG = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyretermes-regular.otf"
FONT_SERIF_ITAL = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyretermes-italic.otf"
FONT_SERIF_BI = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyretermes-bolditalic.otf"
FONT_SANS_BOLD = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheros-bold.otf"
FONT_SANS_REG = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheros-regular.otf"
FONT_SANS_ITAL = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheros-italic.otf"
FONT_SANS_CN_BOLD = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheroscn-bold.otf"
FONT_SANS_CN_REG = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheroscn-regular.otf"

_FONT_CACHE: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}


def load_font(path: str, size_px: int) -> ImageFont.FreeTypeFont:
    key = (path, int(size_px))
    f = _FONT_CACHE.get(key)
    if f is None:
        f = ImageFont.truetype(path, int(size_px))
        _FONT_CACHE[key] = f
    return f


def sx(val: float) -> int:
    """Scale logical SPEC px to physical 4000x4000 px."""
    return int(round(val * SCALE))


# ---------------------------------------------------------------------------
# Editorial Palette
# ---------------------------------------------------------------------------
BG_PAPER = (246, 242, 233)
CARD_BG = (255, 254, 250)
CARD_BORDER = (205, 197, 183)
CARD_SHADOW = (224, 217, 203)
ILLUS_BG = (244, 239, 229)
SCORE_BG = (237, 231, 218)
DARK_BAR = (21, 23, 28)
INK_BLACK = (20, 20, 20)
INK_DARK = (38, 40, 46)
INK_MUTED = (95, 99, 108)
RULE_LIGHT = (204, 196, 182)
RULE_DARK = (24, 24, 24)
CRIMSON = (182, 30, 36)
WHITE = (255, 255, 255)
OCEAN_BG = (222, 234, 240)
OCEAN_GRID = (196, 213, 223)

# 7 Regions in SPEC order (深蓝/砖红/墨绿/紫/橙/青/灰)
REGION_ORDER = [
    "EUROPE",
    "MID EAST",
    "ASIA-PAC",
    "AMERICAS",
    "AFRICA",
    "CLIMATE",
    "AT SEA",
]

REGION_COLORS: Dict[str, Tuple[int, int, int]] = {
    "EUROPE": (29, 66, 115),      # 深蓝
    "MID EAST": (168, 42, 42),    # 砖红
    "ASIA-PAC": (29, 102, 68),    # 墨绿
    "AMERICAS": (106, 53, 124),   # 紫
    "AFRICA": (196, 90, 22),      # 橙
    "CLIMATE": (17, 115, 118),    # 青
    "AT SEA": (73, 84, 98),       # 灰
}

STATUS_COLORS: Dict[str, Tuple[int, int, int]] = {
    "CONFIRMED": (29, 107, 62),   # Green
    "REPORTED": (184, 107, 0),    # Amber
    "CLAIM": (182, 30, 36),       # Red
}


def tint(rgb: Tuple[int, int, int], factor: float = 0.65) -> Tuple[int, int, int]:
    """Blend rgb toward warm white by factor (0=original, 1=white)."""
    return (
        int(round(rgb[0] + (250 - rgb[0]) * factor)),
        int(round(rgb[1] + (248 - rgb[1]) * factor)),
        int(round(rgb[2] + (243 - rgb[2]) * factor)),
    )


# ---------------------------------------------------------------------------
# Strict SPEC Content Data (20 Stories + Scoreboard)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Story:
    num: int
    region: str
    title: str
    source: str
    status: str
    topic_or_city: str
    lede: str = ""
    lon: float = 0.0
    lat: float = 0.0


SCOREBOARD_ITEMS: List[Tuple[str, str]] = [
    ("74,742", "GAZA DEAD"),
    ("03:00", "COP31 DEADLINE"),
    ("148", "DRONES OVER UKRAINE"),
    ("41", "VIETNAM FLOOD DEAD"),
    ("450bn", "EU LOAN TO KYIV"),
    ("17", "PAKISTAN CREW RECOVERED"),
]

STORIES: List[Story] = [
    # 12 Numbered Cards (#1–#12)
    Story(
        1, "CLIMATE", "COP31 ends without a deal", "Reuters, BBC, Guardian", "CONFIRMED",
        "CLIMATE SUMMIT",
        "Negotiations collapse past the 03:00 deadline as delegates deadlock on phase-out language.",
    ),
    Story(
        2, "MID EAST", "Iran claims strikes on two US bases", "Fars, Dawn", "CLAIM",
        "REGIONAL CONFLICT",
        "Iranian media claims Patriot radar struck in Bahrain; Washington has not confirmed damage.",
    ),
    Story(
        3, "AT SEA", "Russian frigate Merkury ablaze in Benghazi", "AP, Al Jazeera, Reuters", "CONFIRMED",
        "MARITIME",
        "Fire engulfs the naval corvette docked in eastern Libya, sending dense smoke over the port.",
    ),
    Story(
        4, "AT SEA", "Maltese tanker hit by suicide drone boat", "Reuters", "CONFIRMED",
        "SHIPPING",
        "Explosive uncrewed surface vessel strikes merchant tanker transiting key sea lane.",
    ),
    Story(
        5, "EUROPE", "Russian drones hit Dymer flats, 2 dead", "Kyiv Independent", "REPORTED",
        "UKRAINE WAR",
        "Overnight wave of 148 drones targets 19 Ukrainian sites, shattering residential apartments.",
    ),
    Story(
        6, "EUROPE", "Emergency blackouts across five regions", "DTEK, Ukrenergo", "CONFIRMED",
        "ENERGY GRID",
        "Grid operators impose emergency outages across five oblasts after substation strikes.",
    ),
    Story(
        7, "MID EAST", "Two VLCCs crippled by mines in Hormuz", "Iran military", "CLAIM",
        "STRAIT SECURITY",
        "Military statement alleges mine detonations disabled two supertankers in the narrow strait.",
    ),
    Story(
        8, "MID EAST", "Gaza death toll rises to 74,742", "Gaza health ministry", "CONFIRMED",
        "HUMANITARIAN",
        "Updated daily ministry bulletin incorporates newly verified fatalities across the strip.",
    ),
    Story(
        9, "AFRICA", "Drones hit Khartoum homes and UN site, 4 dead", "WarStrikes", "REPORTED",
        "SUDAN WAR",
        "Aerial strikes damage housing blocks and a United Nations facility in the Sudanese capital.",
    ),
    Story(
        10, "AFRICA", "UN: drones cause nearly 3/4 of Sudan war deaths", "Reuters", "CONFIRMED",
        "UN REPORT",
        "UN monitors report unmanned aerial attacks now account for almost three-quarters of deaths.",
    ),
    Story(
        11, "ASIA-PAC", "Vietnam floods kill at least 41", "multiple", "CONFIRMED",
        "WEATHER",
        "Relentless monsoon rains submerge central provinces, severing roads and displacing thousands.",
    ),
    Story(
        12, "ASIA-PAC", "Bangladesh quake kills 6, felt in Kolkata", "multiple", "CONFIRMED",
        "SEISMIC",
        "Shallow tremor rattles Dhaka and eastern India, cracking structures and triggering evacuations.",
    ),
    # 8 Map + Numbered Dispatch List Items (#13–#20)
    Story(
        13, "EUROPE", "Fico refuses EU's €450bn loan to Ukraine", "Reuters", "CONFIRMED",
        "BRATISLAVA", lon=17.1, lat=48.1,
    ),
    Story(
        14, "EUROPE", "Commission proposes €450bn loan for Kyiv", "Reuters", "CONFIRMED",
        "BRUSSELS", lon=4.4, lat=50.8,
    ),
    Story(
        15, "AMERICAS", "US pushes for Russia-Ukraine peace by early Jan 2027", "FT", "REPORTED",
        "WASHINGTON", lon=-77.0, lat=38.9,
    ),
    Story(
        16, "EUROPE", "French Senate passes police shooting law", "Reuters", "CONFIRMED",
        "PARIS", lon=2.3, lat=48.9,
    ),
    Story(
        17, "AMERICAS", "Mexico captures FBI ten most wanted fugitive", "Reuters", "CONFIRMED",
        "MEXICO CITY", lon=-99.1, lat=19.4,
    ),
    Story(
        18, "ASIA-PAC", "Hong Kong election turnout hits record", "China Daily", "CONFIRMED",
        "HONG KONG", lon=114.2, lat=22.3,
    ),
    Story(
        19, "ASIA-PAC", "Pakistan's first astronaut departs for Beijing", "APP", "CONFIRMED",
        "ISLAMABAD", lon=73.0, lat=33.7,
    ),
    Story(
        20, "MID EAST", "Missile hits Lahj health centre, about 10 dead", "Soth24", "CLAIM",
        "LAHJ", lon=44.9, lat=13.1,
    ),
]


# ---------------------------------------------------------------------------
# Strict Fit & Collision Detection Engine (SPEC Mandatory Constraints)
# ---------------------------------------------------------------------------
_MEASURE_IMG = Image.new("RGB", (16, 16))
_MEASURE_DRAW = ImageDraw.Draw(_MEASURE_IMG)


def _text_width(text: str, font: ImageFont.FreeTypeFont) -> int:
    if not text:
        return 0
    bb = _MEASURE_DRAW.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]


def _wrap_words(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> List[str]:
    words = text.split()
    if not words:
        return [""]
    lines: List[str] = []
    cur = words[0]
    for w in words[1:]:
        cand = cur + " " + w
        if _text_width(cand, font) <= max_w:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def fit(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_w: int,
    max_lines: int,
    max_h: Optional[int] = None,
    line_spacing: float = 1.12,
    min_logical_px: int = 8,
) -> Tuple[ImageFont.FreeTypeFont, List[str], int, int]:
    """
    SPEC-enforced fit(text, font, max_w, max_lines):
    Measures bounding box; if overflowing max_w / max_lines / max_h, shrinks
    font size step by step (-1px per step, floor 8px logical = 8*SCALE physical).
    Raises ValueError if still overflowing at floor.
    Returns (fitted_font, lines, line_step_px, total_ink_h).
    """
    font_path = getattr(font, "path", None)
    if not font_path:
        raise ValueError("fit() requires a TrueType/OpenType FreeTypeFont")
    start_size = int(round(font.size))
    min_size = min_logical_px * SCALE

    for size in range(start_size, min_size - 1, -1):
        cand_font = load_font(font_path, size)
        if max_lines == 1:
            lines = [text]
        else:
            lines = _wrap_words(text, cand_font, max_w)
        if len(lines) > max_lines:
            continue
        widths = [_text_width(ln, cand_font) for ln in lines]
        if any(w > max_w for w in widths):
            continue
        ascent, descent = cand_font.getmetrics()
        line_h = ascent + descent
        step = max(1, int(round(size * line_spacing)))
        if len(lines) == 1:
            bb = _MEASURE_DRAW.textbbox((0, 0), lines[0], font=cand_font)
            total_h = bb[3] - bb[1]
        else:
            last_bb = _MEASURE_DRAW.textbbox((0, 0), lines[-1], font=cand_font)
            first_bb = _MEASURE_DRAW.textbbox((0, 0), lines[0], font=cand_font)
            total_h = (len(lines) - 1) * step + (last_bb[3] - first_bb[1])
            total_h = max(total_h, (len(lines) - 1) * step + int(line_h * 0.85))
        if max_h is not None and total_h > max_h:
            continue
        return cand_font, lines, step, total_h

    raise ValueError(
        f"fit() failed: text={text!r} cannot fit in max_w={max_w}, "
        f"max_lines={max_lines}, max_h={max_h} even at min size {min_size}px"
    )


BoxRecord = Tuple[str, Tuple[int, int, int, int]]


def no_overlap(boxes: Sequence[BoxRecord]) -> int:
    """
    SPEC-enforced pairwise AABB collision check across ALL text, illustration,
    badge, and map pin blocks. Raises RuntimeError immediately on any overlap.
    Returns total pairs checked.
    """
    n = len(boxes)
    collisions: List[str] = []
    for i in range(n):
        name_a, (ax0, ay0, ax1, ay1) = boxes[i]
        if ax1 <= ax0 or ay1 <= ay0:
            raise RuntimeError(f"Degenerate box {name_a}: {(ax0, ay0, ax1, ay1)}")
        for j in range(i + 1, n):
            name_b, (bx0, by0, bx1, by1) = boxes[j]
            if ax0 < bx1 and ax1 > bx0 and ay0 < by1 and ay1 > by0:
                ix0, iy0 = max(ax0, bx0), max(ay0, by0)
                ix1, iy1 = min(ax1, bx1), min(ay1, by1)
                collisions.append(
                    f"{name_a} {(ax0, ay0, ax1, ay1)} <-> {name_b} {(bx0, by0, bx1, by1)} "
                    f"(overlap {(ix1 - ix0)}x{(iy1 - iy0)}px)"
                )
    if collisions:
        sample = "\n  ".join(collisions[:10])
        raise RuntimeError(f"Collision detected ({len(collisions)} pairs):\n  {sample}")
    return n * (n - 1) // 2


def draw_fitted_text(
    draw: ImageDraw.ImageDraw,
    boxes: List[BoxRecord],
    label: str,
    text: str,
    font: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    max_w: int,
    max_lines: int,
    fill: Tuple[int, int, int],
    align: str = "left",
    valign: str = "top",
    box_h: Optional[int] = None,
    line_spacing: float = 1.12,
    register: bool = True,
) -> Tuple[int, int, int, int]:
    """Fit text via fit(), render crisp lines, and register exact rendered bbox."""
    fitted_font, lines, step, _ = fit(
        text, font, max_w=max_w, max_lines=max_lines, max_h=box_h, line_spacing=line_spacing
    )

    # Measure combined ink bbox relative to y=0 for accurate vertical alignment
    rel_bboxes = [draw.textbbox((0, i * step), ln, font=fitted_font) for i, ln in enumerate(lines)]
    min_top = min(bb[1] for bb in rel_bboxes)
    max_bot = max(bb[3] for bb in rel_bboxes)
    ink_h = max_bot - min_top

    if valign == "middle" and box_h is not None:
        y_base = y + (box_h - ink_h) // 2 - min_top
    elif valign == "bottom" and box_h is not None:
        y_base = y + box_h - ink_h - min_top
    else:
        y_base = y - min_top

    x0_all, y0_all, x1_all, y1_all = 10**9, 10**9, -10**9, -10**9
    for i, ln in enumerate(lines):
        bb0 = draw.textbbox((0, 0), ln, font=fitted_font)
        lw = bb0[2] - bb0[0]
        if align == "center":
            lx = x + (max_w - lw) // 2 - bb0[0]
        elif align == "right":
            lx = x + max_w - lw - bb0[0]
        else:
            lx = x - bb0[0]
        ly = y_base + i * step
        draw.text((lx, ly), ln, font=fitted_font, fill=fill)
        actual_bb = draw.textbbox((lx, ly), ln, font=fitted_font)
        x0_all = min(x0_all, actual_bb[0])
        y0_all = min(y0_all, actual_bb[1])
        x1_all = max(x1_all, actual_bb[2])
        y1_all = max(y1_all, actual_bb[3])

    final_bb = (int(x0_all), int(y0_all), int(x1_all), int(y1_all))
    if register:
        boxes.append((label, final_bb))
    return final_bb


# ---------------------------------------------------------------------------
# Bespoke Card Line-Art Illustrations (2px logical = 8px line, NO faces)
# ---------------------------------------------------------------------------
def _draw_wave(
    draw: ImageDraw.ImageDraw,
    x0: int,
    x1: int,
    y: int,
    amp: int,
    cycles: float,
    color: Tuple[int, int, int],
    width: int,
) -> None:
    pts = []
    steps = 48
    for i in range(steps + 1):
        t = i / steps
        px = x0 + (x1 - x0) * t
        py = y + math.sin(t * cycles * 2 * math.pi) * amp
        pts.append((px, py))
    draw.line(pts, fill=color, width=width, joint="curve")


def draw_card_illustration(
    draw: ImageDraw.ImageDraw,
    story_num: int,
    rect: Tuple[int, int, int, int],
    accent: Tuple[int, int, int],
) -> None:
    """
    Draw a clean editorial line-art vignette (2px logical = 8px stroke, zero faces)
    tailored to each of stories 1..12 inside rect=(x0, y0, x1, y1).
    """
    x0, y0, x1, y1 = rect
    w = x1 - x0
    h = y1 - y0
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    lw = sx(2)          # 2px logical -> 8px physical
    lw_thin = sx(1.25)  # 5px secondary detail
    soft_accent = tint(accent, 0.72)
    mid_accent = tint(accent, 0.42)
    ink = INK_BLACK

    # Panel background + hairline frame
    draw.rectangle(rect, fill=ILLUS_BG, outline=CARD_BORDER, width=sx(1))
    # Subtle geometric wash band in accent tint
    draw.rectangle((x0 + sx(2), y0 + sx(2), x1 - sx(2), y0 + int(h * 0.34)), fill=soft_accent)

    if story_num == 1:
        # COP31: Wireframe globe + gavel + fractured agreement sheet
        r = int(w * 0.33)
        gy = y0 + int(h * 0.34)
        draw.ellipse((cx - r, gy - r, cx + r, gy + r), fill=WHITE, outline=ink, width=lw)
        draw.ellipse((cx - r // 2, gy - r, cx + r // 2, gy + r), outline=accent, width=lw_thin)
        draw.line((cx, gy - r, cx, gy + r), fill=accent, width=lw_thin)
        draw.line((cx - r, gy, cx + r, gy), fill=accent, width=lw_thin)
        draw.arc((cx - r, gy - r // 2, cx + r, gy + r // 2), 180, 360, fill=ink, width=lw_thin)
        # Cracked treaty page below
        px0, py0, px1, py1 = cx - int(w * 0.30), y0 + int(h * 0.62), cx + int(w * 0.30), y1 - sx(8)
        draw.rectangle((px0, py0, px1, py1), fill=WHITE, outline=ink, width=lw)
        for frac in (0.28, 0.48, 0.68):
            ly = py0 + int((py1 - py0) * frac)
            draw.line((px0 + sx(5), ly, px1 - sx(5), ly), fill=INK_MUTED, width=lw_thin)
        # Jagged crack / X across treaty
        draw.line(
            [(px0 + sx(6), py0 + sx(4)), (cx, (py0 + py1) // 2), (px1 - sx(6), py1 - sx(4))],
            fill=CRIMSON, width=lw,
        )
        draw.line(
            [(px1 - sx(6), py0 + sx(4)), (cx, (py0 + py1) // 2), (px0 + sx(6), py1 - sx(4))],
            fill=CRIMSON, width=lw,
        )

    elif story_num == 2:
        # Iran claims strikes on US bases: Radar dish + signal arcs + trajectory
        # Trajectory arc from top-right to radar
        draw.arc((x0 + sx(6), y0 + sx(10), x1 + sx(18), y0 + int(h * 0.65)), 180, 275, fill=CRIMSON, width=lw)
        # Impact starburst at top-left
        bx, by = x0 + int(w * 0.30), y0 + int(h * 0.30)
        for ang in range(0, 360, 45):
            rad = math.radians(ang)
            r1, r2 = sx(4), sx(11)
            draw.line(
                (bx + math.cos(rad) * r1, by + math.sin(rad) * r1,
                 bx + math.cos(rad) * r2, by + math.sin(rad) * r2),
                fill=CRIMSON, width=lw_thin,
            )
        # Radar dish at bottom
        rx, ry = cx + sx(4), y0 + int(h * 0.68)
        draw.pieslice((rx - sx(20), ry - sx(20), rx + sx(20), ry + sx(20)), 145, 325, fill=WHITE, outline=ink, width=lw)
        draw.line((rx, ry, rx - sx(10), ry - sx(14)), fill=ink, width=lw)
        draw.ellipse((rx - sx(13), ry - sx(17), rx - sx(7), ry - sx(11)), fill=accent, outline=ink, width=lw_thin)
        # Tripod base
        draw.line((rx, ry + sx(6), rx - sx(14), y1 - sx(8)), fill=ink, width=lw)
        draw.line((rx, ry + sx(6), rx + sx(14), y1 - sx(8)), fill=ink, width=lw)
        draw.line((x0 + sx(8), y1 - sx(8), x1 - sx(8), y1 - sx(8)), fill=ink, width=lw)

    elif story_num == 3:
        # Frigate Merkury ablaze: Naval ship silhouette + smoke plumes + waves
        wy = y0 + int(h * 0.72)
        # Smoke plumes rising
        for sx_off, sy_off, rad in [(-8, 0.22, 13), (4, 0.32, 15), (-4, 0.44, 11)]:
            draw.ellipse(
                (cx + sx(sx_off) - sx(rad), y0 + int(h * sy_off) - sx(rad),
                 cx + sx(sx_off) + sx(rad), y0 + int(h * sy_off) + sx(rad)),
                fill=mid_accent, outline=ink, width=lw_thin,
            )
        # Flame peaks on deck
        draw.polygon(
            [(cx - sx(10), wy - sx(12)), (cx - sx(3), wy - sx(28)), (cx + sx(2), wy - sx(16)),
             (cx + sx(8), wy - sx(26)), (cx + sx(13), wy - sx(12))],
            fill=CRIMSON, outline=ink, width=lw_thin,
        )
        # Naval hull + superstructure
        draw.polygon(
            [(x0 + sx(7), wy - sx(9)), (x1 - sx(7), wy - sx(9)),
             (x1 - sx(13), wy + sx(4)), (x0 + sx(11), wy + sx(4))],
            fill=WHITE, outline=ink, width=lw,
        )
        draw.rectangle((cx - sx(13), wy - sx(19), cx + sx(8), wy - sx(9)), fill=WHITE, outline=ink, width=lw)
        draw.line((cx - sx(4), wy - sx(19), cx - sx(4), wy - sx(31)), fill=ink, width=lw)
        _draw_wave(draw, x0 + sx(6), x1 - sx(6), wy + sx(8), sx(3), 2.5, accent, lw)
        _draw_wave(draw, x0 + sx(8), x1 - sx(8), wy + sx(16), sx(2.5), 2.0, ink, lw_thin)

    elif story_num == 4:
        # Maltese tanker hit by suicide drone boat
        ty = y0 + int(h * 0.56)
        # Tanker hull
        draw.polygon(
            [(x0 + sx(6), ty - sx(6)), (x1 - sx(6), ty - sx(6)),
             (x1 - sx(10), ty + sx(7)), (x0 + sx(10), ty + sx(7))],
            fill=WHITE, outline=ink, width=lw,
        )
        # Aft bridge & funnel
        draw.rectangle((x1 - sx(20), ty - sx(20), x1 - sx(9), ty - sx(6)), fill=WHITE, outline=ink, width=lw)
        draw.rectangle((x0 + sx(14), ty - sx(11), x1 - sx(24), ty - sx(6)), fill=mid_accent, outline=ink, width=lw_thin)
        # Small USV drone boat below approaching impact point
        ux, uy = x0 + sx(20), ty + sx(22)
        draw.polygon([(ux - sx(10), uy), (ux + sx(10), uy - sx(4)), (ux + sx(4), uy + sx(4))], fill=accent, outline=ink, width=lw)
        # Dashed attack vector + impact flash
        draw.line((ux + sx(8), uy - sx(5), cx - sx(2), ty + sx(6)), fill=CRIMSON, width=lw)
        for dx, dy in [(-10, -16), (0, -22), (10, -16), (-14, -6), (14, -6)]:
            draw.line((cx - sx(2), ty - sx(6), cx - sx(2) + sx(dx), ty - sx(6) + sx(dy)), fill=CRIMSON, width=lw_thin)
        _draw_wave(draw, x0 + sx(6), x1 - sx(6), ty + sx(12), sx(2.5), 2.5, accent, lw)
        _draw_wave(draw, x0 + sx(6), x1 - sx(6), y1 - sx(9), sx(2.5), 2.0, ink, lw_thin)

    elif story_num == 5:
        # Dymer flats hit by Russian drones: apartment block + delta-wing drone
        # Delta-wing drone top
        dy = y0 + int(h * 0.22)
        draw.polygon(
            [(cx, dy - sx(11)), (cx + sx(18), dy + sx(6)), (cx, dy + sx(2)), (cx - sx(18), dy + sx(6))],
            fill=accent, outline=ink, width=lw,
        )
        # Apartment facade below
        bx0, by0, bx1, by1 = x0 + sx(10), y0 + int(h * 0.40), x1 - sx(10), y1 - sx(7)
        draw.rectangle((bx0, by0, bx1, by1), fill=WHITE, outline=ink, width=lw)
        # Grid of windows
        cols, rows = 3, 4
        ww, wh = sx(8), sx(7)
        for r_i in range(rows):
            for c_i in range(cols):
                wx = bx0 + sx(5) + c_i * sx(13)
                wy_i = by0 + sx(5) + r_i * sx(11)
                fill_w = DARK_BAR if (r_i == 0 and c_i == 1) else soft_accent
                draw.rectangle((wx, wy_i, wx + ww, wy_i + wh), fill=fill_w, outline=ink, width=lw_thin)
        # Impact crack lines at top-center of building
        ix, iy = cx, by0 + sx(7)
        for dx, dy2 in [(-12, -8), (12, -8), (-10, 10), (11, 8)]:
            draw.line((ix, iy, ix + sx(dx), iy + sx(dy2)), fill=CRIMSON, width=lw_thin)

    elif story_num == 6:
        # Emergency blackouts: High-voltage transmission pylon + crossed bolt
        top_y = y0 + sx(12)
        bot_y = y1 - sx(8)
        # Pylon A-frame
        draw.line((cx, top_y, cx - sx(16), bot_y), fill=ink, width=lw)
        draw.line((cx, top_y, cx + sx(16), bot_y), fill=ink, width=lw)
        # Cross arms
        for frac, span in [(0.25, 20), (0.48, 23)]:
            ay = top_y + int((bot_y - top_y) * frac)
            draw.line((cx - sx(span), ay, cx + sx(span), ay), fill=ink, width=lw)
            # Insulator drops
            draw.line((cx - sx(span), ay, cx - sx(span), ay + sx(6)), fill=accent, width=lw_thin)
            draw.line((cx + sx(span), ay, cx + sx(span), ay + sx(6)), fill=accent, width=lw_thin)
        # Internal truss X
        mid1 = top_y + int((bot_y - top_y) * 0.48)
        mid2 = top_y + int((bot_y - top_y) * 0.78)
        draw.line((cx - sx(8), mid1, cx + sx(12), mid2), fill=ink, width=lw_thin)
        draw.line((cx + sx(8), mid1, cx - sx(12), mid2), fill=ink, width=lw_thin)
        # Lightning bolt badge (amber/crimson)
        bolt = [
            (cx + sx(4), cy - sx(4)), (cx - sx(6), cy + sx(10)),
            (cx + sx(1), cy + sx(10)), (cx - sx(4), cy + sx(24)),
            (cx + sx(10), cy + sx(7)), (cx + sx(2), cy + sx(7)),
        ]
        draw.polygon(bolt, fill=CRIMSON, outline=ink, width=lw_thin)

    elif story_num == 7:
        # Mines in Hormuz: Horned sea mine + two tanker outlines
        # Distant tanker hulls at top
        for ty_f in (0.18, 0.30):
            ty = y0 + int(h * ty_f)
            draw.polygon(
                [(x0 + sx(10), ty), (x1 - sx(10), ty), (x1 - sx(14), ty + sx(5)), (x0 + sx(14), ty + sx(5))],
                fill=WHITE, outline=ink, width=lw_thin,
            )
        # Sea mine sphere in center-bottom
        my = y0 + int(h * 0.64)
        mr = sx(15)
        for ang in range(0, 360, 45):
            rad = math.radians(ang)
            draw.line(
                (cx + math.cos(rad) * (mr - sx(2)), my + math.sin(rad) * (mr - sx(2)),
                 cx + math.cos(rad) * (mr + sx(8)), my + math.sin(rad) * (mr + sx(8))),
                fill=ink, width=lw,
            )
        draw.ellipse((cx - mr, my - mr, cx + mr, my + mr), fill=mid_accent, outline=ink, width=lw)
        draw.ellipse((cx - sx(5), my - sx(5), cx + sx(5), my + sx(5)), fill=WHITE, outline=ink, width=lw_thin)
        _draw_wave(draw, x0 + sx(6), x1 - sx(6), y0 + int(h * 0.42), sx(2.5), 2.5, accent, lw)

    elif story_num == 8:
        # Gaza toll 74,742: Editorial escalating bar chart + humanitarian medical cross
        # Medical cross in top circle
        cr = sx(12)
        my = y0 + int(h * 0.24)
        draw.ellipse((cx - cr, my - cr, cx + cr, my + cr), fill=WHITE, outline=ink, width=lw)
        draw.rectangle((cx - sx(3), my - sx(8), cx + sx(3), my + sx(8)), fill=CRIMSON)
        draw.rectangle((cx - sx(8), my - sx(3), cx + sx(8), my + sx(3)), fill=CRIMSON)
        # Rising bar chart below
        base_y = y1 - sx(10)
        draw.line((x0 + sx(8), base_y, x1 - sx(8), base_y), fill=ink, width=lw)
        heights = [12, 18, 25, 33, 42]
        bw = sx(7)
        start_x = x0 + sx(10)
        for idx, bh in enumerate(heights):
            bx = start_x + idx * sx(9)
            fill_b = CRIMSON if idx == len(heights) - 1 else mid_accent
            draw.rectangle((bx, base_y - sx(bh), bx + bw, base_y), fill=fill_b, outline=ink, width=lw_thin)

    elif story_num == 9:
        # Khartoum homes + UN site + drone
        # Quad drone hovering top
        dy = y0 + int(h * 0.20)
        draw.line((cx - sx(16), dy, cx + sx(16), dy), fill=ink, width=lw)
        draw.ellipse((cx - sx(6), dy - sx(4), cx + sx(6), dy + sx(4)), fill=accent, outline=ink, width=lw_thin)
        for rx in (cx - sx(16), cx + sx(16)):
            draw.line((rx - sx(5), dy - sx(4), rx + sx(5), dy - sx(4)), fill=ink, width=lw_thin)
        # Arched Khartoum structures + UN flag compound
        base_y = y1 - sx(9)
        draw.rectangle((x0 + sx(8), base_y - sx(26), cx + sx(2), base_y), fill=WHITE, outline=ink, width=lw)
        draw.chord((x0 + sx(13), base_y - sx(16), x0 + sx(25), base_y + sx(8)), 180, 360, fill=soft_accent, outline=ink, width=lw_thin)
        draw.rectangle((cx + sx(2), base_y - sx(36), x1 - sx(8), base_y), fill=WHITE, outline=ink, width=lw)
        # UN flag pole & globe banner
        fx, fy = cx + sx(13), base_y - sx(36)
        draw.line((fx, fy, fx, fy - sx(16)), fill=ink, width=lw_thin)
        draw.rectangle((fx, fy - sx(16), fx + sx(12), fy - sx(8)), fill=(29, 98, 168), outline=ink, width=lw_thin)

    elif story_num == 10:
        # UN: drones cause nearly 3/4 of Sudan war deaths -> 270 deg donut chart + drone
        r = sx(20)
        py = y0 + int(h * 0.42)
        # Full circle base (1/4 remaining)
        draw.ellipse((cx - r, py - r, cx + r, py + r), fill=WHITE, outline=ink, width=lw)
        # 3/4 filled wedge (270 degrees)
        draw.pieslice((cx - r, py - r, cx + r, py + r), 270, 180, fill=accent, outline=ink, width=lw)
        # Inner cutout for donut clarity
        ir = sx(9)
        draw.ellipse((cx - ir, py - ir, cx + ir, py + ir), fill=ILLUS_BG, outline=ink, width=lw_thin)
        # Small drone silhouette below
        dy = y1 - sx(16)
        draw.polygon(
            [(cx, dy - sx(7)), (cx + sx(15), dy + sx(5)), (cx, dy + sx(1)), (cx - sx(15), dy + sx(5))],
            fill=ink, outline=ink, width=lw_thin,
        )

    elif story_num == 11:
        # Vietnam floods: diagonal rain + submerged roof peak + waves
        # Diagonal rain streaks at top
        for rx_off in range(-18, 22, 9):
            draw.line(
                (cx + sx(rx_off) + sx(4), y0 + sx(10), cx + sx(rx_off) - sx(3), y0 + sx(26)),
                fill=accent, width=lw_thin,
            )
        # Pitched roof emerging from floodwater
        ry = y0 + int(h * 0.56)
        draw.polygon([(cx - sx(20), ry), (cx, ry - sx(17)), (cx + sx(20), ry)], fill=WHITE, outline=ink, width=lw)
        draw.rectangle((cx - sx(13), ry, cx + sx(13), ry + sx(12)), fill=soft_accent, outline=ink, width=lw)
        # Floodwater wave bands below
        for wy_off, col in [(6, accent), (15, ink), (24, accent)]:
            _draw_wave(draw, x0 + sx(6), x1 - sx(6), ry + sx(wy_off), sx(3), 2.5, col, lw)

    elif story_num == 12:
        # Bangladesh quake: concentric epicenter rings + jagged seismograph waveform
        ey = y0 + int(h * 0.34)
        for rr in (sx(20), sx(13), sx(6)):
            draw.ellipse((cx - rr, ey - rr, cx + rr, ey + rr), outline=accent if rr != sx(6) else CRIMSON, width=lw_thin)
        draw.ellipse((cx - sx(3), ey - sx(3), cx + sx(3), ey + sx(3)), fill=CRIMSON)
        # Seismograph waveform across bottom half
        sy = y0 + int(h * 0.74)
        draw.line((x0 + sx(6), sy, x1 - sx(6), sy), fill=CARD_BORDER, width=lw_thin)
        wave_pts = [
            (x0 + sx(6), sy), (x0 + sx(14), sy), (x0 + sx(18), sy - sx(6)),
            (x0 + sx(22), sy + sx(9)), (x0 + sx(27), sy - sx(18)),
            (x0 + sx(32), sy + sx(20)), (x0 + sx(37), sy - sx(14)),
            (x0 + sx(42), sy + sx(8)), (x0 + sx(47), sy - sx(4)),
            (x0 + sx(52), sy), (x1 - sx(6), sy),
        ]
        draw.line(wave_pts, fill=ink, width=lw, joint="curve")


# ---------------------------------------------------------------------------
# Vector World Map (7-Region Colored + Pins 13–20, Pure Pillow Polygons)
# ---------------------------------------------------------------------------
# Stylized clean equirectangular lon/lat polygons for all 7 regions
MAP_POLYGONS: List[Tuple[str, List[Tuple[float, float]]]] = [
    # AMERICAS (Purple tint)
    ("AMERICAS", [
        (-168, 66), (-142, 70), (-118, 69), (-95, 68), (-82, 62), (-65, 60),
        (-54, 48), (-67, 44), (-76, 35), (-81, 25), (-88, 21), (-84, 10),
        (-78, 8), (-84, 14), (-96, 16), (-106, 20), (-114, 31), (-124, 40),
        (-130, 54), (-150, 60), (-165, 58),
    ]),
    ("AMERICAS", [(-55, 60), (-42, 60), (-22, 72), (-25, 81), (-58, 78), (-64, 68)]),  # Greenland
    ("AMERICAS", [
        (-78, 9), (-62, 10), (-50, 1), (-35, -6), (-39, -18), (-48, -28),
        (-58, -38), (-67, -54), (-74, -52), (-73, -36), (-71, -18), (-81, -4), (-79, 4),
    ]),
    # EUROPE (Navy tint)
    ("EUROPE", [
        (-9, 37), (-9, 43), (-2, 44), (-4, 48), (2, 51), (8, 54), (11, 58),
        (5, 61), (14, 68), (28, 71), (42, 67), (52, 60), (46, 48), (38, 45),
        (30, 46), (28, 41), (22, 37), (16, 40), (13, 45), (8, 44), (3, 42), (-5, 36),
    ]),
    ("EUROPE", [(-10, 51), (-5, 51), (1, 51), (1, 54), (-3, 58), (-7, 57), (-9, 54)]),  # UK/Ireland
    # AFRICA (Orange tint)
    ("AFRICA", [
        (-17, 15), (-13, 28), (-6, 36), (10, 37), (25, 32), (33, 31), (43, 12),
        (51, 11), (41, -2), (40, -15), (33, -26), (20, -35), (14, -22), (12, -6),
        (9, 4), (-7, 5), (-16, 11),
    ]),
    ("AFRICA", [(44, -25), (47, -25), (50, -13), (47, -13)]),  # Madagascar
    # MID EAST (Brick Red tint)
    ("MID EAST", [
        (26, 40), (36, 42), (45, 40), (54, 37), (61, 35), (61, 25), (56, 26),
        (59, 22), (52, 16), (43, 13), (39, 21), (35, 29), (36, 36), (27, 37),
    ]),
    # ASIA-PAC (Forest Green tint)
    ("ASIA-PAC", [
        (52, 60), (65, 70), (105, 74), (145, 71), (174, 65), (162, 56),
        (142, 53), (135, 43), (128, 35), (122, 39), (121, 31), (118, 24),
        (109, 20), (109, 12), (103, 2), (99, 14), (91, 22), (80, 15),
        (77, 8), (68, 23), (62, 25), (61, 36), (54, 41), (48, 48),
    ]),
    ("ASIA-PAC", [(130, 31), (136, 34), (142, 41), (145, 44), (140, 42), (132, 35)]),  # Japan
    ("ASIA-PAC", [(96, 5), (105, -6), (116, -8), (118, -3), (106, -1)]),               # Indonesia W
    ("ASIA-PAC", [(114, -22), (124, -14), (136, -12), (143, -11), (153, -27),
                  (150, -37), (138, -35), (122, -34), (114, -34)]),                    # Australia
    ("ASIA-PAC", [(167, -46), (173, -41), (178, -37), (174, -35), (169, -43)]),        # New Zealand
    # CLIMATE (Teal polar band — Antarctica)
    ("CLIMATE", [
        (-175, -64), (-120, -67), (-60, -63), (0, -66), (65, -65), (135, -66),
        (175, -65), (175, -78), (-175, -78),
    ]),
]

# Maritime corridors for AT SEA region (Med, Red Sea, Hormuz, Black Sea)
AT_SEA_LANES: List[List[Tuple[float, float]]] = [
    [(-5, 36), (6, 38), (16, 35), (26, 34), (32, 31)],          # Mediterranean (Benghazi)
    [(33, 29), (38, 21), (43, 13), (52, 13), (58, 22), (56, 26)],  # Red Sea -> Hormuz
    [(29, 42), (35, 43), (40, 44)],                              # Black Sea
]

# Custom label offsets (dx_logical, dy_logical) for pins 13–20 so zero pins collide
PIN_OFFSETS: Dict[int, Tuple[int, int]] = {
    13: (20, -14),   # Bratislava -> NE into Eastern Europe (clear of Mid East)
    14: (4, -24),    # Brussels -> N
    15: (10, -16),   # Washington -> NE
    16: (-28, -2),   # Paris -> W
    17: (-24, 16),   # Mexico City -> SW
    18: (18, 16),    # Hong Kong -> SE
    19: (-8, -22),   # Islamabad -> N
    20: (-10, 22),   # Lahj -> S
}


def draw_world_map(
    draw: ImageDraw.ImageDraw,
    boxes: List[BoxRecord],
    map_rect: Tuple[int, int, int, int],
    list_stories: Sequence[Story],
) -> None:
    x0, y0, x1, y1 = map_rect
    # Outer map card
    draw.rectangle(map_rect, fill=CARD_BG, outline=CARD_BORDER, width=sx(1))

    # Map header bar (18px logical = 72px)
    hdr_h = sx(18)
    draw.rectangle((x0, y0, x1, y0 + hdr_h), fill=DARK_BAR)
    draw_fitted_text(
        draw, boxes, "map_header",
        "WORLD DISPATCH MAP · 7 REGIONS · PINS 13–20",
        load_font(FONT_SANS_BOLD, sx(9)),
        x0 + sx(8), y0, (x1 - x0) - sx(16), 1, WHITE,
        align="left", valign="middle", box_h=hdr_h,
    )

    # Inner map projection rectangle
    pad = sx(4)
    mx0, my0 = x0 + pad, y0 + hdr_h + pad
    mx1, my1 = x1 - pad, y1 - sx(20)  # leave bottom strip for 7-region map key
    mw = mx1 - mx0
    mh = my1 - my0

    draw.rectangle((mx0, my0, mx1, my1), fill=OCEAN_BG, outline=CARD_BORDER, width=sx(1))

    def proj(lon: float, lat: float) -> Tuple[int, int]:
        # Lon -180..180, Lat -78..82
        px = mx0 + int(round((lon + 180.0) / 360.0 * mw))
        py = my0 + int(round((82.0 - lat) / 160.0 * mh))
        return (px, py)

    # Graticule lines every 30 deg
    for lon in range(-150, 180, 30):
        p1, p2 = proj(lon, 82), proj(lon, -78)
        draw.line((p1, p2), fill=OCEAN_GRID, width=sx(0.5))
    for lat in range(-60, 90, 30):
        p1, p2 = proj(-180, lat), proj(180, lat)
        w_line = sx(0.75) if lat == 0 else sx(0.5)
        draw.line((p1, p2), fill=OCEAN_GRID, width=w_line)

    # Draw AT SEA maritime lanes first
    sea_col = REGION_COLORS["AT SEA"]
    for lane in AT_SEA_LANES:
        pts = [proj(lo, la) for lo, la in lane]
        draw.line(pts, fill=tint(sea_col, 0.35), width=sx(3), joint="curve")
        draw.line(pts, fill=sea_col, width=sx(1), joint="curve")

    # Draw 7-region colored continents
    for region, poly in MAP_POLYGONS:
        pts = [proj(lo, la) for lo, la in poly]
        base = REGION_COLORS[region]
        draw.polygon(pts, fill=tint(base, 0.45), outline=tint(base, 0.08))
        # Crisp coastline stroke
        draw.line(pts + [pts[0]], fill=tint(base, 0.12), width=sx(0.75))

    # Draw numbered event pins 13–20 with crisp leader lines
    pin_sz = sx(17)  # 17x17 logical = 68x68 physical
    pin_font = load_font(FONT_SANS_BOLD, sx(10))
    for st in list_stories:
        gx, gy = proj(st.lon, st.lat)
        ox_l, oy_l = PIN_OFFSETS[st.num]
        px = max(mx0 + sx(2), min(mx1 - pin_sz - sx(2), gx + sx(ox_l) - pin_sz // 2))
        py = max(my0 + sx(2), min(my1 - pin_sz - sx(2), gy + sx(oy_l) - pin_sz // 2))
        pcx, pcy = px + pin_sz // 2, py + pin_sz // 2
        col = REGION_COLORS[st.region]

        # Leader line + anchor dot at true coordinates
        draw.line((gx, gy, pcx, pcy), fill=INK_BLACK, width=sx(1))
        r_dot = sx(2.0)
        draw.ellipse((gx - r_dot, gy - r_dot, gx + r_dot, gy + r_dot), fill=col, outline=WHITE, width=sx(0.75))

        # Solid numbered badge pin
        pin_box = (px, py, px + pin_sz, py + pin_sz)
        draw.rectangle(pin_box, fill=col, outline=WHITE, width=sx(1))
        draw_fitted_text(
            draw, boxes, f"map_pin_txt_{st.num}",
            str(st.num), pin_font,
            px, py, pin_sz, 1, WHITE,
            align="center", valign="middle", box_h=pin_sz,
            register=False,
        )
        # Register outer pin badge in global collision list
        boxes.append((f"map_pin_{st.num}", pin_box))

    # Bottom 7-region compact key strip inside map frame
    key_y0 = my1 + sx(3)
    key_h = (y1 - sx(3)) - key_y0
    key_w = (x1 - x0) - sx(8)
    slot_w = key_w // len(REGION_ORDER)
    key_font = load_font(FONT_SANS_CN_BOLD, sx(8))
    for idx, reg in enumerate(REGION_ORDER):
        kx = x0 + sx(4) + idx * slot_w
        sw_sz = sx(7)
        sy = key_y0 + (key_h - sw_sz) // 2
        draw.rectangle((kx, sy, kx + sw_sz, sy + sw_sz), fill=REGION_COLORS[reg], outline=INK_DARK, width=sx(0.5))
        draw_fitted_text(
            draw, boxes, f"map_key_{reg}",
            reg, key_font,
            kx + sw_sz + sx(2.5), key_y0, slot_w - sw_sz - sx(4), 1, INK_DARK,
            align="left", valign="middle", box_h=key_h,
        )


# ---------------------------------------------------------------------------
# Main Render Pipeline
# ---------------------------------------------------------------------------
def build_poster() -> Tuple[Image.Image, Dict[str, int], int]:
    # Strict verification of data integrity
    if len(STORIES) != 20:
        raise RuntimeError(f"Expected 20 stories, got {len(STORIES)}")
    cards = STORIES[:12]
    dispatches = STORIES[12:]
    if len(cards) != 12 or len(dispatches) != 8:
        raise RuntimeError("Must have 12 cards + 8 dispatch list items")

    # Dynamically compute 7-region counts from STORIES (NO hardcoding!)
    region_counts: Dict[str, int] = dict(Counter(s.region for s in STORIES))
    for reg in REGION_ORDER:
        region_counts.setdefault(reg, 0)
    if sum(region_counts.values()) != len(STORIES):
        raise RuntimeError("Region count mismatch against total stories")

    img = Image.new("RGB", (CANVAS_W, CANVAS_H), BG_PAPER)
    draw = ImageDraw.Draw(img)
    boxes: List[BoxRecord] = []

    # Content horizontal bounds (aligns 3x316 + 2x8 = 964 logical px -> 18..982)
    MX = 18
    X0 = sx(MX)
    X1 = sx(LOGICAL_W - MX)
    CW = X1 - X0  # 3856 px

    # =========================================================================
    # 1. TOP BAR (y = 0..26, height 26px, 11px uppercase)
    # =========================================================================
    top_h = sx(26)
    draw.rectangle((0, 0, CANVAS_W, top_h), fill=DARK_BAR)
    top_font = load_font(FONT_SANS_BOLD, sx(11))
    draw_fitted_text(
        draw, boxes, "top_left",
        "THE WORLD IN ONE DAY",
        top_font, X0, 0, sx(280), 1, WHITE,
        align="left", valign="middle", box_h=top_h,
    )
    right_banner = (
        f"{len(STORIES)} STORIES · {len(REGION_ORDER)} REGIONS · "
        "EVERY ONE DATED SUNDAY 22 NOVEMBER 2026"
    )
    draw_fitted_text(
        draw, boxes, "top_right",
        right_banner,
        top_font, X0 + sx(290), 0, CW - sx(290), 1, (232, 227, 216),
        align="right", valign="middle", box_h=top_h,
    )

    # =========================================================================
    # 2. GIANT DATE BANNER (86px bold serif, centered, y = 30..136)
    #    + Double-color decorative rule (3px black + 1px red)
    # =========================================================================
    date_y0 = sx(32)
    date_h = sx(102)
    # Allow wide span (984 logical px) so 86px bold serif stays unshrunk at 344px
    draw_fitted_text(
        draw, boxes, "giant_date",
        "Sunday 22 November 2026",
        load_font(FONT_SERIF_BOLD, sx(86)),
        sx(8), date_y0, sx(984), 1, INK_BLACK,
        align="center", valign="middle", box_h=date_h,
    )
    # Double-color decorative rule: 3px black + 2px gap + 1px red
    rule_y = sx(139)
    draw.rectangle((X0, rule_y, X1, rule_y + sx(3)), fill=RULE_DARK)
    draw.rectangle((X0, rule_y + sx(5), X1, rule_y + sx(6)), fill=CRIMSON)

    # =========================================================================
    # 3. SINGLE-LINE SUMMARY (Red italic 15px, y = 148..176)
    # =========================================================================
    sum_text = (
        "COP31 puts its final deal to the vote · "
        "Iran claims Patriot radar hit in Bahrain · "
        "Russia's overnight drones hit 19 sites in Ukraine"
    )
    draw_fitted_text(
        draw, boxes, "summary_line",
        sum_text,
        load_font(FONT_SERIF_ITAL, sx(15)),
        X0, sx(149), CW, 1, CRIMSON,
        align="center", valign="middle", box_h=sx(26),
    )

    # =========================================================================
    # 4. SCOREBOARD STRIP (6 cells, y = 180..242: 30px bold + 9px uppercase)
    # =========================================================================
    sc_y0, sc_y1 = sx(180), sx(242)
    draw.rectangle((X0, sc_y0, X1, sc_y1), fill=SCORE_BG, outline=CARD_BORDER, width=sx(1))
    draw.rectangle((X0, sc_y0, X1, sc_y0 + sx(1.5)), fill=RULE_DARK)
    n_sc = len(SCOREBOARD_ITEMS)
    cell_w = CW / n_sc
    num_font = load_font(FONT_SERIF_BOLD, sx(30))
    lbl_font = load_font(FONT_SANS_CN_BOLD, sx(9))
    for i, (val, lbl) in enumerate(SCOREBOARD_ITEMS):
        cx0 = X0 + int(round(i * cell_w))
        cx1 = X0 + int(round((i + 1) * cell_w))
        cw_i = cx1 - cx0
        if i > 0:
            draw.line((cx0, sc_y0 + sx(6), cx0, sc_y1 - sx(6)), fill=CARD_BORDER, width=sx(1))
        val_color = CRIMSON if i in (0, 2) else INK_BLACK
        draw_fitted_text(
            draw, boxes, f"score_num_{i}",
            val, num_font,
            cx0 + sx(4), sc_y0 + sx(6), cw_i - sx(8), 1, val_color,
            align="center", valign="middle", box_h=sx(36),
        )
        draw_fitted_text(
            draw, boxes, f"score_lbl_{i}",
            lbl, lbl_font,
            cx0 + sx(4), sc_y0 + sx(44), cw_i - sx(8), 1, INK_DARK,
            align="center", valign="middle", box_h=sx(14),
        )

    # =========================================================================
    # 5. 7-COLOR REGION BAR (y = 248..272, height 22px, dynamic counts, 10px bold)
    # =========================================================================
    rb_y0 = sx(249)
    rb_h = sx(22)
    rb_y1 = rb_y0 + rb_h
    total_stories = sum(region_counts[r] for r in REGION_ORDER)
    # Minimum base width + proportional count share (100% driven by counted stories)
    min_seg_l = 96.0
    extra_pool_l = (LOGICAL_W - 2 * MX) - min_seg_l * len(REGION_ORDER)
    seg_widths_l = [
        min_seg_l + extra_pool_l * (region_counts[r] / total_stories) for r in REGION_ORDER
    ]
    cur_x = X0
    rb_font = load_font(FONT_SANS_BOLD, sx(10))
    for idx, reg in enumerate(REGION_ORDER):
        seg_w = int(round(seg_widths_l[idx] * SCALE)) if idx < len(REGION_ORDER) - 1 else (X1 - cur_x)
        seg_box = (cur_x, rb_y0, cur_x + seg_w, rb_y1)
        draw.rectangle(seg_box, fill=REGION_COLORS[reg])
        if idx > 0:
            draw.line((cur_x, rb_y0, cur_x, rb_y1), fill=BG_PAPER, width=sx(1.5))
        draw_fitted_text(
            draw, boxes, f"region_bar_{reg}",
            f"{reg} {region_counts[reg]}",
            rb_font,
            cur_x + sx(3), rb_y0, seg_w - sx(6), 1, WHITE,
            align="center", valign="middle", box_h=rb_h,
        )
        cur_x += seg_w

    # =========================================================================
    # 6. NUMBERED CARD GRID (12 cards: 3 cols x 4 rows, 316x100, gap 8px)
    #    y = 279..703 (4*100 + 3*8 = 424 logical px)
    # =========================================================================
    grid_y0 = sx(279)
    card_w = sx(316)
    card_h = sx(100)
    card_gap = sx(8)

    badge_font = load_font(FONT_SANS_BOLD, sx(17))
    meta_font = load_font(FONT_SANS_CN_BOLD, sx(8))
    status_font = load_font(FONT_SANS_BOLD, sx(8))
    title_font = load_font(FONT_SERIF_BOLD, sx(17))
    lede_font = load_font(FONT_SANS_REG, sx(11))
    src_font = load_font(FONT_SERIF_ITAL, sx(9))

    for idx, st in enumerate(cards):
        col = idx % 3
        row = idx // 3
        cx0 = X0 + col * (card_w + card_gap)
        cy0 = grid_y0 + row * (card_h + card_gap)
        cx1 = cx0 + card_w
        cy1 = cy0 + card_h
        reg_col = REGION_COLORS[st.region]

        # Subtle bottom shadow + crisp card body + top region stripe
        draw.rectangle((cx0 + sx(1), cy0 + sx(2), cx1 + sx(1), cy1 + sx(2)), fill=CARD_SHADOW)
        draw.rectangle((cx0, cy0, cx1, cy1), fill=CARD_BG, outline=CARD_BORDER, width=sx(1))
        draw.rectangle((cx0, cy0, cx1, cy0 + sx(2.5)), fill=reg_col)

        # Left Number Badge: 32x32 logical (128x128 px), solid region color, white 17px bold
        b_sz = sx(32)
        bx0, by0 = cx0 + sx(5), cy0 + sx(5)
        badge_rect = (bx0, by0, bx0 + b_sz, by0 + b_sz)
        draw.rectangle(badge_rect, fill=reg_col)
        draw_fitted_text(
            draw, boxes, f"card_{st.num}_badge_txt",
            str(st.num), badge_font,
            bx0, by0, b_sz, 1, WHITE,
            align="center", valign="middle", box_h=b_sz,
            register=False,
        )
        boxes.append((f"card_{st.num}_badge", badge_rect))

        # Right Illustration Strip: 64x93 logical (256x372 px), 2px line art, NO faces
        il_w = sx(64)
        il_x0 = cx1 - sx(3) - il_w
        il_rect = (il_x0, cy0 + sx(4), cx1 - sx(3), cy1 - sx(3))
        draw_card_illustration(draw, st.num, il_rect, reg_col)
        boxes.append((f"card_{st.num}_illus", il_rect))

        # Text column right of badge & left of illustration
        tx0 = bx0 + b_sz + sx(5)
        tx1 = il_x0 - sx(4)
        tw = tx1 - tx0  # ~203 logical px (812 px)

        # Meta Row (y+4.5..y+15): Region + Topic small tag (8px) on left + Status Pill (8px) on right
        st_col = STATUS_COLORS[st.status]
        st_tw = _text_width(st.status, status_font)
        pill_w = st_tw + sx(8)
        pill_h = sx(10.5)
        pill_x0 = tx1 - pill_w
        pill_y0 = cy0 + sx(4.5)
        pill_rect = (pill_x0, pill_y0, tx1, pill_y0 + pill_h)
        draw.rectangle(pill_rect, fill=st_col)
        draw_fitted_text(
            draw, boxes, f"card_{st.num}_status_txt",
            st.status, status_font,
            pill_x0, pill_y0, pill_w, 1, WHITE,
            align="center", valign="middle", box_h=pill_h,
            register=False,
        )
        boxes.append((f"card_{st.num}_status", pill_rect))

        meta_w = (pill_x0 - sx(4)) - tx0
        draw_fitted_text(
            draw, boxes, f"card_{st.num}_meta",
            f"{st.region} · {st.topic_or_city}",
            meta_font,
            tx0, pill_y0, meta_w, 1, INK_MUTED,
            align="left", valign="middle", box_h=pill_h,
        )

        # Bold Serif Headline (17px, max 2 lines) beside badge
        hl_y0 = cy0 + sx(18)
        hl_h = sx(39)
        draw_fitted_text(
            draw, boxes, f"card_{st.num}_title",
            st.title, title_font,
            tx0, hl_y0, tw, 2, INK_BLACK,
            align="left", valign="top", box_h=hl_h, line_spacing=1.06,
        )

        # Lede (11px, max 2 lines) spanning full left-to-illus width below badge+headline
        lede_x0 = cx0 + sx(5)
        lede_w = tx1 - lede_x0  # ~240 logical px (960 px)
        lede_y0 = cy0 + sx(59.5)
        lede_h = sx(26)
        draw_fitted_text(
            draw, boxes, f"card_{st.num}_lede",
            st.lede, lede_font,
            lede_x0, lede_y0, lede_w, 2, INK_DARK,
            align="left", valign="top", box_h=lede_h, line_spacing=1.08,
        )

        # Source (9px italic, 1 line) at card foot
        src_y0 = cy0 + sx(87)
        src_h = sx(10)
        draw_fitted_text(
            draw, boxes, f"card_{st.num}_source",
            f"Source: {st.source}", src_font,
            lede_x0, src_y0, lede_w, 1, INK_MUTED,
            align="left", valign="middle", box_h=src_h,
        )

    # =========================================================================
    # 7. BOTTOM HALF (y = 711..967, height 256px): Left Map + Right List 13–20
    # =========================================================================
    bot_y0 = sx(711)
    bot_y1 = sx(967)
    map_w = sx(458)
    mid_gap = sx(10)
    map_rect = (X0, bot_y0, X0 + map_w, bot_y1)
    list_x0 = X0 + map_w + mid_gap
    list_rect = (list_x0, bot_y0, X1, bot_y1)

    # Left: World Map (7 regions colored + pins 13–20)
    draw_world_map(draw, boxes, map_rect, dispatches)

    # Right: Numbered Dispatch List (Items 13–20)
    draw.rectangle(list_rect, fill=CARD_BG, outline=CARD_BORDER, width=sx(1))
    lhdr_h = sx(18)
    draw.rectangle((list_x0, bot_y0, X1, bot_y0 + lhdr_h), fill=DARK_BAR)
    draw_fitted_text(
        draw, boxes, "list_header",
        "NUMBERED DISPATCHES · ITEMS 13–20 · DATELINE, SOURCE & STATUS",
        load_font(FONT_SANS_BOLD, sx(9)),
        list_x0 + sx(8), bot_y0, (X1 - list_x0) - sx(16), 1, WHITE,
        align="left", valign="middle", box_h=lhdr_h,
    )

    body_y0 = bot_y0 + lhdr_h + sx(2)
    body_h = (bot_y1 - sx(2)) - body_y0
    row_h = body_h / len(dispatches)  # ~29.25 logical px per item

    lnum_font = load_font(FONT_SANS_BOLD, sx(11))
    ltitle_font = load_font(FONT_SERIF_BOLD, sx(12))
    lsrc_font = load_font(FONT_SERIF_ITAL, sx(9))
    lreg_font = load_font(FONT_SANS_CN_BOLD, sx(8))

    for i, st in enumerate(dispatches):
        ry0 = body_y0 + int(round(i * row_h))
        ry1 = body_y0 + int(round((i + 1) * row_h))
        rh = ry1 - ry0
        reg_col = REGION_COLORS[st.region]

        if i % 2 == 1:
            draw.rectangle((list_x0 + sx(1), ry0, X1 - sx(1), ry1), fill=(249, 246, 240))
        if i > 0:
            draw.line((list_x0 + sx(6), ry0, X1 - sx(6), ry0), fill=RULE_LIGHT, width=sx(0.75))

        # Number square
        nsz = sx(21)
        nx0 = list_x0 + sx(6)
        ny0 = ry0 + (rh - nsz) // 2
        nbox = (nx0, ny0, nx0 + nsz, ny0 + nsz)
        draw.rectangle(nbox, fill=reg_col)
        draw_fitted_text(
            draw, boxes, f"list_{st.num}_num_txt",
            str(st.num), lnum_font,
            nx0, ny0, nsz, 1, WHITE,
            align="center", valign="middle", box_h=nsz,
            register=False,
        )
        boxes.append((f"list_{st.num}_num", nbox))

        # Text column
        lt_x0 = nx0 + nsz + sx(6)
        lt_x1 = X1 - sx(6)
        lt_w = lt_x1 - lt_x0

        # Line 1: CITY UPPERCASE + Dark Bold Headline (12px)
        line1_text = f"{st.topic_or_city} — {st.title}"
        draw_fitted_text(
            draw, boxes, f"list_{st.num}_title",
            line1_text, ltitle_font,
            lt_x0, ry0 + sx(2), lt_w, 1, INK_BLACK,
            align="left", valign="middle", box_h=sx(14),
        )

        # Line 2: Region tag + Source (9px italic) on left, Status pill on right
        st_col = STATUS_COLORS[st.status]
        st_tw = _text_width(st.status, status_font)
        pw = st_tw + sx(8)
        ph = sx(10)
        px0 = lt_x1 - pw
        py0 = ry0 + sx(17)
        prect = (px0, py0, lt_x1, py0 + ph)
        draw.rectangle(prect, fill=st_col)
        draw_fitted_text(
            draw, boxes, f"list_{st.num}_status_txt",
            st.status, status_font,
            px0, py0, pw, 1, WHITE,
            align="center", valign="middle", box_h=ph,
            register=False,
        )
        boxes.append((f"list_{st.num}_status", prect))

        # Region label
        reg_w = _text_width(st.region, lreg_font) + sx(1)
        draw_fitted_text(
            draw, boxes, f"list_{st.num}_region",
            st.region, lreg_font,
            lt_x0, py0, reg_w, 1, reg_col,
            align="left", valign="middle", box_h=ph,
        )

        # Source (9px italic)
        src_x0 = lt_x0 + reg_w + sx(3)
        src_w = (px0 - sx(6)) - src_x0
        draw_fitted_text(
            draw, boxes, f"list_{st.num}_source",
            f"· Source: {st.source}", lsrc_font,
            src_x0, py0, src_w, 1, INK_MUTED,
            align="left", valign="middle", box_h=ph,
        )

    # =========================================================================
    # 8. BOTTOM DATE CHECK BAR (y = 974..1000, deep black bar, white 9px)
    # =========================================================================
    dc_y0 = sx(974)
    dc_h = CANVAS_H - dc_y0  # 26 logical px = 104 physical px
    draw.rectangle((0, dc_y0, CANVAS_W, CANVAS_H), fill=DARK_BAR)
    dc_text = (
        "DATE CHECK — 2026-11-22 ONLY: STRICTLY LIMITED TO SUNDAY 22 NOVEMBER 2026 EVENTS · "
        "FRIDAY 20 NOV & SATURDAY 21 NOV OLD NEWS, RETRACTED ITEMS & DUPLICATES EXCLUDED · "
        "MULTI-SOURCE REPORTS MERGED"
    )
    draw_fitted_text(
        draw, boxes, "date_check",
        dc_text,
        load_font(FONT_SANS_CN_BOLD, sx(9)),
        X0, dc_y0, CW, 1, WHITE,
        align="center", valign="middle", box_h=dc_h,
    )

    # Run mandatory global pairwise collision check across ALL registered blocks
    pairs_checked = no_overlap(boxes)
    return img, region_counts, pairs_checked


def file_md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    img, region_counts, pairs_checked = build_poster()

    # Save deterministic PNG (no timestamps/metadata, optimize=True)
    img.save(OUT_MAIN, format="PNG", optimize=True, compress_level=9)
    size_bytes = os.path.getsize(OUT_MAIN)
    if size_bytes > MAX_PNG_BYTES:
        raise RuntimeError(
            f"entry.png exceeds 8MB SPEC cap: {size_bytes} bytes > {MAX_PNG_BYTES}"
        )

    # Generate 300x300 preview proportionally downscaled from 4000x4000 master
    preview = img.resize((300, 300), Image.Resampling.LANCZOS)
    preview.save(OUT_PREVIEW, format="PNG", optimize=True, compress_level=9)

    counts_str = " · ".join(f"{r} {region_counts[r]}" for r in REGION_ORDER)
    print(f"Stories: {len(STORIES)} (12 cards + 8 list items)")
    print(f"Regions: {counts_str} (sum={sum(region_counts.values())})")
    print(f"Master:  {img.size[0]}x{img.size[1]}, {size_bytes:,} bytes ({size_bytes / (1024*1024):.2f} MiB)")
    print(f"MD5:     {file_md5(OUT_MAIN)}")
    print(f"Preview: 300x300, {os.path.getsize(OUT_PREVIEW):,} bytes, md5={file_md5(OUT_PREVIEW)}")
    print(f"Overlap: 0 collisions across {pairs_checked:,} box pairs")


if __name__ == "__main__":
    main()

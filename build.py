#!/usr/bin/env python3
"""
World in One Day — Sunday 22 November 2026
Card-grid editorial front-page infographic generator (v3 SPEC).
Pure Python + Pillow vector/typographic rendering (deterministic, no external assets).
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Paths & Fonts
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent
ENTRY_PNG = ROOT_DIR / "entry.png"
PREVIEW_PNG = ROOT_DIR / "preview-300.png"

FONT_SERIF_BOLD = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyretermes-bold.otf"
FONT_SERIF_REG = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyretermes-regular.otf"
FONT_SERIF_ITAL = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyretermes-italic.otf"
FONT_SERIF_BOLDITAL = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyretermes-bolditalic.otf"
FONT_SANS_BOLD = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheros-bold.otf"
FONT_SANS_REG = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheros-regular.otf"
FONT_SANS_CN_BOLD = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheroscn-bold.otf"

# ---------------------------------------------------------------------------
# Palette (Editorial Broadsheet)
# ---------------------------------------------------------------------------
BG_PAPER = (246, 243, 235)       # #F6F3EB warm newsprint
BG_CARD = (255, 255, 255)        # #FFFFFF crisp card surface
BG_ILLUS = (250, 248, 242)       # #FAF8F2 warm illustration paper
BG_DARK = (20, 24, 31)           # #14181F masthead / footer ink
BG_SCORE = (252, 250, 246)       # #FCFAF6 scoreboard band

INK_BLACK = (18, 21, 27)         # #12151B primary ink
INK_DARK = (38, 44, 54)          # #262C36 secondary body ink
INK_MUTED = (86, 94, 108)        # #565E6C kicker / meta
RULE_LIGHT = (212, 205, 193)     # #D4CDC1 card borders & hairlines
RULE_MED = (176, 169, 156)       # #B0A99C medium rules
ACCENT_RED = (182, 31, 36)       # #B61F24 double-rule & summary red
WHITE = (255, 255, 255)
CREAM_TEXT = (244, 240, 232)

# 7 distinct region colors (Deep Blue / Brick Red / Forest Green / Purple / Orange / Cyan / Slate Gray)
REGION_ORDER = ["EUROPE", "MID EAST", "ASIA-PAC", "AMERICAS", "AFRICA", "CLIMATE", "AT SEA"]

REGION_DISPLAY = {
    "EUROPE": "EUROPE",
    "MID EAST": "MIDDLE EAST",
    "ASIA-PAC": "ASIA-PACIFIC",
    "AMERICAS": "AMERICAS",
    "AFRICA": "AFRICA",
    "CLIMATE": "CLIMATE",
    "AT SEA": "AT SEA",
}

REGION_COLORS: Dict[str, Tuple[int, int, int]] = {
    "EUROPE": (29, 62, 110),     # Deep Navy Blue
    "MID EAST": (166, 44, 43),   # Brick Red
    "ASIA-PAC": (30, 107, 82),   # Deep Forest Green
    "AMERICAS": (93, 58, 122),   # Editorial Purple
    "AFRICA": (194, 101, 26),    # Burnt Orange / Ochre
    "CLIMATE": (14, 116, 144),   # Deep Cyan / Teal
    "AT SEA": (71, 85, 105),     # Slate Gray-Blue
}

REGION_MAP_FILLS: Dict[str, Tuple[int, int, int]] = {
    "EUROPE": (132, 159, 196),
    "MID EAST": (212, 132, 130),
    "ASIA-PAC": (128, 184, 162),
    "AMERICAS": (167, 142, 191),
    "AFRICA": (226, 170, 118),
    "CLIMATE": (122, 188, 204),
    "AT SEA": (148, 163, 184),
}

STATUS_COLORS: Dict[str, Tuple[int, int, int]] = {
    "CONFIRMED": (21, 128, 61),  # Deep Green
    "REPORTED": (180, 83, 9),    # Deep Amber
    "CLAIM": (185, 28, 28),      # Deep Crimson
}

# ---------------------------------------------------------------------------
# Strict SPEC Data (20 Stories — exact titles, regions, sources, statuses)
# ---------------------------------------------------------------------------
DATE_STR = "Sunday 22 November 2026"
TOP_LEFT = "THE WORLD IN ONE DAY"
TOP_RIGHT = "20 STORIES · 7 REGIONS · EVERY ONE DATED SUNDAY 22 NOVEMBER 2026"
SUMMARY_STR = (
    "COP31 puts its final deal to the vote · "
    "Iran claims Patriot radar hit in Bahrain · "
    "Russia's overnight drones hit 19 sites in Ukraine"
)

SCOREBOARD = [
    ("74,742", "GAZA DEAD", "MID EAST"),
    ("03:00", "COP31 DEADLINE", "CLIMATE"),
    ("148", "DRONES OVER UKRAINE", "EUROPE"),
    ("41", "VIETNAM FLOOD DEAD", "ASIA-PAC"),
    ("450bn", "EU LOAN TO KYIV", "EUROPE"),
    ("17", "PAKISTAN CREW RECOVERED", "AT SEA"),
]

STORIES = [
    # --- 12 Cards (1–12) ---
    {
        "num": 1,
        "region": "CLIMATE",
        "topic": "SUMMIT",
        "title": "COP31 ends without a deal",
        "deck": "Final climate text goes to the floor past the 03:00 deadline without consensus.",
        "source": "Reuters, BBC, Guardian",
        "status": "CONFIRMED",
    },
    {
        "num": 2,
        "region": "MID EAST",
        "topic": "SECURITY",
        "title": "Iran claims strikes on two US bases",
        "deck": "Tehran claims hits on two US sites, including a Patriot radar in Bahrain.",
        "source": "Fars, Dawn",
        "status": "CLAIM",
    },
    {
        "num": 3,
        "region": "AT SEA",
        "topic": "NAVAL",
        "title": "Russian frigate Merkury ablaze in Benghazi",
        "deck": "Fire erupts aboard the Russian warship moored in Libya's eastern port.",
        "source": "AP, Al Jazeera, Reuters",
        "status": "CONFIRMED",
    },
    {
        "num": 4,
        "region": "AT SEA",
        "topic": "MARITIME",
        "title": "Maltese tanker hit by suicide drone boat",
        "deck": "Explosive uncrewed surface vessel strikes a Maltese-flagged merchant ship.",
        "source": "Reuters",
        "status": "CONFIRMED",
    },
    {
        "num": 5,
        "region": "EUROPE",
        "topic": "UKRAINE",
        "title": "Russian drones hit Dymer flats, 2 dead",
        "deck": "Overnight drone barrage strikes 19 Ukrainian sites, hitting residential flats.",
        "source": "Kyiv Independent",
        "status": "REPORTED",
    },
    {
        "num": 6,
        "region": "EUROPE",
        "topic": "ENERGY",
        "title": "Emergency blackouts across five regions",
        "deck": "Power operators impose emergency grid shutdowns after overnight strikes.",
        "source": "DTEK, Ukrenergo",
        "status": "CONFIRMED",
    },
    {
        "num": 7,
        "region": "MID EAST",
        "topic": "HORMUZ",
        "title": "Two VLCCs crippled by mines in Hormuz",
        "deck": "Iranian military claims sea mines disabled two very large crude carriers.",
        "source": "Iran military",
        "status": "CLAIM",
    },
    {
        "num": 8,
        "region": "MID EAST",
        "topic": "GAZA",
        "title": "Gaza death toll rises to 74,742",
        "deck": "Updated tally from the Gaza health ministry records 74,742 cumulative dead.",
        "source": "Gaza health ministry",
        "status": "CONFIRMED",
    },
    {
        "num": 9,
        "region": "AFRICA",
        "topic": "SUDAN",
        "title": "Drones hit Khartoum homes and UN site, 4 dead",
        "deck": "Strikes hit civilian residences and a United Nations facility in Khartoum.",
        "source": "WarStrikes",
        "status": "REPORTED",
    },
    {
        "num": 10,
        "region": "AFRICA",
        "topic": "UN REPORT",
        "title": "UN: drones cause nearly 3/4 of Sudan war deaths",
        "deck": "United Nations report finds drones account for nearly three-quarters of deaths.",
        "source": "Reuters",
        "status": "CONFIRMED",
    },
    {
        "num": 11,
        "region": "ASIA-PAC",
        "topic": "DISASTER",
        "title": "Vietnam floods kill at least 41",
        "deck": "Widespread flooding across Vietnam leaves at least 41 people confirmed dead.",
        "source": "multiple",
        "status": "CONFIRMED",
    },
    {
        "num": 12,
        "region": "ASIA-PAC",
        "topic": "EARTHQUAKE",
        "title": "Bangladesh quake kills 6, felt in Kolkata",
        "deck": "Earthquake kills six in Bangladesh, with tremors felt across eastern India.",
        "source": "multiple",
        "status": "CONFIRMED",
    },
    # --- 8 List Items (13–20) ---
    {
        "num": 13,
        "region": "EUROPE",
        "city": "BRATISLAVA",
        "title": "Fico refuses EU's €450bn loan to Ukraine",
        "source": "Reuters",
        "status": "CONFIRMED",
        "lon": 17.1,
        "lat": 48.1,
    },
    {
        "num": 14,
        "region": "EUROPE",
        "city": "BRUSSELS",
        "title": "Commission proposes €450bn loan for Kyiv",
        "source": "Reuters",
        "status": "CONFIRMED",
        "lon": 4.4,
        "lat": 50.8,
    },
    {
        "num": 15,
        "region": "AMERICAS",
        "city": "WASHINGTON",
        "title": "US pushes for Russia-Ukraine peace by early Jan 2027",
        "source": "FT",
        "status": "REPORTED",
        "lon": -77.0,
        "lat": 38.9,
    },
    {
        "num": 16,
        "region": "EUROPE",
        "city": "PARIS",
        "title": "French Senate passes police shooting law",
        "source": "Reuters",
        "status": "CONFIRMED",
        "lon": 2.3,
        "lat": 48.9,
    },
    {
        "num": 17,
        "region": "AMERICAS",
        "city": "MEXICO CITY",
        "title": "Mexico captures FBI ten most wanted fugitive",
        "source": "Reuters",
        "status": "CONFIRMED",
        "lon": -99.1,
        "lat": 19.4,
    },
    {
        "num": 18,
        "region": "ASIA-PAC",
        "city": "HONG KONG",
        "title": "Hong Kong election turnout hits record",
        "source": "China Daily",
        "status": "CONFIRMED",
        "lon": 114.2,
        "lat": 22.3,
    },
    {
        "num": 19,
        "region": "ASIA-PAC",
        "city": "ISLAMABAD",
        "title": "Pakistan's first astronaut departs for Beijing",
        "source": "APP",
        "status": "CONFIRMED",
        "lon": 73.0,
        "lat": 33.7,
    },
    {
        "num": 20,
        "region": "MID EAST",
        "city": "LAHJ",
        "title": "Missile hits Lahj health centre, about 10 dead",
        "source": "Soth24",
        "status": "CLAIM",
        "lon": 44.9,
        "lat": 13.1,
    },
]

DATE_CHECK_TEXT = (
    "DATE CHECK — 2026-11-22 ONLY: Every story verified for Sunday 22 November 2026. "
    "Friday/Saturday prior-day items, invalidated reports & duplicates explicitly excluded; "
    "multiple reports of the same event merged into single entries."
)

# ---------------------------------------------------------------------------
# Hard Constraints: fit() & no_overlap()
# ---------------------------------------------------------------------------
_FONT_CACHE: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}


def get_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    key = (font_path, size)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = ImageFont.truetype(font_path, size)
    return _FONT_CACHE[key]


def _ink_metrics(font: ImageFont.FreeTypeFont, text: str) -> Tuple[int, int, int, int]:
    """Return tight ink bounding box (x0, y0, x1, y1) at origin (0, 0)."""
    return font.getbbox(text)


def _measure_line(font: ImageFont.FreeTypeFont, text: str) -> Tuple[int, int]:
    bb = _ink_metrics(font, text)
    return (bb[2] - bb[0], bb[3] - bb[1])


def _wrap_words(
    text: str, font: ImageFont.FreeTypeFont, max_w: float, *, max_lines: int = 2, balance: bool = False
) -> Optional[List[str]]:
    words = text.split()
    if not words:
        return [""]
    if _measure_line(font, text)[0] <= max_w:
        return [text]

    # Balanced 2-line split avoids ugly 1-word orphans on headlines
    if balance and max_lines == 2 and len(words) >= 2:
        best: Optional[Tuple[float, List[str]]] = None
        for k in range(1, len(words)):
            l1 = " ".join(words[:k])
            l2 = " ".join(words[k:])
            w1 = _measure_line(font, l1)[0]
            w2 = _measure_line(font, l2)[0]
            if w1 <= max_w and w2 <= max_w:
                # Minimize worst line width + imbalance penalty
                score = max(w1, w2) + 0.35 * abs(w1 - w2)
                if best is None or score < best[0]:
                    best = (score, [l1, l2])
        if best is not None:
            return best[1]
        return None

    lines: List[str] = []
    cur = words[0]
    if _measure_line(font, cur)[0] > max_w:
        return None
    for w in words[1:]:
        cand = cur + " " + w
        if _measure_line(font, cand)[0] <= max_w:
            cur = cand
        else:
            lines.append(cur)
            cur = w
            if _measure_line(font, cur)[0] > max_w:
                return None
    lines.append(cur)
    return lines if len(lines) <= max_lines else None


def _block_ink_size(
    lines: Sequence[str], font: ImageFont.FreeTypeFont, size: int, line_step_ratio: float
) -> Tuple[int, int]:
    """Exact rendered ink width & height when lines are placed at top-aligned ink steps."""
    step = int(round(size * line_step_ratio))
    first_bb = _ink_metrics(font, lines[0])
    # Baseline of line 0 placed so top of line 0 ink sits at y = 0
    base0_y = -first_bb[1]
    min_y = 0
    max_y = first_bb[3] + base0_y
    max_w = first_bb[2] - first_bb[0]
    for idx in range(1, len(lines)):
        bb = _ink_metrics(font, lines[idx])
        base_y = base0_y + idx * step
        min_y = min(min_y, bb[1] + base_y)
        max_y = max(max_y, bb[3] + base_y)
        max_w = max(max_w, bb[2] - bb[0])
    return (max_w, max_y - min_y)


def fit(
    text: str,
    font_path: str,
    start_size: int,
    max_w: float,
    max_lines: int,
    *,
    min_size: int = 32,
    max_h: Optional[float] = None,
    line_step_ratio: float = 1.12,
    balance: bool = False,
) -> Tuple[ImageFont.FreeTypeFont, List[str], int, int, int]:
    """
    Measure tight ink bounding box of text wrapped to <= max_lines within max_w (and optional max_h).
    If text overflows, shrink font size by 1px down to min_size (8px * scale).
    If it still overflows at min_size, raise ValueError.
    Returns: (font, lines, total_w, total_h, chosen_size).
    """
    size = int(round(start_size))
    min_sz = int(round(min_size))
    while size >= min_sz:
        font = get_font(font_path, size)
        if max_lines == 1:
            w, _ = _measure_line(font, text)
            lines = [text] if w <= max_w else None
        else:
            lines = _wrap_words(text, font, max_w, max_lines=max_lines, balance=balance)

        if lines is not None and len(lines) <= max_lines:
            total_w, total_h = _block_ink_size(lines, font, size, line_step_ratio)
            if total_w <= max_w and (max_h is None or total_h <= max_h):
                return font, lines, total_w, total_h, size
        size -= 1

    raise ValueError(
        f"fit() failed: text={text!r} does not fit max_w={max_w:.1f}, "
        f"max_lines={max_lines}, max_h={max_h}, min_size={min_sz}"
    )


def boxes_intersect(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def no_overlap(
    boxes: Sequence[Tuple[str, Tuple[float, float, float, float]]],
    canvas_w: int,
    canvas_h: int,
) -> int:
    """
    Verify every registered bounding box is well-formed, inside canvas bounds,
    and pairwise non-overlapping. Raises RuntimeError on any violation.
    Returns total checked pair count.
    """
    for name, (x0, y0, x1, y1) in boxes:
        if x1 <= x0 or y1 <= y0:
            raise RuntimeError(f"Degenerate box {name}: {(x0, y0, x1, y1)}")
        if x0 < 0 or y0 < 0 or x1 > canvas_w or y1 > canvas_h:
            raise RuntimeError(
                f"Out-of-bounds box {name}: {(x0, y0, x1, y1)} vs canvas ({canvas_w}, {canvas_h})"
            )

    n = len(boxes)
    pairs = 0
    for i in range(n):
        na, ba = boxes[i]
        for j in range(i + 1, n):
            pairs += 1
            nb, bb = boxes[j]
            if boxes_intersect(ba, bb):
                raise RuntimeError(f"Collision detected: {na} {ba} overlaps {nb} {bb}")
    return pairs


def draw_fitted_lines(
    draw: ImageDraw.ImageDraw,
    lines: Sequence[str],
    font: ImageFont.FreeTypeFont,
    x: float,
    y: float,
    color: Tuple[int, int, int],
    *,
    align: str = "left",
    box_w: Optional[float] = None,
    line_step_ratio: float = 1.12,
    size: int = 40,
) -> Tuple[float, float, float, float]:
    """
    Draw wrapped lines with exact tight ink top-alignment at y (eliminating invisible ascender
    headroom drift) and tight editorial line leading (size * line_step_ratio).
    Returns exact rendered tight ink bounding box (x0, y0, x1, y1).
    """
    step = int(round(size * line_step_ratio))
    first_bb = _ink_metrics(font, lines[0])
    base0_y = y - first_bb[1]

    min_x, min_y = float("inf"), float("inf")
    max_x, max_y = float("-inf"), float("-inf")

    for idx, ln in enumerate(lines):
        lbb = _ink_metrics(font, ln)
        lw = lbb[2] - lbb[0]
        if align == "center" and box_w is not None:
            lx = x + (box_w - lw) / 2.0 - lbb[0]
        elif align == "right" and box_w is not None:
            lx = x + (box_w - lw) - lbb[0]
        else:
            lx = x - lbb[0]

        ly = base0_y + idx * step
        tb = draw.textbbox((lx, ly), ln, font=font)
        draw.text((lx, ly), ln, font=font, fill=color)
        min_x = min(min_x, tb[0])
        min_y = min(min_y, tb[1])
        max_x = max(max_x, tb[2])
        max_y = max(max_y, tb[3])

    return (min_x, min_y, max_x, max_y)


# ---------------------------------------------------------------------------
# Bespoke Line-Art Illustrations (12 cards, stroke 2px*scale, ZERO faces)
# ---------------------------------------------------------------------------
def _blend(c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    return (
        int(round(c1[0] + (c2[0] - c1[0]) * t)),
        int(round(c1[1] + (c2[1] - c1[1]) * t)),
        int(round(c1[2] + (c2[2] - c1[2]) * t)),
    )


def draw_card_illustration(
    draw: ImageDraw.ImageDraw,
    story_num: int,
    box: Tuple[int, int, int, int],
    region_color: Tuple[int, int, int],
    scale: float,
) -> None:
    x0, y0, x1, y1 = box
    w = x1 - x0
    h = y1 - y0
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0

    lw = max(2, int(round(2.0 * scale)))      # 8px primary stroke at 4x
    thin = max(1, int(round(1.2 * scale)))    # 5px secondary line
    ink = INK_BLACK
    tint = _blend(BG_ILLUS, region_color, 0.22)
    accent = region_color

    # Framed paper background
    draw.rectangle(box, fill=BG_ILLUS, outline=RULE_LIGHT, width=max(1, int(round(1.0 * scale))))

    px0, py0 = x0 + w * 0.10, y0 + h * 0.08
    px1, py1 = x1 - w * 0.10, y1 - h * 0.08
    pw, ph = px1 - px0, py1 - py0

    if story_num == 1:
        # COP31 ends without a deal: 03:00 clock dial above fractured Earth globe
        cr = pw * 0.24
        ccy = py0 + cr + ph * 0.03
        draw.ellipse([cx - cr, ccy - cr, cx + cr, ccy + cr], fill=tint, outline=ink, width=lw)
        draw.line([(cx, ccy), (cx, ccy - cr * 0.62)], fill=ink, width=lw)
        draw.line([(cx, ccy), (cx + cr * 0.56, ccy)], fill=ACCENT_RED, width=lw)

        gr = pw * 0.44
        gcy = py1 - gr - ph * 0.04
        draw.ellipse([cx - gr, gcy - gr, cx + gr, gcy + gr], fill=tint, outline=ink, width=lw)
        draw.line([(cx - gr, gcy), (cx + gr, gcy)], fill=ink, width=thin)
        draw.arc([cx - gr * 0.9, gcy - gr * 0.55, cx + gr * 0.9, gcy + gr * 0.55], 0, 360, fill=ink, width=thin)
        draw.ellipse([cx - gr * 0.48, gcy - gr, cx + gr * 0.48, gcy + gr], outline=ink, width=thin)
        crack = [
            (cx - gr * 0.18, gcy - gr * 0.85),
            (cx + gr * 0.12, gcy - gr * 0.30),
            (cx - gr * 0.16, gcy + gr * 0.12),
            (cx + gr * 0.20, gcy + gr * 0.82),
        ]
        draw.line(crack, fill=ACCENT_RED, width=lw)

    elif story_num == 2:
        # Iran claims strikes on two US bases: Vertically balanced radar dish + missile arcs + starburst
        by = py1 - ph * 0.14
        draw.line([(px0, by), (px1, by)], fill=ink, width=lw)
        # Radar pedestal
        ped = [(cx - pw * 0.18, by), (cx + pw * 0.18, by), (cx + pw * 0.07, by - ph * 0.20), (cx - pw * 0.07, by - ph * 0.20)]
        draw.polygon(ped, fill=tint)
        draw.line(ped + [ped[0]], fill=ink, width=lw)
        # Parabolic dish (centered higher)
        dcx, dcy = cx - pw * 0.06, by - ph * 0.36
        dr = pw * 0.36
        draw.arc([dcx - dr, dcy - dr, dcx + dr, dcy + dr], 130, 310, fill=ink, width=lw)
        draw.line([(dcx - dr * 0.65, dcy - dr * 0.75), (dcx + dr * 0.65, dcy + dr * 0.75)], fill=ink, width=thin)
        draw.line([(dcx, dcy), (dcx + dr * 0.62, dcy - dr * 0.62)], fill=ink, width=lw)
        draw.ellipse([dcx + dr * 0.53, dcy - dr * 0.71, dcx + dr * 0.71, dcy - dr * 0.53], fill=accent, outline=ink, width=thin)
        # Incoming dashed missile arcs from top-right
        for idx, offset in enumerate([0.0, 0.15]):
            sx, sy = px1 - pw * 0.02, py0 + ph * (0.04 + offset)
            ex, ey = dcx + dr * (0.35 + idx * 0.25), dcy - dr * (0.55 - idx * 0.22)
            steps = 6
            for s in range(0, steps, 2):
                t0, t1 = s / steps, min(1.0, (s + 1.15) / steps)
                draw.line(
                    [(sx + (ex - sx) * t0, sy + (ey - sy) * t0), (sx + (ex - sx) * t1, sy + (ey - sy) * t1)],
                    fill=accent,
                    width=lw,
                )
        # Impact starburst in upper quadrant
        bx, bys = cx + pw * 0.14, py0 + ph * 0.24
        for ang in range(0, 360, 45):
            rad = math.radians(ang)
            r_in = pw * 0.07
            r_out = pw * (0.24 if ang % 90 == 0 else 0.15)
            draw.line(
                [(bx + math.cos(rad) * r_in, bys + math.sin(rad) * r_in),
                 (bx + math.cos(rad) * r_out, bys + math.sin(rad) * r_out)],
                fill=accent,
                width=lw,
            )

    elif story_num == 3:
        # Russian frigate Merkury ablaze in Benghazi: Warship hull + refined layered smoke & flames
        wy = py1 - ph * 0.16
        for wy_off in [0, ph * 0.075]:
            pts = [
                (px0 + pw * (i / 8.0), wy + wy_off + (ph * 0.022 if i % 2 == 0 else -ph * 0.022))
                for i in range(9)
            ]
            draw.line(pts, fill=ink, width=thin)
        # Naval frigate hull
        hull = [
            (px0 + pw * 0.04, wy - ph * 0.09),
            (px1 - pw * 0.04, wy - ph * 0.09),
            (px1 - pw * 0.14, wy),
            (px0 + pw * 0.12, wy),
        ]
        draw.polygon(hull, fill=tint)
        draw.line(hull + [hull[0]], fill=ink, width=lw)
        # Superstructure & mast
        draw.rectangle([cx - pw * 0.24, wy - ph * 0.22, cx + pw * 0.16, wy - ph * 0.09], fill=BG_ILLUS, outline=ink, width=lw)
        draw.line([(cx - pw * 0.10, wy - ph * 0.22), (cx - pw * 0.10, wy - ph * 0.38)], fill=ink, width=lw)
        draw.line([(cx - pw * 0.20, wy - ph * 0.31), (cx, wy - ph * 0.31)], fill=ink, width=thin)
        # Rising smoke plume (smooth continuous silhouette via overlapping filled/outlined arcs)
        smoke_path = [
            (cx + pw * 0.02, wy - ph * 0.34),
            (cx - pw * 0.10, py0 + ph * 0.34),
            (cx - pw * 0.02, py0 + ph * 0.16),
            (cx + pw * 0.20, py0 + ph * 0.06),
            (cx + pw * 0.36, py0 + ph * 0.18),
            (cx + pw * 0.22, py0 + ph * 0.34),
            (cx + pw * 0.20, wy - ph * 0.30),
        ]
        draw.polygon(smoke_path, fill=_blend(BG_ILLUS, INK_MUTED, 0.18))
        draw.line(smoke_path, fill=ink, width=lw)
        # Crisp multi-lick fire at midship
        flame = [
            (cx - pw * 0.06, wy - ph * 0.22),
            (cx - pw * 0.02, wy - ph * 0.36),
            (cx + pw * 0.06, wy - ph * 0.28),
            (cx + pw * 0.14, wy - ph * 0.42),
            (cx + pw * 0.24, wy - ph * 0.22),
        ]
        draw.polygon(flame, fill=_blend(BG_ILLUS, ACCENT_RED, 0.30))
        draw.line(flame, fill=ACCENT_RED, width=lw)

    elif story_num == 4:
        # Maltese tanker hit by suicide drone boat: Centered vertically in frame
        wy = py0 + ph * 0.56
        # Large tanker hull
        hull = [
            (px0 + pw * 0.02, wy - ph * 0.16),
            (px1 - pw * 0.06, wy - ph * 0.16),
            (px1 - pw * 0.14, wy),
            (px0 + pw * 0.06, wy),
        ]
        draw.polygon(hull, fill=tint)
        draw.line(hull + [hull[0]], fill=ink, width=lw)
        # Stern bridge & funnel
        draw.rectangle([px0 + pw * 0.08, wy - ph * 0.34, px0 + pw * 0.34, wy - ph * 0.16], fill=BG_ILLUS, outline=ink, width=lw)
        draw.rectangle([px0 + pw * 0.14, wy - ph * 0.43, px0 + pw * 0.25, wy - ph * 0.34], fill=accent, outline=ink, width=thin)
        for hx in [0.44, 0.60, 0.74]:
            draw.rectangle([px0 + pw * hx, wy - ph * 0.22, px0 + pw * (hx + 0.10), wy - ph * 0.16], outline=ink, width=thin)
        # Waterline wave
        pts = [(px0 + pw * (i / 8.0), wy + ph * 0.03 + (ph * 0.015 if i % 2 == 0 else -ph * 0.015)) for i in range(9)]
        draw.line(pts, fill=ink, width=thin)
        # Impact starburst at starboard side
        ix, iy = cx + pw * 0.14, wy - ph * 0.06
        for ang in [-150, -110, -70, -30, 10]:
            rad = math.radians(ang)
            draw.line(
                [(ix + math.cos(rad) * pw * 0.07, iy + math.sin(rad) * pw * 0.07),
                 (ix + math.cos(rad) * pw * 0.26, iy + math.sin(rad) * pw * 0.26)],
                fill=ACCENT_RED,
                width=lw,
            )
        # Uncrewed wedge drone boat speeding in foreground
        dy = py1 - ph * 0.16
        drone_boat = [
            (cx - pw * 0.06, dy - ph * 0.04),
            (px1 - pw * 0.04, dy - ph * 0.06),
            (px1 - pw * 0.10, dy + ph * 0.03),
            (cx - pw * 0.02, dy + ph * 0.03),
        ]
        draw.polygon(drone_boat, fill=accent)
        draw.line(drone_boat + [drone_boat[0]], fill=ink, width=lw)
        # Speed wake lines
        draw.line([(px0 + pw * 0.08, dy + ph * 0.04), (cx - pw * 0.08, dy + ph * 0.04)], fill=ink, width=thin)
        draw.line([(px0 + pw * 0.18, dy + ph * 0.09), (px1 - pw * 0.10, dy + ph * 0.09)], fill=ink, width=thin)

    elif story_num == 5:
        # Russian drones hit Dymer flats, 2 dead: Apartment block + delta-wing drone
        bx0, by0 = px0 + pw * 0.10, py0 + ph * 0.34
        bx1, by1 = px1 - pw * 0.14, py1 - ph * 0.04
        draw.rectangle([bx0, by0, bx1, by1], fill=tint, outline=ink, width=lw)
        cols, rows = 3, 4
        ww = (bx1 - bx0) / (cols * 2 + 1)
        wh = (by1 - by0) / (rows * 2 + 1)
        for r in range(rows):
            for c in range(cols):
                wx0 = bx0 + ww * (1 + c * 2)
                wy0 = by0 + wh * (1 + r * 2)
                fill_w = BG_ILLUS if not (r == 0 and c == 2) else ACCENT_RED
                draw.rectangle([wx0, wy0, wx0 + ww, wy0 + wh], fill=fill_w, outline=ink, width=thin)
        for ang in [-140, -90, -45, 5]:
            rad = math.radians(ang)
            draw.line(
                [(bx1 - pw * 0.04, by0 + ph * 0.04),
                 (bx1 - pw * 0.04 + math.cos(rad) * pw * 0.22, by0 + ph * 0.04 + math.sin(rad) * pw * 0.22)],
                fill=ACCENT_RED,
                width=lw,
            )
        dtx, dty = cx + pw * 0.12, py0 + ph * 0.24
        delta = [
            (dtx, dty),
            (px0 + pw * 0.06, py0 + ph * 0.08),
            (px0 + pw * 0.34, py0 + ph * 0.05),
        ]
        draw.polygon(delta, fill=accent)
        draw.line(delta + [delta[0]], fill=ink, width=lw)
        draw.line([(px0 + pw * 0.04, py0 + ph * 0.14), (dtx - pw * 0.14, dty - ph * 0.05)], fill=ink, width=thin)

    elif story_num == 6:
        # Emergency blackouts across five regions: Transmission pylon + blackout emblem
        top_y = py0 + ph * 0.12
        bot_y = py1 - ph * 0.06
        draw.line([(cx, top_y), (cx - pw * 0.24, bot_y)], fill=ink, width=lw)
        draw.line([(cx, top_y), (cx + pw * 0.24, bot_y)], fill=ink, width=lw)
        for ay, aw in [(top_y + ph * 0.14, pw * 0.38), (top_y + ph * 0.32, pw * 0.44)]:
            draw.line([(cx - aw, ay), (cx + aw, ay)], fill=ink, width=lw)
            draw.line([(cx - aw, ay), (cx - aw, ay + ph * 0.06)], fill=ink, width=thin)
            draw.line([(cx + aw, ay), (cx + aw, ay + ph * 0.06)], fill=ink, width=thin)
        for f0, f1 in [(0.32, 0.56), (0.56, 0.80), (0.80, 1.0)]:
            y_a = top_y + (bot_y - top_y) * f0
            y_b = top_y + (bot_y - top_y) * f1
            wa = pw * 0.24 * f0
            wb = pw * 0.24 * f1
            draw.line([(cx - wa, y_a), (cx + wb, y_b)], fill=ink, width=thin)
            draw.line([(cx + wa, y_a), (cx - wb, y_b)], fill=ink, width=thin)
        bolt = [
            (cx + pw * 0.10, py0 + ph * 0.44),
            (cx - pw * 0.08, py0 + ph * 0.62),
            (cx + pw * 0.04, py0 + ph * 0.62),
            (cx - pw * 0.10, py0 + ph * 0.82),
        ]
        draw.line(bolt, fill=ACCENT_RED, width=lw)
        br = pw * 0.24
        bcy = py0 + ph * 0.62
        draw.ellipse([cx - br, bcy - br, cx + br, bcy + br], outline=accent, width=lw)
        draw.line([(cx - br * 0.72, bcy - br * 0.72), (cx + br * 0.72, bcy + br * 0.72)], fill=ACCENT_RED, width=lw)

    elif story_num == 7:
        # Two VLCCs crippled by mines in Hormuz: Sea mine + tilted tankers above
        wy = py0 + ph * 0.32
        pts = [(px0 + pw * (i / 8.0), wy + (ph * 0.025 if i % 2 == 0 else -ph * 0.025)) for i in range(9)]
        draw.line(pts, fill=ink, width=lw)
        for tx0, tx1, tilt in [(px0 + pw * 0.04, cx - pw * 0.04, -ph * 0.03), (cx + pw * 0.04, px1 - pw * 0.04, ph * 0.03)]:
            hull_t = [(tx0, wy - ph * 0.09 + tilt), (tx1, wy - ph * 0.09 - tilt),
                      (tx1 - pw * 0.04, wy - tilt * 0.5), (tx0 + pw * 0.04, wy + tilt * 0.5)]
            draw.polygon(hull_t, fill=tint)
            draw.line(hull_t + [hull_t[0]], fill=ink, width=thin)
        mcx, mcy = cx, py0 + ph * 0.62
        mr = pw * 0.25
        draw.ellipse([mcx - mr, mcy - mr, mcx + mr, mcy + mr], fill=tint, outline=ink, width=lw)
        draw.ellipse([mcx - mr * 0.35, mcy - mr * 0.35, mcx + mr * 0.35, mcy + mr * 0.35], outline=accent, width=thin)
        for ang in range(0, 360, 45):
            rad = math.radians(ang)
            draw.line(
                [(mcx + math.cos(rad) * mr, mcy + math.sin(rad) * mr),
                 (mcx + math.cos(rad) * (mr * 1.48), mcy + math.sin(rad) * (mr * 1.48))],
                fill=accent if ang % 90 == 0 else ink,
                width=lw,
            )
        for cy_link in range(4):
            ly = mcy + mr * 1.3 + cy_link * ph * 0.055
            if ly < py1:
                draw.ellipse([mcx - pw * 0.04, ly, mcx + pw * 0.04, ly + ph * 0.045], outline=ink, width=thin)

    elif story_num == 8:
        # Gaza death toll rises to 74,742: Clean fractured architectural pillars + crisp rising count trend arrow
        by = py1 - ph * 0.08
        draw.line([(px0, by), (px1, by)], fill=ink, width=lw)
        # Left broken architectural column
        p1 = [(px0 + pw * 0.08, by), (px0 + pw * 0.08, py0 + ph * 0.44),
              (px0 + pw * 0.20, py0 + ph * 0.50), (px0 + pw * 0.32, py0 + ph * 0.40),
              (px0 + pw * 0.32, by)]
        draw.polygon(p1, fill=tint)
        draw.line(p1, fill=ink, width=lw)
        # Right taller fractured column
        p2 = [(cx + pw * 0.04, by), (cx + pw * 0.04, py0 + ph * 0.32),
              (cx + pw * 0.18, py0 + ph * 0.26), (cx + pw * 0.34, py0 + ph * 0.36),
              (cx + pw * 0.34, by)]
        draw.polygon(p2, fill=tint)
        draw.line(p2, fill=ink, width=lw)
        # Fallen rubble block
        draw.rectangle([cx - pw * 0.14, by - ph * 0.12, cx + pw * 0.10, by], fill=BG_ILLUS, outline=ink, width=lw)
        # Clean, crisp rising step-trend arrow above (zero loops/squiggles)
        ax0, ay0 = px0 + pw * 0.08, py0 + ph * 0.26
        ax1, ay1 = cx - pw * 0.04, py0 + ph * 0.20
        ax2, ay2 = px1 - pw * 0.08, py0 + ph * 0.08
        draw.line([(ax0, ay0), (ax1, ay1), (ax2, ay2)], fill=accent, width=lw)
        # Clean arrowhead at (ax2, ay2)
        draw.line([(ax2 - pw * 0.18, ay2), (ax2, ay2), (ax2 - pw * 0.05, ay2 + ph * 0.10)], fill=accent, width=lw)

    elif story_num == 9:
        # Drones hit Khartoum homes and UN site, 4 dead: Drone cleanly separated above crosshair & compound
        by = py1 - ph * 0.07
        draw.rectangle([px0 + pw * 0.04, by - ph * 0.24, px1 - pw * 0.04, by], fill=tint, outline=ink, width=lw)
        draw.rectangle([px0 + pw * 0.14, by - ph * 0.36, cx + pw * 0.06, by - ph * 0.24], fill=BG_ILLUS, outline=ink, width=lw)
        # UN flag pole on right
        fx = px1 - pw * 0.20
        draw.line([(fx, by - ph * 0.24), (fx, by - ph * 0.44)], fill=ink, width=lw)
        draw.rectangle([fx, by - ph * 0.44, fx + pw * 0.18, by - ph * 0.34], fill=REGION_COLORS["CLIMATE"], outline=ink, width=thin)
        # Drone silhouette cleanly separated at top
        dy = py0 + ph * 0.11
        draw.line([(cx - pw * 0.36, dy), (cx + pw * 0.36, dy)], fill=ink, width=lw)
        draw.line([(cx, dy - ph * 0.04), (cx, dy + ph * 0.07)], fill=ink, width=lw)
        draw.line([(cx - pw * 0.13, dy + ph * 0.07), (cx + pw * 0.13, dy + ph * 0.07)], fill=ink, width=thin)
        # Target crosshairs cleanly centered below drone (zero overlap with drone)
        tcx, tcy = cx, py0 + ph * 0.43
        tr = pw * 0.24
        draw.ellipse([tcx - tr, tcy - tr, tcx + tr, tcy + tr], outline=accent, width=lw)
        draw.line([(tcx - tr * 1.28, tcy), (tcx + tr * 1.28, tcy)], fill=accent, width=thin)
        draw.line([(tcx, tcy - tr * 1.28), (tcx, tcy + tr * 1.28)], fill=accent, width=thin)

    elif story_num == 10:
        # UN: drones cause nearly 3/4 of Sudan war deaths: 3/4 donut chart with roomy center + drone
        dy = py0 + ph * 0.13
        draw.line([(cx - pw * 0.36, dy), (cx + pw * 0.36, dy)], fill=ink, width=lw)
        draw.line([(cx, dy - ph * 0.05), (cx, dy + ph * 0.09)], fill=ink, width=lw)
        draw.polygon([(cx - pw * 0.13, dy + ph * 0.09), (cx + pw * 0.13, dy + ph * 0.09), (cx, dy + ph * 0.02)], fill=accent)
        pr = pw * 0.43
        pcy = py1 - pr - ph * 0.07
        draw.pieslice([cx - pr, pcy - pr, cx + pr, pcy + pr], start=-90, end=180, fill=tint, outline=ink, width=lw)
        draw.pieslice([cx - pr, pcy - pr, cx + pr, pcy + pr], start=180, end=270, fill=BG_ILLUS, outline=ink, width=thin)
        ir = pr * 0.49
        draw.ellipse([cx - ir, pcy - ir, cx + ir, pcy + ir], fill=BG_ILLUS, outline=ink, width=lw)
        f_lbl = get_font(FONT_SANS_BOLD, max(12, int(round(9.0 * scale))))
        draw.text((cx, pcy), "3/4", font=f_lbl, fill=accent, anchor="mm")

    elif story_num == 11:
        # Vietnam floods kill at least 41: Submerged pitched-roof house + rolling waves + rain
        for i in range(5):
            rx = px0 + pw * (0.10 + i * 0.20)
            ry = py0 + ph * (0.04 + (i % 2) * 0.06)
            draw.line([(rx, ry), (rx - pw * 0.08, ry + ph * 0.16)], fill=accent, width=thin)
        wy = py0 + ph * 0.56
        roof = [(cx - pw * 0.36, wy - ph * 0.06), (cx, wy - ph * 0.28), (cx + pw * 0.36, wy - ph * 0.06)]
        draw.polygon(roof, fill=tint)
        draw.line(roof + [roof[0]], fill=ink, width=lw)
        draw.rectangle([cx - pw * 0.26, wy - ph * 0.06, cx + pw * 0.26, wy + ph * 0.08], fill=BG_ILLUS, outline=ink, width=lw)
        for r_idx in range(3):
            y_wave = wy + ph * (0.06 + r_idx * 0.14)
            pts = [
                (px0 + pw * (i / 10.0), y_wave + math.sin(i * 1.15 + r_idx) * ph * 0.032)
                for i in range(11)
            ]
            draw.line(pts, fill=accent if r_idx == 0 else ink, width=lw)

    elif story_num == 12:
        # Bangladesh quake kills 6, felt in Kolkata: Seismograph wave + concentric rings + fault
        sy = py0 + ph * 0.24
        draw.line([(px0, sy), (px1, sy)], fill=RULE_MED, width=thin)
        seismo = [
            (px0, sy), (px0 + pw * 0.20, sy), (px0 + pw * 0.28, sy - ph * 0.08),
            (px0 + pw * 0.36, sy + ph * 0.10), (px0 + pw * 0.45, sy - ph * 0.18),
            (px0 + pw * 0.54, sy + ph * 0.17), (px0 + pw * 0.64, sy - ph * 0.11),
            (px0 + pw * 0.74, sy + ph * 0.06), (px0 + pw * 0.84, sy), (px1, sy),
        ]
        draw.line(seismo, fill=ACCENT_RED, width=lw)
        ecy = py1 - ph * 0.30
        for mult, col in [(0.42, ink), (0.28, accent), (0.14, ink)]:
            rr = pw * mult
            draw.ellipse([cx - rr, ecy - rr, cx + rr, ecy + rr], outline=col, width=lw if mult != 0.28 else thin)
        fault = [
            (px0 + pw * 0.12, ecy - ph * 0.18), (cx - pw * 0.04, ecy - ph * 0.04),
            (cx + pw * 0.08, ecy + ph * 0.04), (px1 - pw * 0.10, ecy + ph * 0.20),
        ]
        draw.line(fault, fill=ink, width=lw)


# ---------------------------------------------------------------------------
# Stylized World Map (7 Regions Colored + Markers 13–20)
# ---------------------------------------------------------------------------
WORLD_POLYGONS: List[Tuple[str, List[Tuple[float, float]]]] = [
    ("AMERICAS", [
        (-164, 65), (-145, 70), (-125, 70), (-100, 68), (-82, 64), (-78, 53),
        (-62, 52), (-54, 47), (-66, 44), (-72, 41), (-76, 35), (-81, 25),
        (-83, 29), (-90, 29), (-97, 26), (-96, 19), (-88, 21), (-83, 10),
        (-78, 8), (-85, 11), (-92, 15), (-105, 20), (-112, 29), (-118, 34),
        (-124, 42), (-125, 50), (-138, 59), (-154, 58), (-164, 61),
    ]),
    ("AMERICAS", [
        (-52, 60), (-42, 60), (-22, 70), (-20, 77), (-45, 77), (-62, 74), (-56, 66),
    ]),
    ("AMERICAS", [
        (-78, 9), (-71, 12), (-61, 10), (-50, 2), (-35, -6), (-38, -14),
        (-42, -23), (-53, -34), (-64, -42), (-68, -55), (-74, -52), (-72, -35),
        (-71, -18), (-81, -5), (-79, 2),
    ]),
    ("EUROPE", [
        (-9, 37), (-9, 43), (-2, 43), (-4, 48), (2, 51), (8, 54), (10, 57),
        (14, 54), (21, 55), (28, 60), (42, 66), (56, 68), (58, 52), (46, 46),
        (38, 45), (30, 46), (28, 41), (23, 38), (19, 40), (14, 45), (16, 40),
        (12, 42), (8, 44), (4, 43), (0, 39), (-5, 36),
    ]),
    ("EUROPE", [
        (5, 60), (10, 59), (15, 56), (20, 60), (22, 65), (29, 71), (20, 70),
        (12, 66), (6, 62),
    ]),
    ("EUROPE", [
        (-6, 50), (1, 51), (-1, 55), (-5, 58), (-8, 54),
    ]),
    ("EUROPE", [
        (-24, 64), (-14, 64), (-15, 66), (-23, 66),
    ]),
    ("AFRICA", [
        (-16, 15), (-13, 28), (-6, 36), (10, 37), (12, 33), (25, 32), (32, 31),
        (37, 21), (43, 12), (51, 11), (46, 2), (40, -10), (35, -24), (28, -33),
        (18, -35), (14, -22), (12, -6), (9, 4), (-2, 5), (-12, 7),
    ]),
    ("AFRICA", [
        (44, -25), (47, -25), (50, -13), (47, -15),
    ]),
    ("MID EAST", [
        (27, 41), (36, 42), (44, 40), (49, 38), (56, 38), (61, 35), (61, 25),
        (56, 26), (59, 22), (52, 16), (44, 13), (40, 20), (35, 29), (35, 36),
        (27, 37),
    ]),
    ("ASIA-PAC", [
        (58, 68), (85, 73), (125, 72), (168, 66), (162, 58), (142, 54), (135, 44),
        (128, 35), (122, 39), (120, 31), (121, 23), (114, 22), (108, 16),
        (109, 10), (103, 2), (100, 14), (96, 17), (90, 22), (82, 15), (77, 8),
        (72, 20), (67, 25), (61, 25), (61, 37), (54, 42), (58, 52),
    ]),
    ("ASIA-PAC", [
        (130, 31), (135, 34), (141, 38), (144, 44), (140, 42), (136, 37), (131, 34),
    ]),
    ("ASIA-PAC", [
        (96, 5), (105, -6), (118, -8), (126, -6), (124, 1), (116, 4), (108, 1),
    ]),
    ("ASIA-PAC", [
        (120, 18), (123, 17), (126, 8), (122, 7), (120, 13),
    ]),
    ("ASIA-PAC", [
        (114, -22), (124, -16), (136, -12), (143, -11), (153, -27), (150, -37),
        (138, -35), (129, -32), (115, -34), (113, -26),
    ]),
    ("ASIA-PAC", [
        (167, -46), (173, -42), (177, -37), (174, -36), (170, -42),
    ]),
    ("CLIMATE", [
        (-166, -59), (-110, -56), (-62, -58), (-20, -56), (40, -55),
        (100, -57), (155, -56), (177, -59), (177, -61), (-166, -61),
    ]),
]

# Carefully tuned callout pin offsets (logical px) — clear of borders and each other
MAP_CALLOUT_OFFSETS: Dict[int, Tuple[float, float]] = {
    13: (26, -15),   # Bratislava -> northeast
    14: (-3, -23),   # Brussels -> north (generous margin below top map frame)
    15: (-20, -22),  # Washington -> northwest
    16: (-28, -2),   # Paris -> west/Atlantic
    17: (-24, 20),   # Mexico City -> southwest
    18: (24, 16),    # Hong Kong -> southeast
    19: (14, -24),   # Islamabad -> north
    20: (24, 18),    # Lahj -> southeast/Indian Ocean
}


def draw_world_map(
    draw: ImageDraw.ImageDraw,
    panel_box: Tuple[int, int, int, int],
    list_stories: Sequence[dict],
    scale: float,
    boxes: List[Tuple[str, Tuple[float, float, float, float]]],
) -> None:
    x0, y0, x1, y1 = panel_box
    pw = x1 - x0
    lw_border = max(1, int(round(1.0 * scale)))

    # Panel container
    draw.rectangle(panel_box, fill=BG_CARD, outline=RULE_LIGHT, width=lw_border)
    draw.rectangle([x0, y0, x1, y0 + int(round(2.5 * scale))], fill=INK_BLACK)

    # Panel header
    hdr_pad_x = int(round(8 * scale))
    hdr_y = y0 + int(round(6.5 * scale))
    hdr_font, hdr_lines, _, _, hdr_sz = fit(
        "GLOBAL DISPATCH MAP · 7 REGIONS · STORIES 13–20",
        FONT_SANS_BOLD,
        int(round(9.5 * scale)),
        pw - hdr_pad_x * 2,
        1,
        min_size=int(round(8 * scale)),
    )
    hdr_bb = draw_fitted_lines(draw, hdr_lines, hdr_font, x0 + hdr_pad_x, hdr_y, INK_BLACK, size=hdr_sz)
    boxes.append(("map_header", hdr_bb))

    # Map viewport
    mx0 = x0 + int(round(8 * scale))
    my0 = int(hdr_bb[3] + round(5 * scale))
    mx1 = x1 - int(round(8 * scale))
    my1 = y1 - int(round(21 * scale))
    mw = mx1 - mx0
    mh = my1 - my0

    ocean = (232, 240, 247)
    grid_col = (210, 223, 234)
    draw.rectangle([mx0, my0, mx1, my1], fill=ocean, outline=RULE_MED, width=lw_border)

    lon_min, lon_max = -168.0, 178.0
    lat_min, lat_max = -61.0, 77.0

    def proj(lon: float, lat: float) -> Tuple[float, float]:
        px = mx0 + (lon - lon_min) / (lon_max - lon_min) * mw
        py = my1 - (lat - lat_min) / (lat_max - lat_min) * mh
        return (px, py)

    # Graticule lines
    grid_w = max(1, int(round(0.6 * scale)))
    for lat in [-30, 0, 30, 60]:
        _, gy = proj(0, lat)
        draw.line([(mx0, gy), (mx1, gy)], fill=grid_col, width=grid_w)
    for lon in [-120, -60, 0, 60, 120]:
        gx, _ = proj(lon, 0)
        draw.line([(gx, my0), (gx, my1)], fill=grid_col, width=grid_w)

    # Continents / 7 region polygons (clean coastlines, no intrusive stray strokes)
    outline_w = max(1, int(round(0.9 * scale)))
    for region, poly in WORLD_POLYGONS:
        pts = [proj(lo, la) for lo, la in poly]
        draw.polygon(pts, fill=REGION_MAP_FILLS[region])
        draw.line(pts + [pts[0]], fill=REGION_COLORS[region], width=outline_w)

    # Subtle open-ocean maritime dashed markers for AT SEA (Mid-Atlantic & Indian Ocean, clear of land & pins)
    dash_w = max(2, int(round(1.1 * scale)))
    for seg in [
        [(-45, 22), (-37, 25)], [(-32, 27), (-24, 29)],
        [(62, 5), (70, 2)], [(75, 0), (84, -3)],
    ]:
        draw.line([proj(*seg[0]), proj(*seg[1])], fill=REGION_MAP_FILLS["AT SEA"], width=dash_w)

    # Numbered markers 13–20 with crisp leader lines
    badge_sz = int(round(19 * scale))
    dot_r = max(3, int(round(2.6 * scale)))
    leader_w = max(2, int(round(1.2 * scale)))

    for st in list_stories:
        num = st["num"]
        reg = st["region"]
        col = REGION_COLORS[reg]
        gx, gy = proj(st["lon"], st["lat"])
        ox, oy = MAP_CALLOUT_OFFSETS[num]
        bx = gx + ox * scale
        by = gy + oy * scale
        half = badge_sz / 2.0
        pad = int(round(6 * scale))
        bx = max(mx0 + half + pad, min(mx1 - half - pad, bx))
        by = max(my0 + half + pad, min(my1 - half - pad, by))

        draw.line([(gx, gy), (bx, by)], fill=INK_BLACK, width=leader_w)
        draw.ellipse(
            [gx - dot_r, gy - dot_r, gx + dot_r, gy + dot_r],
            fill=col,
            outline=WHITE,
            width=max(1, int(round(0.8 * scale))),
        )

        b_rect = (int(round(bx - half)), int(round(by - half)), int(round(bx + half)), int(round(by + half)))
        draw.rectangle(b_rect, fill=col, outline=WHITE, width=max(2, int(round(1.2 * scale))))
        nf = get_font(FONT_SANS_BOLD, int(round(10.5 * scale)))
        draw.text((bx, by), str(num), font=nf, fill=WHITE, anchor="mm")
        boxes.append((f"map_pin_{num}", b_rect))

    # Evenly justified 7-region color legend spanning flush-left to flush-right across mw
    leg_band_y0 = my1 + int(round(5 * scale))
    leg_band_h = y1 - leg_band_y0 - int(round(4 * scale))
    sw = int(round(7.5 * scale))
    sw_gap = int(round(2.8 * scale))

    leg_items = []
    total_items_w = 0.0
    for reg in REGION_ORDER:
        lbl = reg if reg != "MID EAST" else "M.EAST"
        lf, l_lines, lw_txt, lh_txt, l_sz = fit(
            lbl, FONT_SANS_CN_BOLD, int(round(8.4 * scale)), mw / 6.5, 1, min_size=int(round(8 * scale))
        )
        item_w = sw + sw_gap + lw_txt
        leg_items.append((reg, lf, l_lines, lw_txt, lh_txt, l_sz, item_w))
        total_items_w += item_w

    gap_between = (mw - total_items_w) / (len(leg_items) - 1)
    cur_lx = float(mx0)
    for reg, lf, l_lines, lw_txt, lh_txt, l_sz, item_w in leg_items:
        sw_y = leg_band_y0 + (leg_band_h - sw) / 2.0
        draw.rectangle([cur_lx, sw_y, cur_lx + sw, sw_y + sw], fill=REGION_COLORS[reg])
        txt_y = leg_band_y0 + (leg_band_h - lh_txt) / 2.0
        l_bb = draw_fitted_lines(draw, l_lines, lf, cur_lx + sw + sw_gap, txt_y, INK_DARK, size=l_sz)
        boxes.append((f"map_legend_{reg}", l_bb))
        cur_lx += item_w + gap_between


# ---------------------------------------------------------------------------
# Main Renderer
# ---------------------------------------------------------------------------
def render_infographic(canvas_size: int = 4000) -> Tuple[Image.Image, Dict[str, int], int, int]:
    """
    Render the entire card-grid infographic at canvas_size x canvas_size.
    Strictly scales all SPEC logical px by scale = canvas_size / 1000.0 (4.0 at 4000x4000).
    Returns: (image, region_counts, num_boxes, num_checked_pairs).
    """
    S = canvas_size / 1000.0
    W = H = canvas_size
    min_fit_px = int(round(8 * S))  # 32px at 4000x4000

    # --- Dynamic data validation & region counting (NO hardcoding) ---
    assert len(STORIES) == 20, f"Expected 20 stories, got {len(STORIES)}"
    cards_data = STORIES[:12]
    list_data = STORIES[12:]
    assert len(cards_data) == 12 and len(list_data) == 8

    region_counts: Dict[str, int] = dict(Counter(st["region"] for st in STORIES))
    assert set(region_counts.keys()) == set(REGION_ORDER), f"Region mismatch: {region_counts}"
    assert sum(region_counts.values()) == len(STORIES)

    img = Image.new("RGB", (W, H), BG_PAPER)
    draw = ImageDraw.Draw(img)
    boxes: List[Tuple[str, Tuple[float, float, float, float]]] = []

    def sc(v: float) -> int:
        return int(round(v * S))

    M = sc(18)           # 72px page side margin
    CX0 = M
    CX1 = W - M
    CW = CX1 - CX0       # 3856px content width

    # =========================================================================
    # 1. TOP BAR (y = 0..26 logical -> 0..104px)
    # =========================================================================
    top_h = sc(26)
    draw.rectangle([0, 0, W, top_h], fill=BG_DARK)

    f_tl, ln_tl, w_tl, h_tl, sz_tl = fit(
        TOP_LEFT, FONT_SANS_BOLD, sc(11), CW * 0.34, 1, min_size=min_fit_px
    )
    bb_tl = draw_fitted_lines(draw, ln_tl, f_tl, CX0, (top_h - h_tl) / 2.0, CREAM_TEXT, size=sz_tl)
    boxes.append(("top_left", bb_tl))

    f_tr, ln_tr, w_tr, h_tr, sz_tr = fit(
        TOP_RIGHT, FONT_SANS_BOLD, sc(11), CW * 0.64, 1, min_size=min_fit_px
    )
    bb_tr = draw_fitted_lines(
        draw, ln_tr, f_tr, CX1 - w_tr, (top_h - h_tr) / 2.0, (218, 212, 200), size=sz_tr
    )
    boxes.append(("top_right", bb_tr))

    # =========================================================================
    # 2. GIANT DATE (y = 30..136 logical -> 120..544px) + DOUBLE-COLOR RULE
    # =========================================================================
    date_max_w = W - sc(24)  # 3904px so 344px bold serif fills the row cleanly
    f_date, ln_date, w_date, h_date, sz_date = fit(
        DATE_STR, FONT_SERIF_BOLD, sc(86), date_max_w, 1, min_size=min_fit_px
    )
    date_y0 = sc(30)
    date_band_h = sc(106)
    bb_date = draw_fitted_lines(
        draw, ln_date, f_date, sc(12), date_y0 + (date_band_h - h_date) / 2.0,
        INK_BLACK, align="center", box_w=date_max_w, size=sz_date,
    )
    boxes.append(("giant_date", bb_date))

    # Double-color rule: Black 3px (*4=12px) + gap + Red 1px (*4=4px)
    rule_y = sc(140)
    draw.rectangle([CX0, rule_y, CX1, rule_y + sc(3)], fill=INK_BLACK)
    draw.rectangle([CX0, rule_y + sc(4.5), CX1, rule_y + sc(5.5)], fill=ACCENT_RED)

    # =========================================================================
    # 3. SINGLE-LINE SUMMARY (Red Italic 15px*4 = 60px, y = 152..182)
    # =========================================================================
    f_sum, ln_sum, w_sum, h_sum, sz_sum = fit(
        SUMMARY_STR, FONT_SERIF_BOLDITAL, sc(15), CW, 1, min_size=min_fit_px
    )
    bb_sum = draw_fitted_lines(
        draw, ln_sum, f_sum, CX0, sc(153) + (sc(28) - h_sum) / 2.0,
        ACCENT_RED, align="center", box_w=CW, size=sz_sum,
    )
    boxes.append(("summary_line", bb_sum))

    # =========================================================================
    # 4. 6-CELL SCOREBOARD (y = 188..244 logical -> 752..976px)
    # =========================================================================
    sb_y0, sb_y1 = sc(188), sc(244)
    sb_h = sb_y1 - sb_y0
    draw.rectangle([CX0, sb_y0, CX1, sb_y1], fill=BG_SCORE, outline=RULE_LIGHT, width=sc(1))
    cell_w = CW / len(SCOREBOARD)

    # Compute shared cap-height reference so comma descender in "74,742" never shifts its baseline!
    ref_num_f = get_font(FONT_SANS_BOLD, sc(30))
    _, ref_num_h = _measure_line(ref_num_f, "0123456789")
    ref_lbl_f = get_font(FONT_SANS_CN_BOLD, sc(10))
    _, ref_lbl_h = _measure_line(ref_lbl_f, "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    pair_gap = sc(8.0)
    shared_num_y = sb_y0 + sc(2.5) + ((sb_h - sc(2.5)) - (ref_num_h + pair_gap + ref_lbl_h)) / 2.0
    shared_lbl_y = shared_num_y + ref_num_h + pair_gap

    for idx, (val, lbl, reg) in enumerate(SCOREBOARD):
        sx0 = CX0 + idx * cell_w
        sx1 = sx0 + cell_w
        draw.rectangle([sx0 + sc(1), sb_y0, sx1 - sc(1), sb_y0 + sc(2.2)], fill=REGION_COLORS[reg])
        if idx > 0:
            draw.line([(sx0, sb_y0 + sc(6)), (sx0, sb_y1 - sc(6))], fill=RULE_LIGHT, width=sc(1))

        # Big number (30px*4 = 120px) aligned on a laser-straight shared baseline across all 6 cells
        f_num, ln_num, _, _, sz_num = fit(
            val, FONT_SANS_BOLD, sc(30), cell_w - sc(10), 1, min_size=min_fit_px
        )
        # Small uppercase label (10px*4 = 40px for crisp 300px scannability)
        f_lbl, ln_lbl, _, _, sz_lbl = fit(
            lbl, FONT_SANS_CN_BOLD, sc(10), cell_w - sc(8), 1, min_size=min_fit_px
        )

        bb_num = draw_fitted_lines(
            draw, ln_num, f_num, sx0 + sc(5), shared_num_y, INK_BLACK,
            align="center", box_w=cell_w - sc(10), size=sz_num,
        )
        boxes.append((f"score_num_{idx}", bb_num))

        bb_lbl = draw_fitted_lines(
            draw, ln_lbl, f_lbl, sx0 + sc(4), shared_lbl_y, INK_DARK,
            align="center", box_w=cell_w - sc(8), size=sz_lbl,
        )
        boxes.append((f"score_lbl_{idx}", bb_lbl))

    # =========================================================================
    # 5. 7-COLOR REGION BAR (y = 250..274 logical -> 1000..1096px)
    #    Counts computed dynamically from STORIES!
    # =========================================================================
    rb_y0, rb_y1 = sc(250), sc(274)
    rb_h = rb_y1 - rb_y0

    base_min_w = sc(96)
    rem_w = CW - base_min_w * len(REGION_ORDER)
    total_stories = sum(region_counts[r] for r in REGION_ORDER)

    cur_rx = float(CX0)
    for idx, reg in enumerate(REGION_ORDER):
        cnt = region_counts[reg]
        if idx == len(REGION_ORDER) - 1:
            seg_w = CX1 - cur_rx
        else:
            seg_w = base_min_w + rem_w * (cnt / total_stories)

        rx0 = int(round(cur_rx))
        rx1 = int(round(cur_rx + seg_w))
        draw.rectangle([rx0, rb_y0, rx1, rb_y1], fill=REGION_COLORS[reg])
        if idx > 0:
            draw.line([(rx0, rb_y0), (rx0, rb_y1)], fill=WHITE, width=sc(1.5))

        reg_text = f"{REGION_DISPLAY[reg]} {cnt}"
        f_reg, ln_reg, _, h_reg, sz_reg = fit(
            reg_text, FONT_SANS_CN_BOLD, sc(10), (rx1 - rx0) - sc(8), 1, min_size=min_fit_px
        )
        bb_reg = draw_fitted_lines(
            draw, ln_reg, f_reg, rx0 + sc(4), rb_y0 + (rb_h - h_reg) / 2.0, WHITE,
            align="center", box_w=(rx1 - rx0) - sc(8), size=sz_reg,
        )
        boxes.append((f"region_bar_{reg}", bb_reg))
        cur_rx += seg_w

    # =========================================================================
    # 6. 12 NUMBERED CARDS (3 cols x 4 rows, y = 282..714 logical -> 1128..2856px)
    #    Pre-fit uniform headline & deck font sizes across all 12 cards for rock-solid grid rhythm!
    # =========================================================================
    card_cols = 3
    card_gap = sc(8)
    card_w = sc(316)  # 3*316 + 2*8 = 964 == CW
    card_h = sc(102)  # 4*102 + 3*8 = 432 logical (282..714)
    grid_y0 = sc(282)

    num_sz = sc(32)
    ill_w = sc(64)
    top_text_w = card_w - sc(4.5) - num_sz - sc(4.5) - sc(4.5) - ill_w - sc(4.5)
    full_text_w = card_w - sc(4.5) - sc(4.5) - ill_w - sc(4.5)

    hl_step_ratio = 1.07
    deck_step_ratio = 1.15
    hl_max_h = sc(36)    # 144px at 4x -> fits 2 tight lines at up to 68px cleanly!
    deck_max_h = sc(25)  # 100px at 4x -> fits 2 tight lines at up to 44px cleanly!

    # Compute uniform headline size and uniform deck size via fit() over all 12 cards
    uniform_hl_sz = min(
        fit(
            st["title"], FONT_SERIF_BOLD, sc(17), top_text_w, 2,
            min_size=min_fit_px, max_h=hl_max_h, line_step_ratio=hl_step_ratio, balance=True,
        )[4]
        for st in cards_data
    )
    uniform_deck_sz = min(
        fit(
            st["deck"], FONT_SANS_REG, sc(11), full_text_w, 2,
            min_size=min_fit_px, max_h=deck_max_h, line_step_ratio=deck_step_ratio, balance=False,
        )[4]
        for st in cards_data
    )

    for idx, st in enumerate(cards_data):
        row = idx // card_cols
        col = idx % card_cols
        cx0 = CX0 + col * (card_w + card_gap)
        cy0 = grid_y0 + row * (card_h + card_gap)
        cx1 = cx0 + card_w
        cy1 = cy0 + card_h

        reg = st["region"]
        reg_col = REGION_COLORS[reg]
        num = st["num"]

        # Card surface + border + top region color bar
        draw.rectangle([cx0, cy0, cx1, cy1], fill=BG_CARD, outline=RULE_LIGHT, width=sc(1))
        draw.rectangle([cx0, cy0, cx1, cy0 + sc(2.5)], fill=reg_col)

        # (A) Left Number Square: 32x32 logical -> 128x128px (height tuned cleanly to match kicker+2-line title!)
        nx0, ny0 = cx0 + sc(4.5), cy0 + sc(5.5)
        nx1, ny1 = nx0 + num_sz, ny0 + sc(35)  # 32x35 logical aligns flush with kicker + 2-line title bottom
        draw.rectangle([nx0, ny0, nx1, ny1], fill=reg_col)
        f_cn = get_font(FONT_SANS_BOLD, sc(18))
        draw.text(((nx0 + nx1) / 2.0, (ny0 + ny1) / 2.0), str(num), font=f_cn, fill=WHITE, anchor="mm")
        boxes.append((f"card_{num}_numbox", (nx0, ny0, nx1, ny1)))

        # (B) Right Vertical Line-Art Illustration Strip: 64x91 logical -> 256x364px
        ix1 = cx1 - sc(4.5)
        ix0 = ix1 - ill_w
        iy0 = cy0 + sc(5.5)
        iy1 = cy1 - sc(5.0)
        draw_card_illustration(draw, num, (ix0, iy0, ix1, iy1), reg_col, S)
        boxes.append((f"card_{num}_illus", (ix0, iy0, ix1, iy1)))

        tx_top_l = nx1 + sc(4.5)
        tx_full_l = nx0
        tx_r = ix0 - sc(4.5)

        # (C) Region + Topic small tag (8px*4 = 32px uppercase)
        kicker_str = f"{reg} · {st['topic']}"
        f_k, ln_k, _, h_k, sz_k = fit(
            kicker_str, FONT_SANS_BOLD, sc(8), top_text_w, 1, min_size=min_fit_px
        )
        bb_k = draw_fitted_lines(draw, ln_k, f_k, tx_top_l, ny0, reg_col, size=sz_k)
        boxes.append((f"card_{num}_kicker", bb_k))

        # (D) Uniform Bold Serif Headline (balanced 2-line wrap, tight leading)
        f_hl, ln_hl, _, h_hl, sz_hl = fit(
            st["title"], FONT_SERIF_BOLD, uniform_hl_sz, top_text_w, 2,
            min_size=min_fit_px, max_h=hl_max_h, line_step_ratio=hl_step_ratio, balance=True,
        )
        hl_y = bb_k[3] + sc(2.8)
        bb_hl = draw_fitted_lines(
            draw, ln_hl, f_hl, tx_top_l, hl_y, INK_BLACK,
            line_step_ratio=hl_step_ratio, size=sz_hl,
        )
        boxes.append((f"card_{num}_title", bb_hl))

        # (E) Uniform Lead / Deck — fixed consistent vertical zone cleanly below both square & headline
        status_pill_h = sc(12.5)
        py1_s = cy1 - sc(5.0)
        py0_s = py1_s - status_pill_h

        deck_zone_top = max(ny1, bb_hl[3]) + sc(4.2)
        deck_zone_bot = py0_s - sc(3.5)
        f_dk, ln_dk, _, h_dk, sz_dk = fit(
            st["deck"], FONT_SANS_REG, uniform_deck_sz, full_text_w, 2,
            min_size=min_fit_px, max_h=deck_zone_bot - deck_zone_top, line_step_ratio=deck_step_ratio,
        )
        # Vertically center deck slightly in its clean band so 1-line and 2-line headlines look equally poised
        deck_y = deck_zone_top + max(0.0, (deck_zone_bot - deck_zone_top - h_dk) * 0.35)
        bb_dk = draw_fitted_lines(
            draw, ln_dk, f_dk, tx_full_l, deck_y, INK_DARK,
            line_step_ratio=deck_step_ratio, size=sz_dk,
        )
        boxes.append((f"card_{num}_deck", bb_dk))

        # (F) Status Badge (8px*4 = 32px white on Green/Amber/Red) aligned bottom-right
        status = st["status"]
        st_col = STATUS_COLORS[status]
        f_st = get_font(FONT_SANS_BOLD, sc(8))
        sw_txt, _ = _measure_line(f_st, status)
        pill_w = sw_txt + sc(8.0)
        px1_s = tx_r
        px0_s = px1_s - pill_w
        draw.rectangle([px0_s, py0_s, px1_s, py1_s], fill=st_col)
        draw.text(((px0_s + px1_s) / 2.0, (py0_s + py1_s) / 2.0), status, font=f_st, fill=WHITE, anchor="mm")
        boxes.append((f"card_{num}_status", (px0_s, py0_s, px1_s, py1_s)))

        # (G) Source (9px*4 = 36px italic) aligned bottom-left
        src_max_w = (px0_s - sc(3.5)) - tx_full_l
        f_sr, ln_sr, _, h_sr, sz_sr = fit(
            st["source"], FONT_SERIF_ITAL, sc(9), src_max_w, 1, min_size=min_fit_px
        )
        src_y = py0_s + (status_pill_h - h_sr) / 2.0
        bb_sr = draw_fitted_lines(draw, ln_sr, f_sr, tx_full_l, src_y, INK_MUTED, size=sz_sr)
        boxes.append((f"card_{num}_source", bb_sr))

    # =========================================================================
    # 7. BOTTOM HALF (y = 722..966 logical -> 2888..3864px)
    #    Left: World Map (~456 logical = 1824px) | Right: List 13–20 (~498 logical = 1992px)
    # =========================================================================
    bot_y0 = sc(722)
    bot_y1 = sc(966)
    map_w = sc(456)
    mid_gap = sc(10)
    map_box = (CX0, bot_y0, CX0 + map_w, bot_y1)
    list_box = (CX0 + map_w + mid_gap, bot_y0, CX1, bot_y1)

    draw_world_map(draw, map_box, list_data, S, boxes)

    # Right Panel: Numbered List 13–20
    lx0, ly0, lx1, ly1 = list_box
    lw_panel = lx1 - lx0
    draw.rectangle(list_box, fill=BG_CARD, outline=RULE_LIGHT, width=sc(1))
    draw.rectangle([lx0, ly0, lx1, ly0 + sc(2.5)], fill=INK_BLACK)

    l_pad = sc(8)
    lh_f, lh_lines, _, _, lh_sz = fit(
        "GLOBAL BRIEFINGS · STORIES 13–20", FONT_SANS_BOLD, sc(9.5), lw_panel * 0.72, 1, min_size=min_fit_px
    )
    bb_lh = draw_fitted_lines(draw, lh_lines, lh_f, lx0 + l_pad, ly0 + sc(6.5), INK_BLACK, size=lh_sz)
    boxes.append(("list_header", bb_lh))

    ls_f, ls_lines, ls_w, _, ls_sz = fit(
        "8 BRIEFINGS", FONT_SANS_BOLD, sc(8.5), lw_panel * 0.28, 1, min_size=min_fit_px
    )
    bb_ls = draw_fitted_lines(draw, ls_lines, ls_f, lx1 - l_pad - ls_w, ly0 + sc(7.0), INK_MUTED, size=ls_sz)
    boxes.append(("list_subhdr", bb_ls))

    list_top = int(bb_lh[3] + sc(5))
    list_bot = ly1 - sc(3)
    row_h = (list_bot - list_top) / len(list_data)

    for idx, st in enumerate(list_data):
        ry0 = list_top + idx * row_h
        ry1 = ry0 + row_h
        num = st["num"]
        reg = st["region"]
        reg_col = REGION_COLORS[reg]
        status = st["status"]
        st_col = STATUS_COLORS[status]

        # Row separator hairline (top of rows 1..7)
        if idx > 0:
            draw.line([(lx0 + l_pad, ry0), (lx1 - l_pad, ry0)], fill=RULE_LIGHT, width=sc(0.8))

        # Number badge (20x20 logical -> 80x80px, centered cleanly inside row)
        nb_sz = sc(20)
        nb_x0 = lx0 + l_pad
        nb_y0 = ry0 + (row_h - nb_sz) / 2.0
        nb_rect = (int(round(nb_x0)), int(round(nb_y0)), int(round(nb_x0 + nb_sz)), int(round(nb_y0 + nb_sz)))
        draw.rectangle(nb_rect, fill=reg_col)
        f_ln = get_font(FONT_SANS_BOLD, sc(11.5))
        draw.text(((nb_rect[0] + nb_rect[2]) / 2.0, (nb_rect[1] + nb_rect[3]) / 2.0), str(num), font=f_ln, fill=WHITE, anchor="mm")
        boxes.append((f"list_{num}_numbox", nb_rect))

        # Status badge on far right, centered cleanly inside row
        f_lst = get_font(FONT_SANS_BOLD, sc(8))
        stw, _ = _measure_line(f_lst, status)
        sp_w = stw + sc(7.5)
        sp_h = sc(12.5)
        sp_x1 = lx1 - l_pad
        sp_x0 = sp_x1 - sp_w
        sp_y0 = ry0 + (row_h - sp_h) / 2.0
        sp_rect = (int(round(sp_x0)), int(round(sp_y0)), int(round(sp_x1)), int(round(sp_y0 + sp_h)))
        draw.rectangle(sp_rect, fill=st_col)
        draw.text(((sp_rect[0] + sp_rect[2]) / 2.0, (sp_rect[1] + sp_rect[3]) / 2.0), status, font=f_lst, fill=WHITE, anchor="mm")
        boxes.append((f"list_{num}_status", sp_rect))

        # Middle text block: CITY — Title (12px*4=48px bold) + REGION · Source (9px*4=36px italic)
        # Vertically centered as a tight pair inside [ry0, ry1] so dividers NEVER touch text!
        mid_x0 = nb_rect[2] + sc(5.5)
        mid_x1 = sp_rect[0] - sc(5.5)
        mid_w = mid_x1 - mid_x0

        headline_str = f"{st['city']} — {st['title']}"
        f_lt, ln_lt, _, h_lt, sz_lt = fit(
            headline_str, FONT_SERIF_BOLD, sc(12), mid_w, 1, min_size=min_fit_px
        )
        meta_str = f"{reg}  ·  {st['source']}"
        f_lm, ln_lm, _, h_lm, sz_lm = fit(
            meta_str, FONT_SERIF_ITAL, sc(9), mid_w, 1, min_size=min_fit_px
        )

        row_txt_gap = sc(3.2)
        pair_h = h_lt + row_txt_gap + h_lm
        pair_top = ry0 + (row_h - pair_h) / 2.0

        bb_lt = draw_fitted_lines(draw, ln_lt, f_lt, mid_x0, pair_top, INK_BLACK, size=sz_lt)
        bb_lm = draw_fitted_lines(draw, ln_lm, f_lm, mid_x0, pair_top + h_lt + row_txt_gap, INK_MUTED, size=sz_lm)

        # Strict row-divider clearance assertion (guarantees >= 6px margin from top & bottom dividers)
        pad_clear = sc(1.5)
        if bb_lt[1] < ry0 + pad_clear or bb_lm[3] > ry1 - pad_clear:
            raise RuntimeError(
                f"List row {num} text too close to divider: [{bb_lt[1]:.1f}..{bb_lm[3]:.1f}] vs row [{ry0:.1f}..{ry1:.1f}]"
            )

        boxes.append((f"list_{num}_title", bb_lt))
        boxes.append((f"list_{num}_source", bb_lm))

    # =========================================================================
    # 8. BOTTOM DATE CHECK BAR (y = 973..1000 logical -> 3892..4000px)
    # =========================================================================
    dc_y0 = sc(973)
    dc_h = H - dc_y0
    draw.rectangle([0, dc_y0, W, H], fill=BG_DARK)
    draw.rectangle([0, dc_y0, W, dc_y0 + sc(1.5)], fill=ACCENT_RED)

    f_dc, ln_dc, _, h_dc, sz_dc = fit(
        DATE_CHECK_TEXT, FONT_SANS_BOLD, sc(9), CW, 1,
        min_size=min_fit_px, max_h=dc_h - sc(6),
    )
    dc_ty = dc_y0 + sc(1.5) + (dc_h - sc(1.5) - h_dc) / 2.0
    bb_dc = draw_fitted_lines(
        draw, ln_dc, f_dc, CX0, dc_ty, CREAM_TEXT,
        align="center", box_w=CW, size=sz_dc,
    )
    boxes.append(("date_check", bb_dc))

    # =========================================================================
    # HARD COLLISION CHECK (raises RuntimeError if ANY pair intersects)
    # =========================================================================
    checked_pairs = no_overlap(boxes, W, H)
    return img, region_counts, len(boxes), checked_pairs


def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    max_bytes = 8 * 1024 * 1024  # 8 MiB hard cap
    max_pixels = 16_000_000      # 16M pixel hard cap

    final_size = None
    final_counts = None
    final_boxes = 0
    final_pairs = 0
    final_bytes = 0
    final_img = None

    for candidate in (4000, 3600, 3200):
        assert candidate * candidate <= max_pixels
        img, counts, n_boxes, n_pairs = render_infographic(candidate)
        img.save(ENTRY_PNG, format="PNG", optimize=True, compress_level=9)
        byte_size = ENTRY_PNG.stat().st_size
        if byte_size <= max_bytes:
            final_size = candidate
            final_counts = counts
            final_boxes = n_boxes
            final_pairs = n_pairs
            final_bytes = byte_size
            final_img = img
            break
        print(f"[WARN] {candidate}x{candidate} PNG is {byte_size:,} bytes (> 8MB), downshifting...")

    if final_img is None or final_size is None:
        raise RuntimeError("Failed to produce entry.png under 8MB limit.")

    preview = final_img.resize((300, 300), Image.Resampling.LANCZOS)
    preview.save(PREVIEW_PNG, format="PNG", optimize=True, compress_level=9)

    md5_entry = file_md5(ENTRY_PNG)
    md5_prev = file_md5(PREVIEW_PNG)

    print("=== BUILD SUMMARY ===")
    print(f"Stories total   : {len(STORIES)} (12 cards + 8 list items)")
    print("Region counts   : " + " · ".join(f"{r} {final_counts[r]}" for r in REGION_ORDER))
    print(f"Main resolution : {final_size}x{final_size} ({final_size * final_size:,} px)")
    print(f"entry.png size  : {final_bytes:,} bytes ({final_bytes / (1024 * 1024):.2f} MiB)")
    print(f"entry.png md5   : {md5_entry}")
    print(f"preview-300 md5 : {md5_prev} ({PREVIEW_PNG.stat().st_size:,} bytes)")
    print(f"Collision check : PASS (0 overlaps across {final_boxes} blocks / {final_pairs:,} pairs)")


if __name__ == "__main__":
    main()

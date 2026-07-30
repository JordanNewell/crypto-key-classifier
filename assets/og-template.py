"""NEWELL OG image generator for crypto-key-classifier.

Renders a 1200x630 Open Graph preview PNG on the NEWELL brand system.
Colors and spacing are hardcoded from tokens.json (canonical at
e:/vaults/anything.xyz/50_Projects/brand-system/tokens.json) so this
file is self-contained and re-runnable without the vault mounted.

Usage:
    py assets/og-template.py

Output:
    assets/og.png   (1200x630, PNG)

To regenerate for a different product surface, edit the CONTENT block
below — nothing else needs to change.
"""

from __future__ import annotations

import io
import sys
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

from PIL import Image, ImageDraw, ImageFont

# --------------------------------------------------------------------------- #
# CONTENT — edit this block to retarget the OG image.                          #
# --------------------------------------------------------------------------- #

TITLE = "crypto-key-classifier"
SUBHEAD = "BTC / ETH / SOL / Cosmos + ~50 chains — classify any key client-side."
FOOTER = "github.com/JordanNewell/crypto-key-classifier"
TAG = "[live demo]"  # small inline accent next to headline; set to "" to omit

OUTPUT_PATH = Path(__file__).resolve().parent / "og.png"

# --------------------------------------------------------------------------- #
# BRAND TOKENS — sourced from tokens.json (NEWELL Brand System v1.0.0).        #
# Hardcoded so this script runs without the vault mounted. If tokens change,   #
# update both this file AND e:/vaults/anything.xyz/50_Projects/brand-system/   #
# tokens.json — they must stay in sync.                                       #
# --------------------------------------------------------------------------- #

PRIMARY_HEX = "#00FF41"   # primary green
ACCENT_HEX = "#1AFF72"    # accent lift (unused here, kept for reference)
BG_HEX = "#0A0A0A"        # soft black background
SURFACE_HEX = "#0F0F0F"   # card surface
BORDER_HEX = "#1F1F1F"    # hairline borders
TEXT_HEX = "#FFFFFF"      # primary text
MUTED_HEX = "#A0A0A0"     # secondary text

CANVAS_W = 1200
CANVAS_H = 630

# --------------------------------------------------------------------------- #
# FONTS — installed system-wide via Windows Settings.                          #
# Confirmed present in %LOCALAPPDATA%/Microsoft/Windows/Fonts/.                #
# --------------------------------------------------------------------------- #

FONT_DIR = Path.home() / "AppData/Local/Microsoft/Windows/Fonts"
# NOTE on Space Grotesk: the static-weight TTFs in FONT_DIR are corrupt
# (their bytes spell an HTML 404 page — likely a botched manual download).
# Only SpaceGrotesk-variable.ttf is a real font. We instantiate specific
# weights from it via fonttools at runtime, which also keeps the brand
# script resilient on machines that only have the variable font installed.
SPACE_GROTESK_VAR = FONT_DIR / "SpaceGrotesk-variable.ttf"
SPACE_GROTESK_WEIGHT_AXIS = "wght"  # axis tag
SPACE_GROTESK_WEIGHTS = {
    "Medium":   500,
    "SemiBold": 600,
    "Bold":     700,
}
JETBRAINS = {
    "Regular": FONT_DIR / "JetBrainsMono-Regular.ttf",
    "Medium":  FONT_DIR / "JetBrainsMono-Medium.ttf",
    "Bold":    FONT_DIR / "JetBrainsMono-Bold.ttf",
}


class RGB(NamedTuple):
    r: int
    g: int
    b: int


def _hex(s: str) -> RGB:
    s = s.lstrip("#")
    return RGB(int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def _rgb_tuple(c: RGB) -> tuple[int, int, int]:
    return (c.r, c.g, c.b)


def grid(n) -> int:
    """8px spacing grid: grid(1)=8, grid(2)=16, grid(0.5)=4."""
    return int(n * 8)


def _load(path: Path, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(path), size)
    except (FileNotFoundError, OSError) as exc:
        # Last-resort fallback so script still produces output if a font
        # is missing — typography will be off but the PNG renders.
        print(f"WARN: font {path} not found ({exc}); falling back to PIL default.", file=sys.stderr)
        return ImageFont.load_default()


@lru_cache(maxsize=8)
def _instantiate_space_grotesk(weight_label: str) -> bytes:
    """Instantiate a static TTF blob from the Space Grotesk variable font.

    Caches per weight so repeated draws reuse the same bytes.
    """
    try:
        from fontTools import varLib  # noqa: F401
        from fontTools.ttLib import TTFont
    except ImportError as exc:
        raise RuntimeError(
            "fonttools is required to instantiate Space Grotesk weights. "
            "Install with: py -m pip install fonttools"
        ) from exc

    if weight_label not in SPACE_GROTESK_WEIGHTS:
        raise ValueError(f"Unknown Space Grotesk weight: {weight_label!r}")
    wght = SPACE_GROTESK_WEIGHTS[weight_label]

    tt = TTFont(str(SPACE_GROTESK_VAR))
    # Set the weight on every instance-record-bearing table.
    if "fvar" in tt:
        for axis in tt["fvar"].axes:
            if axis.axisTag == SPACE_GROTESK_WEIGHT_AXIS:
                # Pin the default to the requested weight so static
                # instantiation picks it up.
                axis.defaultValue = wght
                break
    # Instantiate at the pinned weight.
    from fontTools.varLib.instancer import instantiateVariableFont
    static = instantiateVariableFont(
        tt,
        {SPACE_GROTESK_WEIGHT_AXIS: wght},
        inplace=True,
    )
    buf = io.BytesIO()
    static.save(buf)
    buf.seek(0)
    return buf.getvalue()


def _space_grotesk(weight: str, size: int) -> ImageFont.FreeTypeFont:
    """Load Space Grotesk at a specific weight + size from the variable font."""
    try:
        blob = _instantiate_space_grotesk(weight)
        return ImageFont.truetype(io.BytesIO(blob), size)
    except Exception as exc:
        print(
            f"WARN: could not instantiate Space Grotesk {weight} ({exc}); "
            f"falling back to PIL default.",
            file=sys.stderr,
        )
        return ImageFont.load_default()


def _jetbrains(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return _load(JETBRAINS[weight], size)


# --------------------------------------------------------------------------- #
# Drawing primitives.                                                          #
# --------------------------------------------------------------------------- #

def _draw_n_logo(draw: ImageDraw.ImageDraw, origin_x: int, origin_y: int, size: int) -> None:
    """NEWELL N mark — three monoline bars, rounded caps.

    Constructed canonically: left vertical, right vertical, diagonal.
    The diagonal is rendered in PRIMARY green (matches favicon variant
    in docs/demo/index.html); the verticals are white.

    size = total bounding box (logo is roughly square but slightly taller
    than wide; we render into a size x size*1.2 box).
    """
    stroke = max(8, size // 8)  # scale stroke with logo size
    # Map a 0..100 x 0..120 viewBox into the target box.
    w = size
    h = int(size * 1.2)
    # endpoints in viewBox coords (matching index.html favicon):
    #   left vertical:  (20,20)-(20,100)
    #   right vertical: (80,20)-(80,100)
    #   diagonal:       (20,20)-(80,100)
    def map_pt(vx: int, vy: int) -> tuple[int, int]:
        return (origin_x + vx * w // 100, origin_y + vy * h // 120)

    white = _rgb_tuple(_hex(TEXT_HEX))
    green = _rgb_tuple(_hex(PRIMARY_HEX))

    # PIL's draw.line with width renders butt caps by default; for round
    # caps we overlay filled circles at each endpoint.
    def line(p1, p2, color):
        draw.line([p1, p2], fill=color, width=stroke)

    def cap(p, color):
        r = stroke // 2
        draw.ellipse([p[0]-r, p[1]-r, p[0]+r, p[1]+r], fill=color)

    left_top = map_pt(20, 20)
    left_bot = map_pt(20, 100)
    right_top = map_pt(80, 20)
    right_bot = map_pt(80, 100)

    # Verticals first (white), then diagonal (green) on top so the joins
    # at (20,20) and (80,100) layer correctly.
    line(left_top, left_bot, white)
    line(right_top, right_bot, white)
    line(left_top, right_bot, green)

    # Round caps on all four endpoints. Diagonal endpoints get green caps
    # to dominate the visual; vertical-only endpoints (bottom-left, top-right)
    # stay white.
    cap(left_top, green)      # diagonal start
    cap(right_bot, green)     # diagonal end
    cap(left_bot, white)
    cap(right_top, white)


def _draw_hairline_border(draw: ImageDraw.ImageDraw) -> None:
    """Architectural 1px border inset 16px from the canvas edge."""
    inset = grid(2)
    draw.rectangle(
        [inset, inset, CANVAS_W - inset, CANVAS_H - inset],
        outline=_rgb_tuple(_hex(BORDER_HEX)),
        width=1,
    )


def _draw_accent_rule(draw: ImageDraw.ImageDraw, x: int, y: int, width: int) -> None:
    """2px primary-green horizontal rule — anchors title block."""
    draw.rectangle([x, y, x + width, y + 2], fill=_rgb_tuple(_hex(PRIMARY_HEX)))


def _draw_receipt_chip(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont,
) -> int:
    """JetBrains Mono receipt chip. Returns the chip's right edge x."""
    pad_x = grid(2)  # 16
    pad_y = grid(1)  # 8
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    box_w = tw + pad_x * 2
    box_h = th + pad_y
    draw.rounded_rectangle(
        [x, y, x + box_w, y + box_h],
        radius=4,
        fill=_rgb_tuple(_hex(SURFACE_HEX)),
        outline=_rgb_tuple(_hex(BORDER_HEX)),
        width=1,
    )
    draw.text(
        (x + pad_x - bbox[0], y + pad_y - bbox[1]),
        text,
        font=font,
        fill=_rgb_tuple(_hex(MUTED_HEX)),
    )
    return x + box_w


# --------------------------------------------------------------------------- #
# Main composition.                                                            #
# --------------------------------------------------------------------------- #

def render() -> Path:
    bg = _rgb_tuple(_hex(BG_HEX))
    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), bg)
    draw = ImageDraw.Draw(canvas)

    _draw_hairline_border(draw)

    margin_x = grid(8)  # 64px outer content gutter

    # --- Top-left: NEWELL N logo -----------------------------------------
    logo_size = 56  # nominal; actual render box is 56 x 67
    logo_top = grid(6)  # 48px from top (inside the 16px border)
    _draw_n_logo(draw, margin_x, logo_top, logo_size)

    # NEWELL wordmark next to the logo
    wordmark_font = _space_grotesk("Bold", 22)
    wordmark_text = "NEWELL"
    wordmark_x = margin_x + logo_size + grid(2)  # 16px gap
    # vertically center against the logo box (logo is ~67px tall)
    logo_h = int(logo_size * 1.2)
    wm_bbox = draw.textbbox((0, 0), wordmark_text, font=wordmark_font)
    wm_y = logo_top + (logo_h - (wm_bbox[3] - wm_bbox[1])) // 2 - wm_bbox[1]
    draw.text(
        (wordmark_x - wm_bbox[0], wm_y),
        wordmark_text,
        font=wordmark_font,
        fill=_rgb_tuple(_hex(TEXT_HEX)),
    )

    # --- Receipt chip top-right ------------------------------------------
    chip_font = _jetbrains("Medium", 16)
    chip_text = "CLIENT-SIDE / NO SERVER"
    chip_bbox = draw.textbbox((0, 0), chip_text, font=chip_font)
    chip_w = chip_bbox[2] - chip_bbox[0] + grid(4)  # 32px padding total
    chip_x = CANVAS_W - margin_x - chip_w
    _draw_receipt_chip(draw, chip_text, chip_x, logo_top, chip_font)

    # --- Accent rule between metadata and headline -----------------------
    rule_y = grid(16)  # 128px
    _draw_accent_rule(draw, margin_x, rule_y, grid(6))  # 48px wide

    # --- Headline --------------------------------------------------------
    title_font = _space_grotesk("Bold", 76)
    title_text = TITLE
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_y = grid(20)  # 160px
    draw.text(
        (margin_x - title_bbox[0], title_y - title_bbox[1]),
        title_text,
        font=title_font,
        fill=_rgb_tuple(_hex(TEXT_HEX)),
    )
    title_w = title_bbox[2] - title_bbox[0]
    title_h = title_bbox[3] - title_bbox[1]

    # Optional inline tag next to the headline
    if TAG:
        tag_font = _jetbrains("Bold", 24)
        tag_text = TAG
        tag_bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
        tag_x = margin_x + title_w + grid(3)  # 24px gap
        # vertically align tag baseline-ish with headline midline
        tag_y = title_y + (title_h - (tag_bbox[3] - tag_bbox[1])) // 2
        draw.text(
            (tag_x - tag_bbox[0], tag_y - tag_bbox[1]),
            tag_text,
            font=tag_font,
            fill=_rgb_tuple(_hex(PRIMARY_HEX)),
        )

    # --- Subhead ---------------------------------------------------------
    sub_font = _jetbrains("Medium", 22)
    sub_text = SUBHEAD
    sub_bbox = draw.textbbox((0, 0), sub_text, font=sub_font)
    sub_y = title_y + title_h + grid(3)  # 24px gap
    draw.text(
        (margin_x - sub_bbox[0], sub_y - sub_bbox[1]),
        sub_text,
        font=sub_font,
        fill=_rgb_tuple(_hex(MUTED_HEX)),
    )

    # --- Footer ----------------------------------------------------------
    footer_font = _jetbrains("Regular", 16)
    footer_text = FOOTER
    footer_bbox = draw.textbbox((0, 0), footer_text, font=footer_font)
    footer_h = footer_bbox[3] - footer_bbox[1]
    footer_y = CANVAS_H - grid(8) - footer_h  # 64px bottom margin
    draw.text(
        (margin_x - footer_bbox[0], footer_y - footer_bbox[1]),
        footer_text,
        font=footer_font,
        fill=_rgb_tuple(_hex(PRIMARY_HEX)),
    )

    # Footer accent rule above the URL
    rule_y2 = footer_y - grid(1)  # 8px gap
    _draw_accent_rule(draw, margin_x, rule_y2, grid(20))  # 160px wide

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUTPUT_PATH, format="PNG", optimize=True)
    return OUTPUT_PATH


def _main() -> int:
    out = render()
    print(f"Wrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(_main())

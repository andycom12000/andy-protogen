"""Generate Protogen face expressions as 128x32 pixel art PNGs.

Based on the character design sheet for 'Andy' protogen.
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw

WIDTH, HEIGHT = 128, 32
BG = (0, 0, 0)
CYAN = (0, 255, 200)  # Main LED color from character design
RED = (255, 60, 60)   # Accent color for angry expression
BSOD_BLUE = (0, 120, 215)  # Windows BSOD background
WHITE = (255, 255, 255)
YELLOW = (255, 200, 0)  # Warning color for loading_bar

# Eye centers
LEFT_EYE = (32, 16)
RIGHT_EYE = (96, 16)

OUT_DIR = Path(__file__).parent.parent / "expressions"


# ---------------------------------------------------------------------------
# Helper drawing functions
# ---------------------------------------------------------------------------

def _mirror_points(points: list[tuple[int, int]], cx_from: int, cx_to: int):
    """Mirror a list of points from one eye center X to another."""
    return [(cx_to - (x - cx_from), y) for x, y in points]


def _draw_default_eye(draw: ImageDraw.ImageDraw, cx: int, cy: int,
                      color=CYAN, is_left: bool = True,
                      rx: int = 10, ry: int = 7, angle: int | None = None):
    """Draw a filled ellipse eye tilted slightly downward toward the nose.

    From the character design: filled oval eyes with a slight inward tilt.
    """
    import PIL.Image

    if angle is None:
        angle = -15 if is_left else 15  # degrees

    # Draw rotated filled ellipse using a temporary image
    size = max(rx, ry) * 2 + 4
    tmp = PIL.Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
    tmp_draw = ImageDraw.Draw(tmp)
    tcx, tcy = size, size
    tmp_draw.ellipse([tcx - rx, tcy - ry, tcx + rx, tcy + ry],
                     fill=(*color, 255))
    tmp = tmp.rotate(angle, center=(tcx, tcy), resample=PIL.Image.BILINEAR)

    # Paste onto the main image
    draw._image.paste(color, (cx - size, cy - size), tmp.split()[3])


def _draw_arc_eye(draw: ImageDraw.ImageDraw, cx: int, cy: int, color=CYAN):
    """Draw an upward arc eye like ^ ^ (happy squint)."""
    w, h = 10, 8
    draw.arc([cx - w, cy - h, cx + w, cy + h], 200, 340, fill=color, width=3)


def _draw_angry_eye(draw: ImageDraw.ImageDraw, cx: int, cy: int,
                    is_left: bool, color=RED):
    """Draw an angry narrow eye with brow line pressing down."""
    w = 10
    # Narrow slit eye
    slit_h = 2
    draw.rectangle([cx - w, cy - slit_h, cx + w, cy + slit_h], fill=color)

    # Angry brow line — slants inward-down
    brow_y_outer = cy - 8
    brow_y_inner = cy - 4
    if is_left:
        draw.line([(cx - w, brow_y_outer), (cx + w, brow_y_inner)],
                  fill=color, width=2)
    else:
        draw.line([(cx - w, brow_y_inner), (cx + w, brow_y_outer)],
                  fill=color, width=2)


def _draw_round_eye(draw: ImageDraw.ImageDraw, cx: int, cy: int,
                    outer_r: int = 9, inner_r: int = 3, color=CYAN):
    """Draw a round eye filled solid."""
    draw.ellipse([cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r],
                 fill=color)


def _draw_teardrop_eye(draw: ImageDraw.ImageDraw, cx: int, cy: int,
                       color=CYAN):
    """Draw an oval eye with teardrop lines below."""
    # Oval eye (outline only, no pupil — teary/watery look)
    rx, ry = 8, 6
    draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=color, width=2)
    # Teardrop lines (brighter cyan)
    bright = (100, 255, 240)
    draw.line([(cx - 3, cy + ry + 1), (cx - 3, cy + ry + 7)],
              fill=bright, width=2)
    draw.line([(cx + 3, cy + ry + 1), (cx + 3, cy + ry + 5)],
              fill=bright, width=2)


def _draw_flat_eye(draw: ImageDraw.ImageDraw, cx: int, cy: int, color=CYAN):
    """Draw a half-closed/flat line eye for helpless expression."""
    w = 10
    # Main flat line
    draw.line([(cx - w, cy), (cx + w, cy)], fill=color, width=3)


def _draw_closed_eye(draw: ImageDraw.ImageDraw, cx: int, cy: int,
                     color=CYAN):
    """Draw a fully closed eye (horizontal line)."""
    draw.line([(cx - 10, cy), (cx + 10, cy)], fill=color, width=3)


def _draw_nose_dots(draw: ImageDraw.ImageDraw, color=CYAN):
    """Draw two small dots for the nose."""
    draw.rectangle([62, 19, 63, 20], fill=color)
    draw.rectangle([64, 19, 65, 20], fill=color)


def _draw_mouth_zigzag(draw: ImageDraw.ImageDraw, color=CYAN):
    """Draw a zigzag/jagged smile mouth."""
    # Zigzag smile: a wavy line with teeth-like pattern
    pts = [
        (54, 25),
        (57, 27), (60, 25), (62, 27), (64, 25), (66, 27), (68, 25),
        (71, 27), (74, 25),
    ]
    draw.line(pts, fill=color, width=1)


def _draw_mouth_zigzag_angry(draw: ImageDraw.ImageDraw, color=CYAN):
    """Draw a dense zigzag U-shaped angry mouth (corners up, center down)."""
    pts = [
        (54, 29),
        (55, 28), (56, 29), (57, 27), (58, 28), (59, 27), (60, 26),
        (61, 27), (62, 25), (63, 26), (64, 24), (65, 26), (66, 25),
        (67, 27), (68, 26), (69, 27), (70, 28), (71, 27), (72, 29),
        (73, 28), (74, 29),
    ]
    draw.line(pts, fill=color, width=1)


def _draw_mouth_zigzag_frown(draw: ImageDraw.ImageDraw, color=CYAN):
    """Draw a zigzag frown mouth (downward curve with jagged edges)."""
    pts = [
        (54, 25),
        (57, 26), (59, 25), (61, 27), (63, 26), (65, 27), (67, 25),
        (70, 26), (74, 25),
    ]
    draw.line(pts, fill=color, width=1)


def _draw_mouth_zigzag_o(draw: ImageDraw.ImageDraw, color=CYAN):
    """Draw a small zigzag 'o' shaped surprised mouth."""
    pts = [
        (61, 25), (63, 24), (65, 25), (67, 26),
        (66, 28), (64, 29), (62, 28), (61, 26), (61, 25),
    ]
    draw.line(pts, fill=color, width=1)


# ---------------------------------------------------------------------------
# Expression generators
# ---------------------------------------------------------------------------

def generate_default() -> Image.Image:
    """Default: filled tilted oval eyes, nose dots, zigzag smile."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    _draw_default_eye(draw, *LEFT_EYE, is_left=True)
    _draw_default_eye(draw, *RIGHT_EYE, is_left=False)
    _draw_nose_dots(draw)
    _draw_mouth_zigzag(draw)
    return img


def generate_happy() -> Image.Image:
    """Happy: upward arc eyes ^ ^ with wide zigzag smile, corners up."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    _draw_arc_eye(draw, *LEFT_EYE)
    _draw_arc_eye(draw, *RIGHT_EYE)
    _draw_nose_dots(draw)
    # Zigzag U-shaped smile, rounder curve, sparser teeth
    pts = [
        (40, 19),
        (44, 20), (48, 22),
        (52, 25), (56, 24),
        (60, 28), (64, 29),
        (68, 28), (72, 24),
        (76, 25), (80, 22),
        (84, 20), (88, 19),
    ]
    draw.line(pts, fill=CYAN, width=3)
    return img


def generate_angry() -> Image.Image:
    """Angry: flat filled oval eyes (red) + brow lines, dense zigzag mouth."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    # Flatter oval eyes, red
    _draw_default_eye(draw, *LEFT_EYE, color=RED, is_left=True, rx=12, ry=5)
    _draw_default_eye(draw, *RIGHT_EYE, color=RED, is_left=False, rx=12, ry=5)
    # Angry brow lines pressing down over the eyes
    lx, ly = LEFT_EYE
    rcx, rcy = RIGHT_EYE
    draw.line([(lx - 12, ly - 9), (lx + 12, ly - 5)], fill=RED, width=2)
    draw.line([(rcx - 12, rcy - 5), (rcx + 12, rcy - 9)], fill=RED, width=2)
    _draw_nose_dots(draw, color=RED)
    _draw_mouth_zigzag_angry(draw, color=RED)
    return img


def generate_very_angry() -> Image.Image:
    """Very angry: egg eyes half-cut by heavy brows, frown wrinkles, fierce zigzag mouth."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    for (cx, cy), is_left in [(LEFT_EYE, True), (RIGHT_EYE, False)]:
        # Draw full egg-shaped eye (taller oval)
        _draw_default_eye(draw, cx, cy, color=RED, is_left=is_left, rx=10, ry=8, angle=-12 if is_left else 12)
        # Cut the top half with a black mask + heavy brow line
        brow_y_outer = cy - 6
        brow_y_inner = cy - 1
        if is_left:
            pts_mask = [(cx - 15, cy - 14), (cx + 15, cy - 14),
                        (cx + 15, brow_y_inner), (cx - 15, brow_y_outer)]
            draw.polygon(pts_mask, fill=BG)
            draw.line([(cx - 13, brow_y_outer), (cx + 13, brow_y_inner)], fill=RED, width=3)
        else:
            pts_mask = [(cx - 15, cy - 14), (cx + 15, cy - 14),
                        (cx - 15, brow_y_inner + 2), (cx + 15, brow_y_outer + 2)]
            draw.polygon(pts_mask, fill=BG)
            draw.line([(cx - 13, brow_y_inner), (cx + 13, brow_y_outer)], fill=RED, width=3)

    _draw_nose_dots(draw, color=RED)
    # Wider zigzag mouth with looser teeth
    pts = [
        (50, 29),
        (53, 27), (56, 29), (59, 26), (62, 28),
        (64, 22),
        (66, 28), (69, 26), (72, 29), (75, 27),
        (78, 29),
    ]
    draw.line(pts, fill=RED, width=1)

    # Mirror left half to right half for perfect symmetry
    left_half = img.crop((0, 0, 64, 32))
    right_half = left_half.transpose(Image.FLIP_LEFT_RIGHT)
    img.paste(right_half, (64, 0))
    return img


def generate_crying() -> Image.Image:
    """Crying: oval eyes with teardrop lines below, zigzag frown."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    _draw_teardrop_eye(draw, *LEFT_EYE)
    _draw_teardrop_eye(draw, *RIGHT_EYE)
    _draw_nose_dots(draw)
    _draw_mouth_zigzag_frown(draw)
    return img


def generate_shocked() -> Image.Image:
    """Shocked: large filled round eyes, upper-half egg mouth."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    _draw_round_eye(draw, *LEFT_EYE, outer_r=10, inner_r=3)
    _draw_round_eye(draw, *RIGHT_EYE, outer_r=10, inner_r=3)
    _draw_nose_dots(draw)
    # Upper half egg mouth, filled solid
    draw.chord([48, 22, 80, 38], 180, 360, fill=CYAN)
    # Crescent fangs carved from top of mouth downward (negative space)
    # Left fang: cut ) shape from top
    draw.ellipse([55, 19, 63, 29], fill=BG)
    draw.ellipse([57, 19, 65, 29], fill=CYAN)
    # Right fang: cut ( shape from top (mirrored)
    draw.ellipse([65, 19, 73, 29], fill=BG)
    draw.ellipse([63, 19, 71, 29], fill=CYAN)
    return img


def generate_helpless() -> Image.Image:
    """Helpless: half-closed flat eyes with zigzag frown."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    _draw_flat_eye(draw, *LEFT_EYE)
    _draw_flat_eye(draw, *RIGHT_EYE)
    _draw_nose_dots(draw)
    _draw_mouth_zigzag_frown(draw)
    return img


def generate_bsod() -> Image.Image:
    """BSOD: Blue Screen of Death — full blue background with :( and text lines."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BSOD_BLUE)
    draw = ImageDraw.Draw(img)

    # Large :( on the left side (Windows 10/11 style)
    # Colon — two dots
    draw.rectangle([12, 8, 14, 11], fill=WHITE)
    draw.rectangle([12, 15, 14, 18], fill=WHITE)
    # Left parenthesis ( — curves left in the middle
    paren_pts = [
        (20, 7), (19, 8), (18, 10), (18, 12), (18, 14),
        (18, 16), (18, 18), (19, 20), (20, 21),
    ]
    for x, y in paren_pts:
        draw.rectangle([x, y, x + 1, y + 1], fill=WHITE)

    # Simulated error text lines on the right side
    text_x = 40
    draw.line([(text_x, 10), (text_x + 50, 10)], fill=WHITE, width=1)
    draw.line([(text_x, 14), (text_x + 38, 14)], fill=WHITE, width=1)
    draw.line([(text_x, 18), (text_x + 44, 18)], fill=WHITE, width=1)
    draw.line([(text_x, 22), (text_x + 30, 22)], fill=WHITE, width=1)

    return img


def generate_blink_frames(base_img: Image.Image, n_frames: int = 7):
    """Generate blink animation based on default expression.

    7 frames: open -> closing -> closed -> opening -> open
    Frame progression: 100% -> 66% -> 33% -> 0% -> 33% -> 66% -> 100%
    """
    frames = []
    # Blink curve: how closed the eye is (0=open, 1=fully closed)
    close_amounts = [0.0, 0.33, 0.66, 1.0, 0.66, 0.33, 0.0]

    for close in close_amounts:
        frame = Image.new("RGB", (WIDTH, HEIGHT), BG)
        draw = ImageDraw.Draw(frame)

        if close >= 1.0:
            # Fully closed — horizontal lines
            _draw_closed_eye(draw, *LEFT_EYE)
            _draw_closed_eye(draw, *RIGHT_EYE)
            _draw_nose_dots(draw)
            _draw_mouth_zigzag(draw)
        elif close <= 0.0:
            # Fully open — copy from base
            frame = base_img.copy()
        else:
            # Partially closed: squish the oval eye vertically
            squished_ry = max(1, int(7 * (1 - close)))
            if squished_ry < 2:
                _draw_closed_eye(draw, *LEFT_EYE)
                _draw_closed_eye(draw, *RIGHT_EYE)
            else:
                for (ecx, ecy), is_left in [(LEFT_EYE, True), (RIGHT_EYE, False)]:
                    rx = 10
                    angle = -15 if is_left else 15
                    size = max(rx, squished_ry) * 2 + 4
                    tmp = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
                    tmp_draw = ImageDraw.Draw(tmp)
                    tc = size
                    tmp_draw.ellipse([tc - rx, tc - squished_ry, tc + rx, tc + squished_ry],
                                     fill=(*CYAN, 255))
                    tmp = tmp.rotate(angle, center=(tc, tc), resample=Image.BILINEAR)
                    frame.paste(CYAN, (ecx - size, ecy - size), tmp.split()[3])
            # Always draw nose and mouth on blink frames
            _draw_nose_dots(draw)
            _draw_mouth_zigzag(draw)

        frames.append(frame)
    return frames


def generate_loading_spinner_frames() -> list[Image.Image]:
    """Generate a spinning dots animation (8 frames).

    8 dots arranged in a circle, each frame highlights a different dot
    with a fading tail of 2-3 trailing dots.
    """
    n_dots = 8
    cx, cy = 64, 16
    radius = 12
    dot_r = 2
    frames = []

    for frame_i in range(n_dots):
        img = Image.new("RGB", (WIDTH, HEIGHT), BG)
        draw = ImageDraw.Draw(img)

        for dot_i in range(n_dots):
            angle = 2 * math.pi * dot_i / n_dots - math.pi / 2  # start from top
            dx = int(cx + radius * math.cos(angle))
            dy = int(cy + radius * math.sin(angle))

            # Distance behind the current highlight (wrapping)
            dist = (frame_i - dot_i) % n_dots

            if dist == 0:
                brightness = 1.0
            elif dist == 1:
                brightness = 0.6
            elif dist == 2:
                brightness = 0.3
            else:
                brightness = 0.08

            color = (
                int(CYAN[0] * brightness),
                int(CYAN[1] * brightness),
                int(CYAN[2] * brightness),
            )
            draw.ellipse([dx - dot_r, dy - dot_r, dx + dot_r, dy + dot_r],
                         fill=color)

        frames.append(img)
    return frames


def generate_loading_bar_frames() -> list[Image.Image]:
    """Generate a loading bar + warning flash animation (18 frames).

    Phase A (12 frames): progress bar filling left to right.
    Phase B (6 frames): yellow warning triangle flashing on/off.
    """
    bar_w = 80
    bar_h = 8
    bar_x = (WIDTH - bar_w) // 2
    bar_y = (HEIGHT - bar_h) // 2
    n_fill = 12
    n_flash = 6
    frames = []

    # Phase A: progress bar
    for i in range(n_fill):
        img = Image.new("RGB", (WIDTH, HEIGHT), BG)
        draw = ImageDraw.Draw(img)
        # Outer frame
        draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
                        outline=CYAN)
        # Inner fill (2px padding)
        fill_max = bar_w - 3  # inner width
        fill_w = int(fill_max * (i + 1) / n_fill)
        if fill_w > 0:
            draw.rectangle([bar_x + 2, bar_y + 2,
                            bar_x + 2 + fill_w, bar_y + bar_h - 2],
                           fill=CYAN)
        frames.append(img)

    # Phase B: warning triangle flash (3 cycles of on/off)
    # Build the warning triangle frame
    tri_cx, tri_cy = 64, 16
    tri_half_w = 12
    tri_top_y = tri_cy - 10
    tri_bot_y = tri_cy + 8
    tri_points = [
        (tri_cx, tri_top_y),
        (tri_cx - tri_half_w, tri_bot_y),
        (tri_cx + tri_half_w, tri_bot_y),
    ]

    for i in range(n_flash):
        img = Image.new("RGB", (WIDTH, HEIGHT), BG)
        if i % 2 == 0:
            # Show warning triangle
            draw = ImageDraw.Draw(img)
            draw.polygon(tri_points, fill=YELLOW)
            # Exclamation mark (white !)
            draw.rectangle([tri_cx - 1, tri_top_y + 5, tri_cx + 1, tri_bot_y - 5],
                           fill=WHITE)
            draw.rectangle([tri_cx - 1, tri_bot_y - 3, tri_cx + 1, tri_bot_y - 2],
                           fill=WHITE)
        # else: pure black frame (already BG)
        frames.append(img)

    return frames


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    base_dir = OUT_DIR / "base"
    base_dir.mkdir(parents=True, exist_ok=True)
    blink_dir = OUT_DIR / "animations" / "blink"
    blink_dir.mkdir(parents=True, exist_ok=True)

    # Generate all static expressions
    expressions = {
        "default": generate_default,
        "happy": generate_happy,
        "angry": generate_angry,
        "crying": generate_crying,
        "shocked": generate_shocked,
        "helpless": generate_helpless,
        "very_angry": generate_very_angry,
        "bsod": generate_bsod,
    }

    generated_images = {}
    for name, gen_func in expressions.items():
        img = gen_func()
        img.save(base_dir / f"{name}.png")
        generated_images[name] = img
        print(f"Generated: {name}.png")

    # Generate blink animation frames (based on default expression)
    blink_frames = generate_blink_frames(generated_images["default"])
    for i, frame in enumerate(blink_frames):
        frame.save(blink_dir / f"frame_{i:02d}.png")
    print(f"Generated: {len(blink_frames)} blink frames")

    # Generate loading spinner animation frames
    spinner_dir = OUT_DIR / "animations" / "loading_spinner"
    spinner_dir.mkdir(parents=True, exist_ok=True)
    spinner_frames = generate_loading_spinner_frames()
    for i, frame in enumerate(spinner_frames):
        frame.save(spinner_dir / f"frame_{i:02d}.png")
    print(f"Generated: {len(spinner_frames)} loading_spinner frames")

    # Generate loading bar animation frames
    bar_dir = OUT_DIR / "animations" / "loading_bar"
    bar_dir.mkdir(parents=True, exist_ok=True)
    bar_frames = generate_loading_bar_frames()
    for i, frame in enumerate(bar_frames):
        frame.save(bar_dir / f"frame_{i:02d}.png")
    print(f"Generated: {len(bar_frames)} loading_bar frames")

    # Clean up old files that are no longer needed
    old_files = [base_dir / "sad.png"]
    for f in old_files:
        if f.exists():
            f.unlink()
            print(f"Removed old file: {f.name}")

    print(f"\nDone! All expressions saved to {OUT_DIR}")


if __name__ == "__main__":
    main()

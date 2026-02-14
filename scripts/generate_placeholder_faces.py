"""Generate placeholder Protogen face expressions as 128x32 pixel art PNGs."""
from pathlib import Path
from PIL import Image, ImageDraw

WIDTH, HEIGHT = 128, 32
BG = (0, 0, 0)
EYE_COLOR = (0, 255, 200)  # Cyan-ish protogen eye color

OUT_DIR = Path(__file__).parent.parent / "expressions"


def draw_eye_v(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, flip: bool = False):
    """Draw a V-shaped (happy) eye."""
    pts = []
    if flip:
        # Inverted V (like ^)
        pts = [(cx - size, cy + size // 2), (cx, cy - size // 2), (cx + size, cy + size // 2)]
    else:
        # V shape
        pts = [(cx - size, cy - size // 2), (cx, cy + size // 2), (cx + size, cy - size // 2)]
    draw.line(pts, fill=EYE_COLOR, width=2)


def draw_eye_round(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int):
    """Draw a round eye."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=EYE_COLOR, width=2)


def draw_eye_half_closed(draw: ImageDraw.ImageDraw, cx: int, cy: int, w: int):
    """Draw a half-closed eye (horizontal line)."""
    draw.line([(cx - w, cy), (cx + w, cy)], fill=EYE_COLOR, width=3)


def draw_eye_slant(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, angry: bool = False):
    """Draw a slanted eye for angry/determined expression."""
    if angry:
        # Inner side high, outer side low (for left eye, mirror for right)
        draw.line([(cx - size, cy - size // 3), (cx + size, cy + size // 3)], fill=EYE_COLOR, width=2)
        draw.line([(cx - size, cy - size // 3 + 4), (cx + size, cy + size // 3 + 4)], fill=EYE_COLOR, width=2)
    else:
        draw.line([(cx - size, cy + size // 3), (cx + size, cy - size // 3)], fill=EYE_COLOR, width=2)


def generate_happy():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    # Left eye: V shape (happy squint)
    draw_eye_v(draw, 32, 16, 10)
    # Right eye: V shape
    draw_eye_v(draw, 96, 16, 10)
    # Small mouth arc
    draw.arc([52, 20, 76, 30], 0, 180, fill=EYE_COLOR, width=1)
    return img


def generate_sad():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    # Inverted V eyes (sad)
    draw_eye_v(draw, 32, 16, 10, flip=True)
    draw_eye_v(draw, 96, 16, 10, flip=True)
    # Sad mouth
    draw.arc([52, 22, 76, 32], 180, 360, fill=EYE_COLOR, width=1)
    return img


def generate_angry():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    # Angry slanted eyes
    draw_eye_slant(draw, 32, 14, 10, angry=True)
    # Mirror for right eye
    draw.line([(96 - 10, 14 + 10 // 3), (96 + 10, 14 - 10 // 3)], fill=EYE_COLOR, width=2)
    draw.line([(96 - 10, 14 + 10 // 3 + 4), (96 + 10, 14 - 10 // 3 + 4)], fill=EYE_COLOR, width=2)
    # Angry mouth
    draw.line([(54, 26), (74, 26)], fill=EYE_COLOR, width=2)
    return img


def generate_blink_frames(base_img: Image.Image, n_frames: int = 7):
    """Generate blink animation: eyes close then open."""
    frames = []
    # Extract eye regions and create closing animation
    for i in range(n_frames):
        frame = base_img.copy()
        draw = ImageDraw.Draw(frame)
        progress = i / (n_frames - 1)  # 0 to 1

        if progress <= 0.5:
            # Closing: 0 -> 0.5
            close = progress * 2  # 0 to 1
        else:
            # Opening: 0.5 -> 1
            close = (1 - progress) * 2  # 1 to 0

        # Draw eyes at various stages of closing
        eye_height = int(10 * (1 - close))
        if eye_height <= 1:
            # Fully closed - horizontal line
            draw_eye_half_closed(draw, 32, 16, 10)
            draw_eye_half_closed(draw, 96, 16, 10)
        else:
            # Partially open V eyes
            # Clear eye areas first (black boxes)
            draw.rectangle([18, 6, 46, 26], fill=BG)
            draw.rectangle([82, 6, 110, 26], fill=BG)
            draw_eye_v(draw, 32, 16, max(3, eye_height))
            draw_eye_v(draw, 96, 16, max(3, eye_height))
            # Redraw mouth
            draw.arc([52, 20, 76, 30], 0, 180, fill=EYE_COLOR, width=1)

        frames.append(frame)
    return frames


def main():
    # Create directories
    base_dir = OUT_DIR / "base"
    base_dir.mkdir(parents=True, exist_ok=True)
    blink_dir = OUT_DIR / "animations" / "blink"
    blink_dir.mkdir(parents=True, exist_ok=True)

    # Generate static expressions
    happy = generate_happy()
    happy.save(base_dir / "happy.png")
    print("Generated: happy.png")

    sad = generate_sad()
    sad.save(base_dir / "sad.png")
    print("Generated: sad.png")

    angry = generate_angry()
    angry.save(base_dir / "angry.png")
    print("Generated: angry.png")

    # Generate blink animation frames
    blink_frames = generate_blink_frames(happy)
    for i, frame in enumerate(blink_frames):
        frame.save(blink_dir / f"frame_{i:02d}.png")
    print(f"Generated: {len(blink_frames)} blink frames")

    print("Done! All expressions saved to", OUT_DIR)


if __name__ == "__main__":
    main()

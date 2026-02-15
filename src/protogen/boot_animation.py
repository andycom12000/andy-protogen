from __future__ import annotations

import asyncio

from PIL import Image, ImageDraw, ImageFont

from protogen.display.base import DisplayBase


def render_boot_frame(width: int, height: int, t: float) -> Image.Image:
    """Render a single boot animation frame.

    Args:
        width: Display width in pixels.
        height: Display height in pixels.
        t: Progress from 0.0 to 1.0.

    Returns:
        RGB image for this frame.
    """
    img = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Phase 1: Scanline sweep (t=0.0 to 0.3)
    if t < 0.3:
        progress = t / 0.3
        y = int(progress * height)
        # Draw a bright cyan scanline with glow
        for dy in range(-2, 3):
            row = y + dy
            if 0 <= row < height:
                intensity = max(0, 255 - abs(dy) * 80)
                draw.line([(0, row), (width - 1, row)], fill=(0, intensity, intensity))

    # Phase 2: Text display (t=0.3 to 0.75)
    elif t < 0.75:
        text_progress = (t - 0.3) / 0.45
        text = "PROTOGEN"
        font = ImageFont.load_default()
        bbox = font.getbbox(text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (width - tw) // 2
        y = (height - th) // 2

        # Fade in the text
        brightness = min(255, int(text_progress * 3 * 255))
        color = (0, brightness, brightness)
        draw.text((x, y), text, fill=color, font=font)

    # Phase 3: Fade out (t=0.75 to 1.0)
    else:
        fade_progress = (t - 0.75) / 0.25
        text = "PROTOGEN"
        font = ImageFont.load_default()
        bbox = font.getbbox(text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (width - tw) // 2
        y = (height - th) // 2

        brightness = max(0, int((1.0 - fade_progress) * 255))
        color = (0, brightness, brightness)
        draw.text((x, y), text, fill=color, font=font)

    return img


async def play_boot_animation(
    display: DisplayBase,
    duration: float = 2.0,
    fps: int = 15,
) -> None:
    """Play the boot animation sequence on the display."""
    total_frames = max(1, int(duration * fps))
    interval = 1.0 / fps

    for i in range(total_frames + 1):
        t = i / total_frames
        frame = render_boot_frame(display.width, display.height, t)
        display.show_image(frame)
        if i < total_frames:
            await asyncio.sleep(interval)

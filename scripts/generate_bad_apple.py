"""Download Bad Apple!! video and extract frames as 128x32 black-and-white PNGs.

Requirements: yt-dlp, opencv-python-headless, Pillow
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

WIDTH, HEIGHT = 128, 32
TARGET_FPS = 15
THRESHOLD = 128  # Grayscale threshold for black/white conversion
OUT_DIR = Path(__file__).parent.parent / "expressions" / "animations" / "bad_apple"
VIDEO_URL = "https://www.youtube.com/watch?v=FtutLA63Cp8"


def download_video(output_path: str) -> str:
    """Download Bad Apple video using yt-dlp."""
    print("==> Downloading Bad Apple!! video...")
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-f", "worst[ext=mp4]",  # smallest mp4 for speed
        "-o", output_path,
        "--no-playlist",
        VIDEO_URL,
    ]
    subprocess.run(cmd, check=True)
    return output_path


def extract_frames(video_path: str, out_dir: Path, target_fps: int = TARGET_FPS):
    """Extract frames from video, resize to 128x32 B&W, save as PNGs."""
    out_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    src_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / src_fps if src_fps > 0 else 0

    # Calculate frame sampling interval
    frame_interval = src_fps / target_fps

    print(f"    Source: {total_frames} frames @ {src_fps:.1f} fps ({duration:.1f}s)")
    print(f"    Target: {target_fps} fps -> ~{int(duration * target_fps)} frames")

    frame_idx = 0
    output_idx = 0
    next_sample = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx >= next_sample:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Resize to 128x32 (stretch to fill)
            resized = cv2.resize(gray, (WIDTH, HEIGHT), interpolation=cv2.INTER_AREA)

            # Threshold to pure black and white
            _, bw = cv2.threshold(resized, THRESHOLD, 255, cv2.THRESH_BINARY)

            # Convert to RGB PIL Image (white on black)
            rgb = np.stack([bw, bw, bw], axis=-1)
            img = Image.fromarray(rgb, "RGB")
            img.save(out_dir / f"frame_{output_idx:04d}.png")

            output_idx += 1
            next_sample += frame_interval

            if output_idx % 500 == 0:
                print(f"    Processed {output_idx} frames...")

        frame_idx += 1

    cap.release()
    print(f"==> Extracted {output_idx} frames to {out_dir}")
    return output_idx


def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = str(Path(tmpdir) / "bad_apple.mp4")
        download_video(video_path)
        n_frames = extract_frames(video_path, OUT_DIR)

    print(f"\nDone! {n_frames} frames saved to {OUT_DIR}")
    print(f"Add to manifest.json with fps={TARGET_FPS}")


if __name__ == "__main__":
    main()

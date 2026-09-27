"""Stand-in photos for test data: a coloured background with a plain shape on it.

Test ads need pictures, but not real ones. A flat colour and a square, circle or triangle is enough to
see that the cards, the galleries, the thumbnails and the page weight all behave — and it is instantly
obvious to anyone looking at the site that this ad is not real.

The files are written the way real photos are written (a full size and a small copy next to it, same
naming), but into a folder of their own, so removing the test data removes the pictures with it.
"""

import shutil
from pathlib import Path

from PIL import Image, ImageDraw

from app.services.photos import FULL_SIDE, QUALITY, THUMB_QUALITY, THUMB_SIDE, media_root, thumb_path

FOLDER = "ads/placeholder"
WIDTH, HEIGHT = 1600, 1200

# muted backgrounds; a test card should look calm next to a real one, not shout
BACKGROUNDS: tuple[tuple[int, int, int], ...] = (
    (222, 232, 242), (238, 226, 214), (226, 240, 228), (244, 232, 240),
    (232, 236, 216), (216, 234, 240), (240, 224, 222), (228, 226, 244),
    (236, 240, 222), (224, 238, 236), (242, 236, 218), (230, 228, 230),
)  # fmt: skip
FOREGROUNDS: tuple[tuple[int, int, int], ...] = (
    (72, 104, 148), (150, 96, 64), (78, 134, 92), (146, 84, 126),
    (120, 128, 60), (64, 124, 148), (156, 88, 82), (94, 88, 156),
)  # fmt: skip
SHAPES = ("square", "circle", "triangle", "rounded", "diamond")


def _draw(shape: str, background: tuple[int, int, int], foreground: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), background)
    pen = ImageDraw.Draw(image)
    side = int(min(WIDTH, HEIGHT) * 0.42)
    cx, cy = WIDTH // 2, HEIGHT // 2
    box = (cx - side, cy - side, cx + side, cy + side)
    if shape == "square":
        pen.rectangle(box, fill=foreground)
    elif shape == "circle":
        pen.ellipse(box, fill=foreground)
    elif shape == "rounded":
        pen.rounded_rectangle(box, radius=side // 3, fill=foreground)
    elif shape == "triangle":
        pen.polygon([(cx, cy - side), (cx - side, cy + side), (cx + side, cy + side)], fill=foreground)
    else:  # diamond
        pen.polygon([(cx, cy - side), (cx + side, cy), (cx, cy + side), (cx - side, cy)], fill=foreground)
    return image


def _write(image: Image.Image, path: Path, side: int, quality: int) -> int:
    copy = image.copy()
    copy.thumbnail((side, side), Image.LANCZOS)
    path.parent.mkdir(parents=True, exist_ok=True)
    copy.save(path, "JPEG", quality=quality, optimize=True, progressive=True)
    return path.stat().st_size


def build_pool() -> list[tuple[str, int, int, int]]:
    """Every colour-and-shape combination, written once. Returns (path, width, height, size) rows.

    Thousands of ads share these few dozen files: a test needs many ads, not many different pictures.
    """
    pool: list[tuple[str, int, int, int]] = []
    for shape_index, shape in enumerate(SHAPES):
        for colour_index, background in enumerate(BACKGROUNDS):
            foreground = FOREGROUNDS[(shape_index + colour_index) % len(FOREGROUNDS)]
            relative = f"{FOLDER}/{shape}-{colour_index:02d}.jpg"
            full = media_root() / relative
            image = _draw(shape, background, foreground)
            size = _write(image, full, FULL_SIDE, QUALITY)
            _write(image, media_root() / thumb_path(relative), THUMB_SIDE, THUMB_QUALITY)
            width, height = Image.open(full).size
            pool.append((f"/media/{relative}", width, height, size))
    return pool


def delete_pool() -> int:
    """The whole folder goes at once; no real photo has ever lived in it."""
    folder = media_root() / FOLDER
    if not folder.exists():
        return 0
    files = sum(1 for _ in folder.iterdir())
    shutil.rmtree(folder, ignore_errors=True)
    return files

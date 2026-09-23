"""Photos of an ad.

A phone photo arrives as it was taken: 4 MB, sideways, with the place it was taken written inside it.
We never keep that file. Pillow opens it, turns it the right way up, drops everything but the pixels and
writes two JPEGs: one for the ad page and a small one for the cards. The names are random, so nobody can
guess another person's photo by its address.
"""

import logging
import secrets
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, status
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings

log = logging.getLogger("bazarcito.photos")

MAX_BYTES = 8 * 1024 * 1024
# a picture that unpacks into hundreds of megapixels is an attack on memory, not a photo of a sofa
MAX_PIXELS = 50_000_000
FULL_SIDE = 1600
THUMB_SIDE = 420
QUALITY = 82
THUMB_QUALITY = 78
THUMB_SUFFIX = "_s"

# what a phone or a computer sends; the first bytes decide, not the file name
SIGNATURES: tuple[bytes, ...] = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"RIFF", b"GIF8")


def media_root() -> Path:
    return Path(settings.media_root)


def _check(data: bytes) -> None:
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty_file")
    if len(data) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large")
    if not any(data.startswith(magic) for magic in SIGNATURES):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "not_an_image")


def _open(data: bytes) -> Image.Image:
    try:
        image = Image.open(BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "not_an_image") from exc
    if image.width * image.height > MAX_PIXELS:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "image_too_large")
    # EXIF says "this one is sideways": apply it, then forget the EXIF (it can hold the place and time)
    image = ImageOps.exif_transpose(image)
    if image.mode in ("RGBA", "LA", "P"):
        flat = Image.new("RGB", image.size, (255, 255, 255))
        rgba = image.convert("RGBA")
        flat.paste(rgba, mask=rgba.split()[-1])
        return flat
    return image.convert("RGB")


def _write(image: Image.Image, path: Path, side: int, quality: int) -> int:
    copy = image.copy()
    copy.thumbnail((side, side), Image.LANCZOS)
    path.parent.mkdir(parents=True, exist_ok=True)
    copy.save(path, "JPEG", quality=quality, optimize=True, progressive=True)
    return path.stat().st_size


def thumb_path(path: str) -> str:
    """The card-sized copy that sits next to the full photo."""
    name, _, ext = path.rpartition(".")
    return f"{name}{THUMB_SUFFIX}.{ext}"


def save(data: bytes) -> tuple[str, int, int, int]:
    """Returns (path as the site serves it, width, height, size in bytes)."""
    _check(data)
    image = _open(data)

    now = datetime.now(UTC)
    name = f"{secrets.token_urlsafe(12)}.jpg"
    relative = f"ads/{now:%Y/%m}/{name}"
    full = media_root() / relative

    size = _write(image, full, FULL_SIDE, QUALITY)
    _write(image, media_root() / thumb_path(relative), THUMB_SIDE, THUMB_QUALITY)
    width, height = Image.open(full).size
    return f"/media/{relative}", width, height, size


def delete(path: str) -> None:
    """Best effort: a photo whose row is gone must not keep the disk busy, but a missing file is fine."""
    relative = path.removeprefix("/media/")
    for candidate in (relative, thumb_path(relative)):
        file = media_root() / candidate
        try:
            file.unlink(missing_ok=True)
        except OSError as error:  # a file we may not touch: log it, the row is deleted anyway
            log.warning("cannot delete %s: %s", file, error)

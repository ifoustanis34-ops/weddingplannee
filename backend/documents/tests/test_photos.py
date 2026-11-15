"""Photos (staff, tasks, equipment), not logos: JPEG, right way up (feedback 15/11/2026)."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from core.exceptions import BusinessError
from documents.images import process_photo


def jpeg(size: tuple[int, int], orientation: int | None = None) -> bytes:
    image = Image.new("RGB", size, (200, 30, 90))
    exif = Image.Exif()
    if orientation:
        exif[0x0112] = orientation
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif.tobytes())
    return buffer.getvalue()


def test_a_photo_is_stored_as_a_light_jpeg_turned_the_right_way_up() -> None:
    processed = process_photo(jpeg((4000, 3000), orientation=6))  # taken rotated
    assert (processed.extension, processed.content_type) == ("jpg", "image/jpeg")
    with Image.open(io.BytesIO(processed.content)) as stored:
        assert stored.format == "JPEG"
        assert stored.size == (900, 1200)  # portrait again, longest side 1200


def test_a_transparent_png_gets_a_white_background() -> None:
    buffer = io.BytesIO()
    Image.new("RGBA", (50, 50), (0, 0, 0, 0)).save(buffer, format="PNG")
    with Image.open(io.BytesIO(process_photo(buffer.getvalue()).content)) as stored:
        pixel = stored.getpixel((10, 10))
        assert isinstance(pixel, tuple) and pixel[0] > 240


def test_an_unreadable_file_says_what_to_do() -> None:
    with pytest.raises(BusinessError) as refused:
        process_photo(b"ftypheic not a picture Pillow knows")
    assert "Le plus compatible" in str(refused.value.detail)

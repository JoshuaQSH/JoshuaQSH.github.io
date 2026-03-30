#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from PIL import ExifTags, Image, ImageOps


RAW_DIR = Path("photo_album_raw")
OUT_DIR = Path("static/images/photo-album")
DATA_PATH = Path("data/photo_album.json")
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_WIDTH = 2200
JPEG_QUALITY = 84
DEFAULT_CAMERA = "Sony ILCE-7M4"
DEFAULT_LENS = "FE 24-105mm F4 G OSS"
EDITABLE_FIELDS = (
    "title",
    "marker",
    "display_date",
    "alt",
    "camera",
    "lens",
    "aperture",
    "iso",
    "exposure_time",
)


def slugify(text: str) -> str:
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def read_taken_datetime(exif_tags: dict[object, object], path: Path) -> datetime:
    dt_raw = exif_tags.get("DateTime")
    if isinstance(dt_raw, str):
        try:
            return datetime.strptime(dt_raw, "%Y:%m:%d %H:%M:%S")
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime)


def load_existing_entries() -> dict[str, dict[str, object]]:
    if not DATA_PATH.exists():
        return {}
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    entries = payload.get("entries", [])
    return {
        str(entry.get("image")): entry
        for entry in entries
        if isinstance(entry, dict) and entry.get("image")
    }


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    existing_entries = load_existing_entries()
    entries = []
    generated_images = set()

    for path in sorted(RAW_DIR.iterdir()):
        if path.name.startswith(".") or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        title = path.stem
        slug = slugify(title)
        output_name = f"{slug}.jpg"
        output_path = OUT_DIR / output_name
        image_url = f"/images/photo-album/{output_name}"

        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image)
            exif = image.getexif()
            tags = {ExifTags.TAGS.get(key, key): value for key, value in exif.items()}
            taken = read_taken_datetime(tags, path)

            width, height = image.size
            if width > MAX_WIDTH:
                resized_height = int(height * (MAX_WIDTH / width))
                image = image.resize((MAX_WIDTH, resized_height), Image.Resampling.LANCZOS)

            image.convert("RGB").save(
                output_path,
                format="JPEG",
                quality=JPEG_QUALITY,
                optimize=True,
                progressive=True,
            )

        entry = {
            "title": title,
            "marker": taken.strftime("%b %Y"),
            "taken_at": taken.strftime("%Y-%m-%d %H:%M:%S"),
            "display_date": taken.strftime("%b %d, %Y %H:%M"),
            "image": image_url,
            "alt": title,
            "camera": DEFAULT_CAMERA,
            "lens": DEFAULT_LENS,
            "aperture": "",
            "iso": "",
            "exposure_time": "",
        }

        existing_entry = existing_entries.get(image_url)
        if existing_entry:
            for field in EDITABLE_FIELDS:
                value = existing_entry.get(field)
                if value not in (None, ""):
                    entry[field] = value

        entries.append(entry)
        generated_images.add(output_path.name)

    entries.sort(key=lambda item: item["taken_at"])
    DATA_PATH.write_text(json.dumps({"entries": entries}, indent=2) + "\n", encoding="utf-8")

    for path in OUT_DIR.glob("*.jpg"):
        if path.name not in generated_images:
            path.unlink()


if __name__ == "__main__":
    main()

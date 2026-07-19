"""Create web-ready storybook assets from the archived source images.

This helper is for maintainers.  Students do not need it in Colab.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = REPO_ROOT / "data" / "ai_solution_practicum" / "assets"
ILLUSTRATION_DIR = REPO_ROOT / "docs" / "assets" / "illustrations"
BRAND_DIR = REPO_ROOT / "docs" / "assets" / "brand"

ILLUSTRATIONS = {
    "cover-ai-story-lab.png": ("cover-ai-story-lab.webp", 1680),
    "story-cnn-pet-shelter.png": ("story-cnn-pet-shelter.webp", 1280),
    "story-rnn-message-triage.png": ("story-rnn-message-triage.webp", 1280),
    "story-gan-art-studio.png": ("story-gan-art-studio.webp", 1280),
    "story-rl-strategy-board.png": ("story-rl-strategy-board.webp", 1280),
    "style-content-coast.png": ("style-content-coast.webp", 960),
    "style-reference-sea-wind.png": ("style-reference-sea-wind.webp", 960),
}

BRAND_STICKERS = {
    "teacher-check.png": "teacher-check.webp",
    "teacher-magnify.png": "teacher-magnify.webp",
    "teacher-cheer.png": "teacher-cheer.webp",
}


def resize_to_width(image: Image.Image, max_width: int) -> Image.Image:
    if image.width <= max_width:
        return image
    height = round(image.height * max_width / image.width)
    return image.resize((max_width, height), Image.Resampling.LANCZOS)


def save_webp(source: Path, destination: Path, max_width: int, quality: int) -> None:
    with Image.open(source) as image:
        image = resize_to_width(image, max_width)
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, "WEBP", quality=quality, method=6)
        print(f"{source.name} -> {destination.relative_to(REPO_ROOT)} ({image.width}x{image.height})")


def main() -> None:
    for source_name, (output_name, max_width) in ILLUSTRATIONS.items():
        save_webp(
            SOURCE_DIR / source_name,
            ILLUSTRATION_DIR / output_name,
            max_width=max_width,
            quality=86,
        )

    save_webp(
        BRAND_DIR / "enen-teacher.png",
        BRAND_DIR / "enen-teacher.webp",
        max_width=512,
        quality=90,
    )

    for source_name, output_name in BRAND_STICKERS.items():
        save_webp(
            BRAND_DIR / source_name,
            BRAND_DIR / output_name,
            max_width=264,
            quality=92,
        )


if __name__ == "__main__":
    main()

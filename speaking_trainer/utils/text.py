from __future__ import annotations

import re
import unicodedata


def normalize_plain_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def slugify(value: str, fallback: str = "project") -> str:
    value = re.sub(r"[^a-z0-9]+", "_", value.lower().strip())
    value = re.sub(r"_+", "_", value).strip("_")
    return value or fallback

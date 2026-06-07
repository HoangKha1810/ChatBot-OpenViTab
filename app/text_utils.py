from __future__ import annotations

import re
import unicodedata
from typing import Iterable


def strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value or "")
    text = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").replace("Đ", "D")


def normalize_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\xa0", " ").replace("\t", " ")
    text = re.sub(r"\[[^\]]+\]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_key(value: object) -> str:
    text = strip_accents(normalize_text(value)).lower()
    text = re.sub(r"[^a-z0-9%]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize(value: object) -> list[str]:
    text = normalize_key(value)
    return [part for part in text.split() if part]


def token_set(value: object) -> set[str]:
    return set(tokenize(value))


def jaccard(left: Iterable[str], right: Iterable[str]) -> float:
    a = set(left)
    b = set(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def compact(value: object) -> str:
    return re.sub(r"\s+", "", normalize_key(value))


def parse_number(value: object) -> float | None:
    text = normalize_text(value)
    if not text or text in {"-", "—", "–"}:
        return None

    match = re.search(r"-?\d[\d\s.,]*", text)
    if not match:
        return None

    raw = match.group(0).replace(" ", "")
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        parts = raw.split(",")
        if len(parts[-1]) == 3 and len(parts) > 1:
            raw = raw.replace(",", "")
        else:
            raw = raw.replace(",", ".")
    elif raw.count(".") > 1:
        raw = raw.replace(".", "")
    elif "." in raw and len(raw.rsplit(".", 1)[-1]) == 3:
        raw = raw.replace(".", "")

    try:
        return float(raw)
    except ValueError:
        return None


def format_number(value: float) -> str:
    if abs(value - int(value)) < 1e-9:
        return str(int(value))
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def contains_all_terms(text: object, terms: Iterable[str]) -> bool:
    haystack = normalize_key(text)
    return all(term in haystack for term in terms if term)


def truthy_answer(value: str) -> bool | None:
    key = normalize_key(value)
    yes = {"co", "dung", "phai", "yes"}
    no = {"khong", "sai", "no"}
    if key in yes:
        return True
    if key in no:
        return False
    return None

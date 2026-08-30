"""Local, offline OCR for handwritude 'parchi' (handwritten order slips): OpenCV
deskew/threshold preprocessing, pytesseract for text extraction, thefuzz for matching
extracted lines against items.item_name. No network call, no API key.

Every failure mode — undecodable image, tesseract raising, zero usable tokens — returns a
{"success": False, "reason": ...} dict rather than raising, so the router can turn it into
a plain `200 {success: false, reason: ...}` per the handoff spec section 4 ("On OCR failure
... return 200 {success: false, reason: ...}, not a 500").
"""
import logging
import re
from typing import Dict, List, Optional

import cv2
import numpy as np
import pytesseract
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Item

logger = logging.getLogger("pos_backend.ocr")

if settings.TESSERACT_CMD:
    # Windows doesn't put tesseract.exe on PATH by default — point pytesseract at it
    # explicitly (set TESSERACT_CMD in the environment, e.g. to
    # "C:\\Program Files\\Tesseract-OCR\\tesseract.exe").
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

_QTY_PATTERN = re.compile(r"(?:^|[\sx×\-])(\d{1,4})\s*$", re.IGNORECASE)


def _deskew(gray: np.ndarray) -> np.ndarray:
    """Best-effort deskew via minAreaRect on foreground pixels. Falls back to the
    un-rotated image on anything that looks degenerate (too few foreground pixels, a
    nonsensical angle) rather than risking a warped, less-readable image."""
    try:
        inverted = cv2.bitwise_not(gray)
        _, thresh = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        coords = np.column_stack(np.where(thresh > 0))
        if coords.shape[0] < 50:
            return gray
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        if abs(angle) < 0.1 or abs(angle) > 45:
            return gray
        h, w = gray.shape[:2]
        matrix = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        return cv2.warpAffine(gray, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    except Exception as exc:  # noqa: BLE001
        logger.debug("deskew skipped: %s", exc)
        return gray


def preprocess_image(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("could not decode image data")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = _deskew(gray)
    gray = cv2.medianBlur(gray, 3)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )
    return thresh


def extract_lines(image_bytes: bytes, lang: str = "eng") -> List[str]:
    processed = preprocess_image(image_bytes)
    text = pytesseract.image_to_string(processed, lang=lang)
    return [line.strip() for line in text.splitlines() if line.strip()]


def split_qty(raw_line: str) -> "tuple[str, float]":
    """'chaki ata 5kg - 10' -> ('chaki ata 5kg', 10.0). No trailing number -> qty 1."""
    m = _QTY_PATTERN.search(raw_line)
    if m:
        qty = float(m.group(1))
        name_part = raw_line[: m.start()].strip(" -x×")
        if name_part:
            return name_part, qty
    return raw_line.strip(), 1.0


def _fuzzy_candidate(name_part: str, choices: List[str]) -> "tuple[Optional[str], float]":
    if not choices:
        return None, 0.0
    try:
        from thefuzz import process as fuzz_process

        match, score = fuzz_process.extractOne(name_part, choices)
        return match, round(score / 100.0, 2)
    except Exception as exc:  # noqa: BLE001
        logger.debug("fuzzy match failed for %r: %s", name_part, exc)
        return None, 0.0


def match_items(lines: List[str], name_to_id: Dict[str, int]) -> List[dict]:
    """Best-effort fuzzy match for every raw line, unfiltered by confidence — the caller
    decides the floor cutoff."""
    choices = list(name_to_id.keys())
    out = []
    for raw in lines:
        name_part, qty = split_qty(raw)
        candidate_name, confidence = _fuzzy_candidate(name_part, choices)
        candidate_id = name_to_id.get(candidate_name) if candidate_name else None
        out.append(
            {
                "raw_text": raw,
                "candidate_id": candidate_id,
                "candidate_name": candidate_name,
                "confidence": confidence,
                "qty": qty,
            }
        )
    return out


def run_ocr(db: Session, image_bytes: bytes, confidence_floor: float) -> dict:
    try:
        lines_raw = extract_lines(image_bytes, lang=settings.OCR_LANG)
    except Exception as exc:  # noqa: BLE001 — never let a bad image 500 this endpoint
        logger.info("OCR extraction failed: %s", exc)
        return {
            "success": False,
            "reason": f"could not read this parchi — {exc}",
        }

    if not lines_raw:
        return {
            "success": False,
            "reason": (
                f"tesseract returned 0 usable tokens above the confidence floor "
                f"({confidence_floor:.2f}). likely causes: low contrast, heavy skew, or ink bleed."
            ),
        }

    name_to_id = {name: item_id for item_id, name in db.query(Item.id, Item.item_name).all()}
    matched = match_items(lines_raw, name_to_id)

    lines_out = []
    unmatched: List[str] = []
    for m in matched:
        included = m["candidate_id"] is not None and m["confidence"] >= confidence_floor
        lines_out.append(
            {
                "raw_text": m["raw_text"],
                "matched_item_id": m["candidate_id"] if included else None,
                "matched_item_name": m["candidate_name"] if included else None,
                "confidence": m["confidence"],
                "qty": m["qty"],
            }
        )
        if not included:
            unmatched.append(m["raw_text"])

    return {
        "success": True,
        "lines": lines_out,
        "unmatched": unmatched,
        "confidence_floor": confidence_floor,
    }

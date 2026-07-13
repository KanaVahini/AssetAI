"""
OCR wrapper. Kept isolated here so swapping Tesseract -> PaddleOCR later
only touches this one file, not every handler that needs OCR.
"""

import os
import re

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    
# Try to import PaddleOCR as fallback
try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False


def _configure_tesseract():
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            pytesseract.pytesseract.tesseract_cmd = candidate
            return candidate
    return pytesseract.pytesseract.tesseract_cmd


_configure_tesseract()


def _preprocess_image(pil_image: Image.Image) -> Image.Image:
    image = pil_image.convert("L")
    image = ImageOps.autocontrast(image)
    image = image.resize((image.width * 2, image.height * 2))
    image = ImageEnhance.Sharpness(image).enhance(2.0)
    image = image.filter(ImageFilter.MedianFilter())
    return image


def _is_meaningful_token(token: str) -> bool:
    if not token:
        return False
    cleaned = token.strip()
    if not cleaned:
        return False
    return bool(re.search(r"[A-Za-z0-9]", cleaned))


def _build_text_from_data(data, min_confidence: float = 65.0) -> str:
    lines = {}
    for idx, token in enumerate(data.get("text", [])):
        token = (token or "").strip()
        conf_raw = data.get("conf", ["-1"])[idx]
        try:
            confidence = float(conf_raw)
        except (TypeError, ValueError):
            confidence = -1.0

        if confidence < min_confidence or not _is_meaningful_token(token):
            continue

        line_key = (
            data.get("block_num", [0])[idx],
            data.get("par_num", [0])[idx],
            data.get("line_num", [0])[idx],
        )
        lines.setdefault(line_key, []).append((data.get("left", [0])[idx], token))

    ordered_lines = []
    for line_key in sorted(lines.keys()):
        words = [word for _, word in sorted(lines[line_key], key=lambda item: item[0])]
        line_text = " ".join(words).strip()
        if line_text:
            ordered_lines.append(line_text)

    return "\n".join(ordered_lines).strip()


def _ocr_tesseract(pil_image: Image.Image):
    """OCR using Tesseract (if installed)"""
    processed = _preprocess_image(pil_image)
    config = "--oem 1 --psm 4"
    data = pytesseract.image_to_data(processed, config=config, output_type=pytesseract.Output.DICT)

    text = _build_text_from_data(data)
    confs = []
    for conf_raw, token in zip(data.get("conf", []), data.get("text", [])):
        token = (token or "").strip()
        if not token or not _is_meaningful_token(token):
            continue
        try:
            confidence = float(conf_raw)
        except (TypeError, ValueError):
            continue
        if confidence >= 65.0:
            confs.append(confidence)

    mean_conf = (sum(confs) / len(confs) / 100.0) if confs else 0.0

    if not text.strip():
        alt_text = pytesseract.image_to_string(processed, config=config)
        text = alt_text.strip()

    return text, round(mean_conf, 3)


def _ocr_paddle(pil_image: Image.Image):
    """OCR using PaddleOCR (pure Python, no system dependencies)"""
    if not PADDLE_AVAILABLE:
        raise ImportError("PaddleOCR not installed. Install with: pip install paddleocr paddlepaddle")
    
    # Initialize PaddleOCR on demand (without use_gpu parameter for compatibility)
    ocr = PaddleOCR(use_angle_cls=True, lang='en')
    result = ocr.ocr(pil_image)
    
    words = []
    confs = []
    for line in result or []:
        # PaddleOCR can return either a flat line entry or a nested batch result.
        if isinstance(line, list) and line and isinstance(line[0], list) and len(line) == 1 and isinstance(line[0][0], list):
            line = line[0]
        for word_info in line or []:
            if not isinstance(word_info, list) or len(word_info) < 2:
                continue
            text_part = word_info[1][0]
            conf = word_info[1][1]
            if text_part.strip():
                words.append(text_part)
                confs.append(conf)
    
    text = " ".join(words)
    mean_conf = round(sum(confs) / len(confs), 3) if confs else 0.0
    return text, mean_conf


def ocr_image(pil_image: Image.Image):
    """
    Run OCR on a PIL image.
    Tries Tesseract first; falls back to PaddleOCR if Tesseract not available.
    Returns: (extracted_text: str, mean_confidence: float 0-1)
    """
    try:
        return _ocr_tesseract(pil_image)
    except Exception as tesseract_error:
        # Tesseract failed, try PaddleOCR
        if PADDLE_AVAILABLE:
            try:
                return _ocr_paddle(pil_image)
            except Exception as paddle_error:
                raise RuntimeError(
                    f"Both OCR engines failed. "
                    f"Tesseract: {str(tesseract_error)[:100]}. "
                    f"PaddleOCR: {str(paddle_error)[:100]}"
                )
        else:
            raise RuntimeError(
                "OCR failed: Tesseract not installed and PaddleOCR not available. "
                "Install PaddleOCR with: pip install paddleocr paddlepaddle"
            )
#
# from paddleocr import PaddleOCR
# _paddle = PaddleOCR(use_angle_cls=True, lang="en")
#
# def ocr_image_paddle(pil_image: Image.Image):
#     import numpy as np
#     result = _paddle.ocr(np.array(pil_image), cls=True)
#     lines = result[0] if result else []
#     words = [line[1][0] for line in lines]
#     confs = [line[1][1] for line in lines]
#     text = " ".join(words)
#     mean_conf = sum(confs) / len(confs) if confs else 0.0
#     return text, round(mean_conf, 3)

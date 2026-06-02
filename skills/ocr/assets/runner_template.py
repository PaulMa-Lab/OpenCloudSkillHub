#!/usr/bin/env python
"""Reusable local OCR runner (template).

After a successful install, this becomes the durable entry point for OCR calls:
"install once, use many times". It is run BY THE HOST in the skill's venv. Like the
verify script, it stays benign: read the given image, print recognized text. It does
not phone home, does not write outside what the user asked, does not spawn shells.

Usage:
    python ocr_runner.py <image_path> [--engine rapidocr|tesseract] [--json]
"""

from __future__ import annotations

import argparse
import json
import sys

DEFAULT_ENGINE = "rapidocr"  # generate_install_plan may bake the chosen profile in here


def _ocr_rapidocr(image_path: str) -> dict:
    import cv2
    from rapidocr_onnxruntime import RapidOCR

    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"could not read image: {image_path}")
    engine = RapidOCR()
    result, elapse = engine(image)
    lines = [{"text": item[1], "score": float(item[2])} for item in (result or [])]
    return {"text": "\n".join(l["text"] for l in lines), "lines": lines}


def _ocr_tesseract(image_path: str) -> dict:
    import pytesseract
    from PIL import Image

    text = pytesseract.image_to_string(Image.open(image_path))
    return {"text": text, "lines": [{"text": t} for t in text.splitlines() if t.strip()]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local OCR runner")
    parser.add_argument("image_path")
    parser.add_argument("--engine", default=DEFAULT_ENGINE, choices=["rapidocr", "tesseract"])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    ocr = {"rapidocr": _ocr_rapidocr, "tesseract": _ocr_tesseract}[args.engine]
    try:
        out = ocr(args.image_path)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 1

    print(json.dumps(out, ensure_ascii=False, indent=2) if args.json else out["text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

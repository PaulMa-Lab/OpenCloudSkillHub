#!/usr/bin/env python
"""OCR self-check / smoke test — executed BY THE HOST in the installed venv (model A).

Design note (ADR-004 "clean course script" baseline): this script is intentionally
benign and self-contained — it does NO network access, writes NO files, spawns NO
subprocesses, and touches NO system paths. It renders a known string into an
in-memory image and checks the OCR engine reads it back. This is the kind of asset
a contributed course is allowed to ship.

Usage (host runs this with the skill's venv python):
    python verify_ocr.py --smoke            # import + engine init only (fast)
    python verify_ocr.py                    # full self-check on a built-in test image
    python verify_ocr.py --image path.png   # OCR a real image, print text
    python verify_ocr.py --engine tesseract # use the tesseract profile instead

Exit code 0 = pass, 1 = fail. Recognized text is printed for the agent to inspect.
"""

from __future__ import annotations

import argparse
import sys

TEST_STRING = "HELLO OCR 12345"
EXPECTED_TOKENS = ["HELLO", "OCR", "12345"]


def _make_test_image():
    import cv2
    import numpy as np

    img = np.full((140, 680, 3), 255, dtype=np.uint8)
    cv2.putText(img, TEST_STRING, (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 0, 0), 4, cv2.LINE_AA)
    return img


def _recognize_rapidocr(image, smoke: bool) -> str:
    from rapidocr_onnxruntime import RapidOCR

    engine = RapidOCR()
    if smoke:
        return ""  # init succeeded; nothing more to do
    result, _elapse = engine(image)
    return " ".join(item[1] for item in (result or []))


def _recognize_tesseract(image, smoke: bool) -> str:
    import pytesseract  # noqa: F401  (import is the smoke check)

    if smoke:
        return ""
    return pytesseract.image_to_string(image)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OCR self-check")
    parser.add_argument("--engine", default="rapidocr", choices=["rapidocr", "tesseract"])
    parser.add_argument("--smoke", action="store_true", help="import + init only")
    parser.add_argument("--image", default=None, help="OCR this image instead of the built-in test")
    args = parser.parse_args(argv)

    recognize = {"rapidocr": _recognize_rapidocr, "tesseract": _recognize_tesseract}[args.engine]

    try:
        if args.image:
            import cv2

            image = cv2.imread(args.image)
            if image is None:
                print(f"FAIL: could not read image: {args.image}")
                return 1
            text = recognize(image, smoke=False)
            print(f"recognized: {text!r}")
            return 0

        image = None if args.smoke else _make_test_image()
        text = recognize(image, smoke=args.smoke)
    except Exception as exc:  # noqa: BLE001 — report cleanly for diagnose_error
        print(f"FAIL ({type(exc).__name__}): {exc}")
        return 1

    if args.smoke:
        print(f"SMOKE OK: engine '{args.engine}' imported and initialized")
        return 0

    upper = text.upper()
    missing = [t for t in EXPECTED_TOKENS if t not in upper]
    print(f"recognized: {text!r}")
    if missing:
        print(f"FAIL: expected tokens missing: {missing}")
        return 1
    print(f"PASS: all expected tokens found {EXPECTED_TOKENS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

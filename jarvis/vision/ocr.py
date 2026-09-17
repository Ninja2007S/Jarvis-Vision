from __future__ import annotations

import cv2
import pytesseract


class OCR:

    def __init__(
        self,
        tesseract_path: str | None = None,
    ):

        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = (
                tesseract_path
            )

    def read(
        self,
        frame,
    ) -> str:

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY,
        )

        gray = cv2.resize(
            gray,
            None,
            fx=1.5,
            fy=1.5,
            interpolation=cv2.INTER_CUBIC,
        )

        gray = cv2.GaussianBlur(
            gray,
            (3, 3),
            0,
        )

        _, threshold = cv2.threshold(
            gray,
            0,
            255,
            cv2.THRESH_BINARY +
            cv2.THRESH_OTSU,
        )

        text = pytesseract.image_to_string(
            threshold
        )

        return text.strip()
"""OpenCV preprocessing for OCR input images."""

from typing import Any


def preprocess_for_ocr(image: Any) -> Any:
    """Deskew and binarize an image while preserving a usable OCR fallback."""
    try:
        import cv2
        import numpy as np

        array = np.asarray(image)
        gray = cv2.cvtColor(array, cv2.COLOR_RGB2GRAY) if len(array.shape) == 3 else array
        threshold = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        coordinates = np.column_stack(np.where(threshold < 255))
        if coordinates.size:
            angle = cv2.minAreaRect(coordinates)[-1]
            angle = -(90 + angle) if angle < -45 else -angle
            if abs(angle) > 0.5:
                height, width = threshold.shape[:2]
                matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
                threshold = cv2.warpAffine(
                    threshold,
                    matrix,
                    (width, height),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE,
                )
        return threshold
    except (ImportError, ValueError, TypeError):
        return image


"""
ocr.py

Prescription OCR for veterinary prescriptions.

Flow:
    image
      ↓
    OpenCV preprocessing
      ↓
    Tesseract OCR
      ↓
    extracted text
"""

import os
import re

import cv2
import pytesseract


# ============================================================
# WINDOWS TESSERACT LOCATION
# ============================================================

import os
import pytesseract

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

if os.path.exists(TESSERACT_PATH):

    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

    print("========================================")
    print("TESSERACT FOUND")
    print(TESSERACT_PATH)
    print("========================================")

else:

    print("========================================")
    print("TESSERACT NOT FOUND")
    print("Expected location:")
    print(TESSERACT_PATH)
    print("========================================")

# ============================================================
# CHECK TESSERACT
# ============================================================

def check_tesseract():

    try:

        version = pytesseract.get_tesseract_version()

        print("========================================")
        print("TESSERACT FOUND")
        print("Version:", version)
        print("========================================")

        return True

    except Exception as e:

        print("========================================")
        print("TESSERACT CHECK FAILED")
        print("========================================")
        print(e)
        print("========================================")

        return False


# ============================================================
# CLEAN OCR TEXT
# ============================================================

def clean_text(text):

    if not text:
        return ""

    # Remove form-feed
    text = text.replace("\x0c", " ")

    # Normalize spaces
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    # Remove excessive blank lines
    text = re.sub(
        r"\n\s*\n+",
        "\n",
        text
    )

    return text.strip()


# ============================================================
# PREPROCESS IMAGE
# ============================================================

def preprocess_image(image_path):

    image = cv2.imread(image_path)

    if image is None:

        raise ValueError(
            "Unable to read prescription image."
        )

    height, width = image.shape[:2]

    print(
        "Original image:",
        width,
        "x",
        height
    )

    # --------------------------------------------------------
    # Resize small images
    # --------------------------------------------------------

    if width < 1600:

        scale = 1600 / width

        image = cv2.resize(
            image,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC
        )

    # --------------------------------------------------------
    # Grayscale
    # --------------------------------------------------------

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    # --------------------------------------------------------
    # Contrast
    # --------------------------------------------------------

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )

    enhanced = clahe.apply(gray)

    # --------------------------------------------------------
    # Denoise
    # --------------------------------------------------------

    denoised = cv2.fastNlMeansDenoising(
        enhanced,
        None,
        10,
        7,
        21
    )

    # --------------------------------------------------------
    # Adaptive threshold
    # --------------------------------------------------------

    adaptive = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11
    )

    # --------------------------------------------------------
    # Otsu threshold
    # --------------------------------------------------------

    _, otsu = cv2.threshold(
        denoised,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    return [
        gray,
        enhanced,
        denoised,
        adaptive,
        otsu
    ]


# ============================================================
# RUN TESSERACT
# ============================================================

def run_tesseract(image, psm=6):

    config = f"--oem 3 --psm {psm}"

    try:

        text = pytesseract.image_to_string(
            image,
            lang="eng",
            config=config
        )

        return clean_text(text)

    except Exception as e:

        print(
            "TESSERACT ERROR:",
            e
        )

        return ""


# ============================================================
# EXTRACT TEXT
# ============================================================

def extract_text(image_path):

    print("\n")
    print("========================================")
    print("STARTING PRESCRIPTION OCR")
    print("========================================")
    print("Image:", image_path)

    # --------------------------------------------------------
    # Check file
    # --------------------------------------------------------

    if not image_path:

        print("OCR ERROR: No image path.")
        return ""

    if not os.path.exists(image_path):

        print(
            "OCR ERROR: File does not exist:",
            image_path
        )

        return ""

    # --------------------------------------------------------
    # Check Tesseract
    # --------------------------------------------------------

    if not check_tesseract():

        return ""

    try:

        # ----------------------------------------------------
        # Preprocess
        # ----------------------------------------------------

        images = preprocess_image(
            image_path
        )

        candidates = []

        # ----------------------------------------------------
        # Try multiple OCR modes
        # ----------------------------------------------------

        for index, image in enumerate(images):

            print(
                f"OCR image version {index + 1}"
            )

            for psm in [6, 11, 12]:

                print(
                    f"Trying PSM {psm}..."
                )

                text = run_tesseract(
                    image,
                    psm
                )

                if text:

                    print(
                        f"PSM {psm} extracted:"
                    )

                    print(text)

                    candidates.append(text)

        # ----------------------------------------------------
        # No result
        # ----------------------------------------------------

        if not candidates:

            print(
                "========================================"
            )

            print(
                "OCR RESULT: NO TEXT FOUND"
            )

            print(
                "========================================"
            )

            return ""

        # ----------------------------------------------------
        # Remove duplicates
        # ----------------------------------------------------

        unique = []

        for text in candidates:

            if text not in unique:

                unique.append(text)

        # ----------------------------------------------------
        # Select best result
        # ----------------------------------------------------

        unique.sort(
            key=lambda value: (
                sum(
                    character.isalpha()
                    for character in value
                ),
                len(value)
            ),
            reverse=True
        )

        result = unique[0].strip()

        # ----------------------------------------------------
        # Final result
        # ----------------------------------------------------

        print(
            "========================================"
        )

        print(
            "FINAL OCR TEXT"
        )

        print(
            "========================================"
        )

        print(result)

        print(
            "========================================"
        )

        return result

    except Exception as e:

        print(
            "========================================"
        )

        print(
            "OCR PROCESS FAILED"
        )

        print(
            "ERROR:",
            e
        )

        print(
            "========================================"
        )

        return ""


# ============================================================
# OCR CONFIDENCE
# ============================================================

def get_ocr_confidence(image_path):

    try:

        if not os.path.exists(image_path):

            return 0.0

        if not check_tesseract():

            return 0.0

        images = preprocess_image(
            image_path
        )

        best_confidence = 0.0

        for image in images:

            data = pytesseract.image_to_data(
                image,
                lang="eng",
                config="--oem 3 --psm 6",
                output_type=pytesseract.Output.DICT
            )

            values = []

            for confidence in data["conf"]:

                try:

                    value = float(
                        confidence
                    )

                    if value >= 0:

                        values.append(
                            value
                        )

                except (
                    ValueError,
                    TypeError
                ):

                    pass

            if values:

                confidence = (
                    sum(values)
                    / len(values)
                )

                best_confidence = max(
                    best_confidence,
                    confidence
                )

        return round(
            best_confidence,
            2
        )

    except Exception as e:

        print(
            "OCR CONFIDENCE ERROR:",
            e
        )

        return 0.0


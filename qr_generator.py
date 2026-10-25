"""
=============================================================
Smart Library Management System — qr_generator.py
Generates and manages QR code images for library books
=============================================================

Each book gets a PNG QR code whose payload is simply its
book_id string (e.g. "BK001").  This keeps QR images small
and scannable from long distances.

The images are stored in SmartLibrary/qr_codes/<book_id>.png
"""

import os
from PIL import Image, ImageDraw, ImageFont

try:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_H
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False
    print("[WARNING] qrcode library not installed — QR generation disabled.")
    print("          Run: pip install qrcode[pil]")

_HERE    = os.path.dirname(os.path.abspath(__file__))
QR_DIR   = os.path.join(_HERE, '..', 'qr_codes')


class QRGenerator:
    """
    Generates high-quality QR code PNG images for library books.

    Features
    --------
    • Error correction level H (30 % damage tolerance)
    • Caption label underneath with Book ID, Title, Author
    • Auto-creates output directory on first use
    """

    def __init__(self):
        os.makedirs(QR_DIR, exist_ok=True)

    def generate_qr(self, book_id: str, title: str, author: str) -> str:
        """
        Create and save a QR code image for the given book.

        The QR payload is the book_id alone so that the scanner
        can do a fast lookup in the database.

        Parameters
        ----------
        book_id : str   Library book identifier (e.g. "BK001")
        title   : str   Book title (used in the caption label)
        author  : str   Author name (used in the caption label)

        Returns
        -------
        str : Absolute path to the saved PNG file.
        """
        if not QRCODE_AVAILABLE:
            raise RuntimeError("qrcode library is not installed.")

        # ── Build the QR matrix ─────────────────────────────────────────────
        qr = qrcode.QRCode(
            version=2,
            error_correction=ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(book_id)
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

        # ── Append a text label below the QR code ───────────────────────────
        label_height = 70
        qr_w, qr_h   = qr_img.size
        combined      = Image.new("RGB", (qr_w, qr_h + label_height), "white")
        combined.paste(qr_img, (0, 0))

        draw = ImageDraw.Draw(combined)

        # Try to use a truetype font; fall back to default if unavailable
        try:
            font_large = ImageFont.truetype("arial.ttf", 14)
            font_small = ImageFont.truetype("arial.ttf", 11)
        except (IOError, OSError):
            font_large = ImageFont.load_default()
            font_small = font_large

        # Centre each line of text
        id_text    = f"ID: {book_id}"
        title_text = title[:35] + ("…" if len(title) > 35 else "")
        auth_text  = author[:35] + ("…" if len(author) > 35 else "")

        for i, (text, font) in enumerate(
            [(id_text, font_large), (title_text, font_small), (auth_text, font_small)]
        ):
            bbox   = draw.textbbox((0, 0), text, font=font)
            tw     = bbox[2] - bbox[0]
            tx     = (qr_w - tw) // 2
            ty     = qr_h + 5 + i * 20
            draw.text((tx, ty), text, fill="black", font=font)

        # ── Save ────────────────────────────────────────────────────────────
        out_path = os.path.join(QR_DIR, f"{book_id}.png")
        combined.save(out_path, "PNG", dpi=(300, 300))

        return os.path.abspath(out_path)

    def get_qr_path(self, book_id: str) -> str | None:
        """Return the path to an existing QR image, or None if absent."""
        path = os.path.join(QR_DIR, f"{book_id}.png")
        return os.path.abspath(path) if os.path.isfile(path) else None

    def generate_all(self, books: list) -> dict:
        """
        Batch-generate QR codes for a list of book dicts.

        Parameters
        ----------
        books : list of dicts with keys 'book_id', 'title', 'author'

        Returns
        -------
        dict : {book_id: qr_path or error_message}
        """
        results = {}
        for book in books:
            bid = book.get('book_id', '')
            try:
                path = self.generate_qr(bid, book.get('title', ''), book.get('author', ''))
                results[bid] = path
            except Exception as exc:
                results[bid] = f"ERROR: {exc}"
        return results

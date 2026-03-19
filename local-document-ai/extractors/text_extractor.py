"""
Text extraction module - PDF and image OCR support.
Replaces SAP Document AI's document ingestion layer.
"""
import os
import io
from typing import Optional


class TextExtractor:
    """Extracts raw text from PDF files and images."""

    @staticmethod
    def extract_from_pdf(file_path: str) -> str:
        """Extract text from a PDF file using pdfplumber."""
        import pdfplumber

        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)

    @staticmethod
    def extract_from_pdf_bytes(file_bytes: bytes) -> str:
        """Extract text from PDF bytes."""
        import pdfplumber

        text_parts = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)

    @staticmethod
    def extract_tables_from_pdf(file_path: str) -> list:
        """Extract tables from a PDF file."""
        import pdfplumber

        all_tables = []
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                for table in tables:
                    all_tables.append({
                        "page": page_num + 1,
                        "rows": table
                    })
        return all_tables

    @staticmethod
    def extract_tables_from_pdf_bytes(file_bytes: bytes) -> list:
        """Extract tables from PDF bytes."""
        import pdfplumber

        all_tables = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                for table in tables:
                    all_tables.append({
                        "page": page_num + 1,
                        "rows": table
                    })
        return all_tables

    @staticmethod
    def extract_from_image(file_path: str, lang: str = "eng+tur") -> str:
        """Extract text from an image using Tesseract OCR."""
        import pytesseract
        from PIL import Image

        image = Image.open(file_path)
        return pytesseract.image_to_string(image, lang=lang)

    @staticmethod
    def extract_from_image_bytes(file_bytes: bytes, lang: str = "eng+tur") -> str:
        """Extract text from image bytes using Tesseract OCR."""
        import pytesseract
        from PIL import Image

        image = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(image, lang=lang)

    @classmethod
    def extract(cls, file_path: str, lang: str = "eng+tur") -> dict:
        """
        Auto-detect file type and extract text + tables.
        Returns dict with 'text', 'tables', and 'source' keys.
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            text = cls.extract_from_pdf(file_path)
            tables = cls.extract_tables_from_pdf(file_path)
            return {"text": text, "tables": tables, "source": "pdf"}
        elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"):
            text = cls.extract_from_image(file_path, lang=lang)
            return {"text": text, "tables": [], "source": "ocr"}
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    @classmethod
    def extract_from_bytes(cls, file_bytes: bytes, filename: str, lang: str = "eng+tur") -> dict:
        """Extract from raw bytes with filename hint."""
        ext = os.path.splitext(filename)[1].lower()

        if ext == ".pdf":
            text = cls.extract_from_pdf_bytes(file_bytes)
            tables = cls.extract_tables_from_pdf_bytes(file_bytes)
            return {"text": text, "tables": tables, "source": "pdf"}
        elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"):
            text = cls.extract_from_image_bytes(file_bytes, lang=lang)
            return {"text": text, "tables": [], "source": "ocr"}
        else:
            raise ValueError(f"Unsupported file type: {ext}")

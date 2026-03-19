"""
Base document field extractor with common utilities.
"""
import re
from datetime import datetime
from typing import Optional


class BaseDocumentExtractor:
    """Base class for document field extraction."""

    # Common date patterns (TR and EN)
    DATE_PATTERNS = [
        # DD.MM.YYYY, DD/MM/YYYY, DD-MM-YYYY
        r'(\d{1,2})[./\-](\d{1,2})[./\-](\d{4})',
        # YYYY-MM-DD
        r'(\d{4})[./\-](\d{1,2})[./\-](\d{1,2})',
        # DD Month YYYY (Turkish)
        r'(\d{1,2})\s+(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+(\d{4})',
        # DD Month YYYY (English)
        r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})',
    ]

    # Currency patterns
    CURRENCY_PATTERNS = [
        r'([\d.,]+)\s*(TL|TRY|USD|EUR|GBP|₺|\$|€|£)',
        r'(TL|TRY|USD|EUR|GBP|₺|\$|€|£)\s*([\d.,]+)',
    ]

    # Amount patterns
    AMOUNT_PATTERN = r'[\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?'

    @staticmethod
    def clean_text(text: str) -> str:
        """Normalize whitespace in extracted text."""
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def find_pattern(text: str, pattern: str, group: int = 1, flags: int = re.IGNORECASE) -> Optional[str]:
        """Find first match of a regex pattern."""
        match = re.search(pattern, text, flags)
        if match:
            return match.group(group).strip()
        return None

    @staticmethod
    def find_all_patterns(text: str, pattern: str, flags: int = re.IGNORECASE) -> list:
        """Find all matches of a regex pattern."""
        return re.findall(pattern, text, flags)

    @classmethod
    def extract_dates(cls, text: str) -> list:
        """Extract all dates found in text."""
        dates = []
        for pattern in cls.DATE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                dates.append(match.group(0))
        return dates

    @classmethod
    def extract_amounts(cls, text: str) -> list:
        """Extract monetary amounts from text."""
        amounts = []
        for pattern in cls.CURRENCY_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                amounts.append(match.group(0).strip())
        return amounts

    @staticmethod
    def parse_amount(amount_str: str) -> Optional[float]:
        """Parse a string amount to float. Handles Turkish (1.234,56) and English (1,234.56) formats."""
        if not amount_str:
            return None
        cleaned = re.sub(r'[^\d.,]', '', amount_str)
        if not cleaned:
            return None

        # Turkish format: 1.234,56
        if ',' in cleaned and '.' in cleaned:
            if cleaned.rindex(',') > cleaned.rindex('.'):
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        elif ',' in cleaned:
            # Could be Turkish decimal or English thousands
            parts = cleaned.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')

        try:
            return float(cleaned)
        except ValueError:
            return None

    @staticmethod
    def extract_tax_id(text: str) -> Optional[str]:
        """Extract Turkish tax ID (Vergi No) or TCKN."""
        # Vergi Kimlik No (10 digits)
        vkn = re.search(r'(?:V\.?K\.?N\.?|Vergi\s*(?:Kimlik)?\s*(?:No|Numarası))\s*[:\s]*(\d{10})', text, re.IGNORECASE)
        if vkn:
            return vkn.group(1)

        # TCKN (11 digits)
        tckn = re.search(r'(?:T\.?C\.?\s*(?:Kimlik)?\s*(?:No|Numarası))\s*[:\s]*(\d{11})', text, re.IGNORECASE)
        if tckn:
            return tckn.group(1)

        return None

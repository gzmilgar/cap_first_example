"""
Payment Advice (Ödeme Bildirimi) field extractor.
Mimics SAP Document AI payment advice extraction.
"""
import re
from .base_extractor import BaseDocumentExtractor


class PaymentAdviceExtractor(BaseDocumentExtractor):
    """Extracts structured fields from payment advice documents."""

    DOCUMENT_TYPE = "paymentAdvice"

    def extract_header(self, text: str) -> dict:
        header = {
            "documentType": self.DOCUMENT_TYPE,
            "paymentAdviceNumber": None,
            "paymentDate": None,
            "payerName": None,
            "payeeName": None,
            "bankName": None,
            "iban": None,
            "currency": None,
            "totalAmount": None,
            "paymentMethod": None,
        }

        # Payment advice number
        pa_patterns = [
            r'(?:Ödeme\s*(?:Bildirimi)?\s*(?:No|Numarası))\s*[:\s]*([A-Z0-9\-/]+)',
            r'(?:Payment\s*(?:Advice)?\s*(?:No|Number|#))\s*[:\s]*([A-Z0-9\-/]+)',
            r'(?:Remittance\s*(?:Advice)?\s*(?:No|Number))\s*[:\s]*([A-Z0-9\-/]+)',
        ]
        for p in pa_patterns:
            val = self.find_pattern(text, p)
            if val:
                header["paymentAdviceNumber"] = val
                break

        # Payment date
        date_patterns = [
            r'(?:Ödeme\s*Tarihi|Payment\s*Date)\s*[:\s]*(.+?)(?:\n|$)',
        ]
        for p in date_patterns:
            val = self.find_pattern(text, p)
            if val:
                header["paymentDate"] = val.strip()
                break
        if not header["paymentDate"]:
            dates = self.extract_dates(text)
            if dates:
                header["paymentDate"] = dates[0]

        # Payer
        for p in [r'(?:Ödeyen|Payer|From)\s*[:\s]*(.+?)(?:\n|$)']:
            val = self.find_pattern(text, p)
            if val:
                header["payerName"] = self.clean_text(val)
                break

        # Payee
        for p in [r'(?:Alıcı|Payee|To|Lehtar)\s*[:\s]*(.+?)(?:\n|$)']:
            val = self.find_pattern(text, p)
            if val:
                header["payeeName"] = self.clean_text(val)
                break

        # IBAN
        iban = re.search(r'(?:IBAN\s*[:\s]*)?(TR\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2})', text, re.IGNORECASE)
        if not iban:
            iban = re.search(r'(?:IBAN\s*[:\s]*)?([A-Z]{2}\d{2}[\s]?[\dA-Z\s]{10,30})', text, re.IGNORECASE)
        if iban:
            header["iban"] = re.sub(r'\s+', '', iban.group(1))

        # Bank
        for p in [r'(?:Banka|Bank)\s*[:\s]*(.+?)(?:\n|$)']:
            val = self.find_pattern(text, p)
            if val:
                header["bankName"] = self.clean_text(val)
                break

        # Currency
        for pattern, curr in [(r'(?:TL|TRY|₺)', 'TRY'), (r'(?:USD|\$)', 'USD'), (r'(?:EUR|€)', 'EUR')]:
            if re.search(pattern, text, re.IGNORECASE):
                header["currency"] = curr
                break

        # Total amount
        for p in [r'(?:Toplam|Ödeme\s*Tutarı|Total\s*Amount|Payment\s*Amount)\s*[:\s]*([\d.,]+)']:
            val = self.find_pattern(text, p)
            if val:
                header["totalAmount"] = self.parse_amount(val)
                break

        # Payment method
        for p in [r'(?:Ödeme\s*(?:Şekli|Yöntemi)|Payment\s*Method)\s*[:\s]*(.+?)(?:\n|$)']:
            val = self.find_pattern(text, p)
            if val:
                header["paymentMethod"] = self.clean_text(val)
                break

        return header

    def extract_line_items(self, text: str, tables: list = None) -> list:
        """Extract payment line items (invoice references being paid)."""
        items = []
        if tables:
            for table_data in tables:
                rows = table_data.get("rows", [])
                if len(rows) < 2:
                    continue
                for row in rows[1:]:
                    if not row or all(c is None or str(c).strip() == '' for c in row):
                        continue
                    item = {}
                    for i, cell in enumerate(row):
                        if cell:
                            item[f"col_{i}"] = str(cell).strip()
                    if item:
                        items.append(item)
        return items

    def extract(self, text: str, tables: list = None) -> dict:
        header = self.extract_header(text)
        line_items = self.extract_line_items(text, tables)

        header_fields = [v for k, v in header.items() if k != "documentType" and v is not None]
        confidence = min(len(header_fields) / 8.0, 1.0)

        return {
            "status": "DONE",
            "documentType": self.DOCUMENT_TYPE,
            "confidence": round(confidence, 2),
            "headerFields": header,
            "lineItems": line_items,
            "lineItemCount": len(line_items),
        }

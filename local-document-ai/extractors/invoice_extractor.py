"""
Invoice (Fatura) field extractor.
Mimics SAP Document AI invoice extraction capabilities.
"""
import re
from typing import Optional
from .base_extractor import BaseDocumentExtractor


class InvoiceExtractor(BaseDocumentExtractor):
    """
    Extracts structured fields from invoice documents.

    Supported fields (SAP Document AI compatible):
    - Header: invoice number, date, due date, vendor, customer, currency, totals, tax
    - Line items: description, quantity, unit price, amount, tax rate
    """

    DOCUMENT_TYPE = "invoice"

    # --- Header field patterns ---

    INVOICE_NUMBER_PATTERNS = [
        r'(?:Fatura\s*(?:No|Numarası|Seri(?:\s*No)?))\s*[:\s]*([A-Z0-9\-/]+)',
        r'(?:Invoice\s*(?:No|Number|#))\s*[:\s]*([A-Z0-9\-/]+)',
        r'(?:Belge\s*(?:No|Numarası))\s*[:\s]*([A-Z0-9\-/]+)',
        r'(?:Fiş\s*No)\s*[:\s]*([A-Z0-9\-/]+)',
    ]

    VENDOR_NAME_PATTERNS = [
        r'(?:Satıcı|Tedarikçi|Firma)\s*[:\s]*(.+?)(?:\n|$)',
        r'(?:Vendor|Supplier|Seller)\s*[:\s]*(.+?)(?:\n|$)',
    ]

    CUSTOMER_NAME_PATTERNS = [
        r'(?:Müşteri|Alıcı)\s*[:\s]*(.+?)(?:\n|$)',
        r'(?:Customer|Buyer|Bill\s*To)\s*[:\s]*(.+?)(?:\n|$)',
    ]

    TOTAL_PATTERNS = [
        r'(?:Genel\s*Toplam|Toplam\s*Tutar|Net\s*Toplam)\s*[:\s]*([\d.,]+)',
        r'(?:Grand\s*Total|Total\s*Amount|Net\s*Total)\s*[:\s]*([\d.,]+)',
        r'(?:TOPLAM)\s*[:\s]*([\d.,]+)',
    ]

    SUBTOTAL_PATTERNS = [
        r'(?:Ara\s*Toplam|Mal\s*Hizmet\s*Toplamı)\s*[:\s]*([\d.,]+)',
        r'(?:Sub\s*Total|Subtotal)\s*[:\s]*([\d.,]+)',
    ]

    TAX_AMOUNT_PATTERNS = [
        r'(?:KDV\s*(?:Tutarı)?|Vergi\s*Tutarı)\s*[:\s]*([\d.,]+)',
        r'(?:Tax\s*Amount|VAT\s*Amount|Tax)\s*[:\s]*([\d.,]+)',
    ]

    TAX_RATE_PATTERNS = [
        r'(?:KDV\s*(?:Oranı)?|Vergi\s*Oranı)\s*[:\s]*%?\s*(\d+)',
        r'(?:Tax\s*Rate|VAT\s*Rate)\s*[:\s]*%?\s*(\d+)',
    ]

    CURRENCY_DETECT_PATTERNS = [
        (r'(?:TL|TRY|₺)', 'TRY'),
        (r'(?:USD|\$)', 'USD'),
        (r'(?:EUR|€)', 'EUR'),
        (r'(?:GBP|£)', 'GBP'),
    ]

    INVOICE_DATE_PATTERNS = [
        r'(?:Fatura\s*Tarihi|Düzenleme\s*Tarihi)\s*[:\s]*(.+?)(?:\n|$)',
        r'(?:Invoice\s*Date|Date)\s*[:\s]*(.+?)(?:\n|$)',
    ]

    DUE_DATE_PATTERNS = [
        r'(?:Vade\s*Tarihi|Son\s*Ödeme)\s*[:\s]*(.+?)(?:\n|$)',
        r'(?:Due\s*Date|Payment\s*Date)\s*[:\s]*(.+?)(?:\n|$)',
    ]

    # --- Line item patterns ---

    LINE_ITEM_HEADER_KEYWORDS = [
        'açıklama', 'description', 'ürün', 'product', 'malzeme', 'material',
        'miktar', 'quantity', 'adet', 'birim', 'unit',
        'fiyat', 'price', 'tutar', 'amount',
    ]

    def extract_header(self, text: str) -> dict:
        """Extract invoice header fields."""
        header = {
            "documentType": self.DOCUMENT_TYPE,
            "invoiceNumber": None,
            "invoiceDate": None,
            "dueDate": None,
            "vendorName": None,
            "vendorTaxId": None,
            "customerName": None,
            "customerTaxId": None,
            "currency": None,
            "subtotal": None,
            "taxAmount": None,
            "taxRate": None,
            "totalAmount": None,
        }

        # Invoice number
        for pattern in self.INVOICE_NUMBER_PATTERNS:
            val = self.find_pattern(text, pattern)
            if val:
                header["invoiceNumber"] = val
                break

        # Invoice date
        for pattern in self.INVOICE_DATE_PATTERNS:
            val = self.find_pattern(text, pattern)
            if val:
                header["invoiceDate"] = val.strip()
                break
        if not header["invoiceDate"]:
            dates = self.extract_dates(text)
            if dates:
                header["invoiceDate"] = dates[0]

        # Due date
        for pattern in self.DUE_DATE_PATTERNS:
            val = self.find_pattern(text, pattern)
            if val:
                header["dueDate"] = val.strip()
                break

        # Vendor
        for pattern in self.VENDOR_NAME_PATTERNS:
            val = self.find_pattern(text, pattern)
            if val:
                header["vendorName"] = self.clean_text(val)
                break

        # Customer
        for pattern in self.CUSTOMER_NAME_PATTERNS:
            val = self.find_pattern(text, pattern)
            if val:
                header["customerName"] = self.clean_text(val)
                break

        # Tax IDs - look for two separate tax IDs
        tax_ids = re.findall(r'(?:V\.?K\.?N\.?|Vergi\s*(?:Kimlik)?\s*(?:No|Numarası))\s*[:\s]*(\d{10})', text, re.IGNORECASE)
        if len(tax_ids) >= 2:
            header["vendorTaxId"] = tax_ids[0]
            header["customerTaxId"] = tax_ids[1]
        elif len(tax_ids) == 1:
            header["vendorTaxId"] = tax_ids[0]

        # Currency
        for pattern, currency in self.CURRENCY_DETECT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                header["currency"] = currency
                break

        # Amounts
        for pattern in self.TOTAL_PATTERNS:
            val = self.find_pattern(text, pattern)
            if val:
                header["totalAmount"] = self.parse_amount(val)
                break

        for pattern in self.SUBTOTAL_PATTERNS:
            val = self.find_pattern(text, pattern)
            if val:
                header["subtotal"] = self.parse_amount(val)
                break

        for pattern in self.TAX_AMOUNT_PATTERNS:
            val = self.find_pattern(text, pattern)
            if val:
                header["taxAmount"] = self.parse_amount(val)
                break

        for pattern in self.TAX_RATE_PATTERNS:
            val = self.find_pattern(text, pattern)
            if val:
                header["taxRate"] = int(val)
                break

        return header

    def extract_line_items(self, text: str, tables: list = None) -> list:
        """
        Extract invoice line items.
        Tries table extraction first, falls back to text-based parsing.
        """
        items = []

        # Try from tables first
        if tables:
            items = self._extract_items_from_tables(tables)

        # Fallback: text-based line item parsing
        if not items:
            items = self._extract_items_from_text(text)

        return items

    def _extract_items_from_tables(self, tables: list) -> list:
        """Extract line items from PDF table data."""
        items = []
        for table_data in tables:
            rows = table_data.get("rows", [])
            if len(rows) < 2:
                continue

            header_row = rows[0]
            if not header_row:
                continue

            # Try to identify column indices
            col_map = self._map_table_columns(header_row)
            if not col_map:
                continue

            for row in rows[1:]:
                if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                    continue
                item = self._parse_table_row(row, col_map)
                if item.get("description"):
                    items.append(item)

        return items

    def _map_table_columns(self, header_row: list) -> dict:
        """Map table column headers to field names."""
        col_map = {}
        desc_keywords = {'açıklama', 'description', 'ürün', 'product', 'malzeme', 'mal/hizmet'}
        qty_keywords = {'miktar', 'quantity', 'adet', 'qty'}
        price_keywords = {'birim fiyat', 'unit price', 'fiyat', 'price'}
        amount_keywords = {'tutar', 'amount', 'toplam', 'total'}
        tax_keywords = {'kdv', 'tax', 'vat', 'vergi'}

        for i, col in enumerate(header_row):
            if col is None:
                continue
            col_lower = str(col).lower().strip()
            if any(k in col_lower for k in desc_keywords):
                col_map['description'] = i
            elif any(k in col_lower for k in qty_keywords):
                col_map['quantity'] = i
            elif any(k in col_lower for k in price_keywords):
                col_map['unitPrice'] = i
            elif any(k in col_lower for k in amount_keywords):
                col_map['amount'] = i
            elif any(k in col_lower for k in tax_keywords):
                col_map['taxRate'] = i

        return col_map if 'description' in col_map else {}

    def _parse_table_row(self, row: list, col_map: dict) -> dict:
        """Parse a single table row into a line item."""
        item = {
            "description": None,
            "quantity": None,
            "unitPrice": None,
            "amount": None,
            "taxRate": None,
        }

        for field, idx in col_map.items():
            if idx < len(row) and row[idx] is not None:
                val = str(row[idx]).strip()
                if field == 'description':
                    item[field] = val
                elif field in ('quantity', 'unitPrice', 'amount'):
                    item[field] = self.parse_amount(val)
                elif field == 'taxRate':
                    rate = re.search(r'(\d+)', val)
                    if rate:
                        item[field] = int(rate.group(1))

        return item

    def _extract_items_from_text(self, text: str) -> list:
        """Fallback: extract line items from raw text using patterns."""
        items = []
        lines = text.split('\n')

        # Look for numbered line items
        item_pattern = re.compile(
            r'(\d+)\s+'  # line number
            r'(.+?)\s+'  # description
            r'(\d+(?:[.,]\d+)?)\s+'  # quantity
            r'([\d.,]+)\s+'  # unit price
            r'([\d.,]+)',  # amount
            re.IGNORECASE
        )

        for line in lines:
            match = item_pattern.search(line)
            if match:
                items.append({
                    "lineNumber": int(match.group(1)),
                    "description": match.group(2).strip(),
                    "quantity": self.parse_amount(match.group(3)),
                    "unitPrice": self.parse_amount(match.group(4)),
                    "amount": self.parse_amount(match.group(5)),
                })

        return items

    def extract(self, text: str, tables: list = None) -> dict:
        """
        Full invoice extraction - returns SAP Document AI compatible structure.
        """
        header = self.extract_header(text)
        line_items = self.extract_line_items(text, tables)

        # Calculate confidence based on how many fields were extracted
        header_fields = [v for k, v in header.items() if k != "documentType" and v is not None]
        confidence = min(len(header_fields) / 10.0, 1.0)

        return {
            "status": "DONE",
            "documentType": self.DOCUMENT_TYPE,
            "confidence": round(confidence, 2),
            "headerFields": header,
            "lineItems": line_items,
            "lineItemCount": len(line_items),
        }

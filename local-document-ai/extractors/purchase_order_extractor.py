"""
Purchase Order (Satınalma Siparişi) field extractor.
Mimics SAP Document AI purchase order extraction.
"""
import re
from .base_extractor import BaseDocumentExtractor


class PurchaseOrderExtractor(BaseDocumentExtractor):
    """Extracts structured fields from purchase order documents."""

    DOCUMENT_TYPE = "purchaseOrder"

    PO_NUMBER_PATTERNS = [
        r'(?:Sipariş\s*(?:No|Numarası))\s*[:\s]*([A-Z0-9\-/]+)',
        r'(?:Purchase\s*Order\s*(?:No|Number|#)|PO\s*(?:No|Number|#))\s*[:\s]*([A-Z0-9\-/]+)',
        r'(?:Satınalma\s*(?:Sipariş)?\s*(?:No|Numarası))\s*[:\s]*([A-Z0-9\-/]+)',
    ]

    PO_DATE_PATTERNS = [
        r'(?:Sipariş\s*Tarihi|Order\s*Date)\s*[:\s]*(.+?)(?:\n|$)',
    ]

    DELIVERY_DATE_PATTERNS = [
        r'(?:Teslimat\s*Tarihi|Teslim\s*Tarihi|Delivery\s*Date)\s*[:\s]*(.+?)(?:\n|$)',
    ]

    BUYER_PATTERNS = [
        r'(?:Alıcı|Buyer|Satın\s*Alan)\s*[:\s]*(.+?)(?:\n|$)',
    ]

    SUPPLIER_PATTERNS = [
        r'(?:Tedarikçi|Satıcı|Supplier|Vendor)\s*[:\s]*(.+?)(?:\n|$)',
    ]

    SHIP_TO_PATTERNS = [
        r'(?:Sevk\s*Adresi|Teslimat\s*Adresi|Ship\s*To|Delivery\s*Address)\s*[:\s]*(.+?)(?:\n|$)',
    ]

    PAYMENT_TERMS_PATTERNS = [
        r'(?:Ödeme\s*(?:Koşulları|Şartları)|Payment\s*Terms)\s*[:\s]*(.+?)(?:\n|$)',
    ]

    def extract_header(self, text: str) -> dict:
        """Extract PO header fields."""
        header = {
            "documentType": self.DOCUMENT_TYPE,
            "poNumber": None,
            "poDate": None,
            "deliveryDate": None,
            "buyerName": None,
            "supplierName": None,
            "shipToAddress": None,
            "paymentTerms": None,
            "currency": None,
            "totalAmount": None,
        }

        for patterns, field in [
            (self.PO_NUMBER_PATTERNS, "poNumber"),
            (self.PO_DATE_PATTERNS, "poDate"),
            (self.DELIVERY_DATE_PATTERNS, "deliveryDate"),
            (self.BUYER_PATTERNS, "buyerName"),
            (self.SUPPLIER_PATTERNS, "supplierName"),
            (self.SHIP_TO_PATTERNS, "shipToAddress"),
            (self.PAYMENT_TERMS_PATTERNS, "paymentTerms"),
        ]:
            for pattern in patterns:
                val = self.find_pattern(text, pattern)
                if val:
                    header[field] = self.clean_text(val)
                    break

        if not header["poDate"]:
            dates = self.extract_dates(text)
            if dates:
                header["poDate"] = dates[0]

        # Currency
        currency_map = [
            (r'(?:TL|TRY|₺)', 'TRY'), (r'(?:USD|\$)', 'USD'),
            (r'(?:EUR|€)', 'EUR'), (r'(?:GBP|£)', 'GBP'),
        ]
        for pattern, currency in currency_map:
            if re.search(pattern, text, re.IGNORECASE):
                header["currency"] = currency
                break

        # Total
        total_patterns = [
            r'(?:Genel\s*Toplam|Toplam\s*Tutar|Grand\s*Total|Total)\s*[:\s]*([\d.,]+)',
        ]
        for pattern in total_patterns:
            val = self.find_pattern(text, pattern)
            if val:
                header["totalAmount"] = self.parse_amount(val)
                break

        return header

    def extract_line_items(self, text: str, tables: list = None) -> list:
        """Extract PO line items."""
        items = []

        if tables:
            for table_data in tables:
                rows = table_data.get("rows", [])
                if len(rows) < 2:
                    continue
                header_row = rows[0]
                col_map = self._map_columns(header_row)
                if not col_map:
                    continue
                for row in rows[1:]:
                    if not row or all(c is None or str(c).strip() == '' for c in row):
                        continue
                    item = {}
                    for field, idx in col_map.items():
                        if idx < len(row) and row[idx] is not None:
                            val = str(row[idx]).strip()
                            if field in ('quantity', 'unitPrice', 'amount'):
                                item[field] = self.parse_amount(val)
                            else:
                                item[field] = val
                    if item.get("description") or item.get("materialNumber"):
                        items.append(item)

        return items

    def _map_columns(self, header_row: list) -> dict:
        col_map = {}
        mappings = {
            'description': {'açıklama', 'description', 'ürün', 'malzeme', 'material'},
            'materialNumber': {'malzeme no', 'material no', 'part no', 'parça no'},
            'quantity': {'miktar', 'quantity', 'adet', 'qty'},
            'unit': {'birim', 'unit', 'uom'},
            'unitPrice': {'birim fiyat', 'unit price', 'fiyat'},
            'amount': {'tutar', 'amount', 'toplam'},
        }
        for i, col in enumerate(header_row):
            if col is None:
                continue
            col_lower = str(col).lower().strip()
            for field, keywords in mappings.items():
                if any(k in col_lower for k in keywords):
                    col_map[field] = i
                    break
        return col_map

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

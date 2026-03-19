"""
Template Manager - Extraction rule templates.
A template defines HOW to extract each field defined in a schema.
Each template is linked to a schema and contains extraction rules per field.

Template structure:
{
    "id": "invoice_tr_standard",
    "name": "Standart TR Fatura",
    "schemaId": "invoice_default",
    "description": "Turkiye standart e-fatura formati",
    "headerRules": {
        "invoiceNumber": {
            "method": "regex",
            "patterns": ["Fatura\\s*No\\s*[:\\s]*([A-Z0-9\\-/]+)"],
            "postProcess": "trim"
        },
        "totalAmount": {
            "method": "regex",
            "patterns": ["Genel\\s*Toplam\\s*[:\\s]*([\\d.,]+)"],
            "postProcess": "parseAmount"
        }
    },
    "lineItemRules": {
        "method": "table",           # "table" or "regex"
        "tableKeywords": {           # column header keywords for table method
            "description": ["aciklama", "urun"],
            "quantity": ["miktar", "adet"],
            ...
        },
        "regexPattern": null         # fallback regex for line items
    }
}
"""
import json
import os
import uuid
from datetime import datetime
from typing import Optional


TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "templates")


# Post-processing functions available
POST_PROCESS_TYPES = ["trim", "uppercase", "lowercase", "parseAmount", "parseDate", "parseInteger", "parseIBAN"]


DEFAULT_TEMPLATES = [
    {
        "id": "invoice_tr_standard",
        "name": "Standart TR Fatura",
        "schemaId": "invoice_default",
        "description": "Turkiye standart e-fatura formati icin kurallar",
        "builtIn": True,
        "headerRules": {
            "invoiceNumber": {
                "method": "regex",
                "patterns": [
                    "(?:Fatura\\s*(?:No|Numarası|Seri(?:\\s*No)?))\\s*[:\\s]*([A-Z0-9\\-/]+)",
                    "(?:Invoice\\s*(?:No|Number|#))\\s*[:\\s]*([A-Z0-9\\-/]+)"
                ],
                "postProcess": "trim"
            },
            "invoiceDate": {
                "method": "regex",
                "patterns": [
                    "(?:Fatura\\s*Tarihi|Düzenleme\\s*Tarihi)\\s*[:\\s]*(.+?)(?:\\n|$)",
                    "(?:Invoice\\s*Date|Date)\\s*[:\\s]*(.+?)(?:\\n|$)"
                ],
                "postProcess": "parseDate"
            },
            "dueDate": {
                "method": "regex",
                "patterns": [
                    "(?:Vade\\s*Tarihi|Son\\s*Ödeme)\\s*[:\\s]*(.+?)(?:\\n|$)",
                    "(?:Due\\s*Date)\\s*[:\\s]*(.+?)(?:\\n|$)"
                ],
                "postProcess": "parseDate"
            },
            "vendorName": {
                "method": "regex",
                "patterns": [
                    "(?:Satıcı|Tedarikçi|Firma)\\s*[:\\s]*(.+?)(?:\\n|$)",
                    "(?:Vendor|Supplier|Seller)\\s*[:\\s]*(.+?)(?:\\n|$)"
                ],
                "postProcess": "trim"
            },
            "vendorTaxId": {
                "method": "regex",
                "patterns": [
                    "(?:V\\.?K\\.?N\\.?|Vergi\\s*(?:Kimlik)?\\s*(?:No|Numarası))\\s*[:\\s]*(\\d{10})"
                ],
                "postProcess": "trim",
                "matchIndex": 0
            },
            "customerName": {
                "method": "regex",
                "patterns": [
                    "(?:Müşteri|Alıcı)\\s*[:\\s]*(.+?)(?:\\n|$)",
                    "(?:Customer|Buyer|Bill\\s*To)\\s*[:\\s]*(.+?)(?:\\n|$)"
                ],
                "postProcess": "trim"
            },
            "customerTaxId": {
                "method": "regex",
                "patterns": [
                    "(?:V\\.?K\\.?N\\.?|Vergi\\s*(?:Kimlik)?\\s*(?:No|Numarası))\\s*[:\\s]*(\\d{10})"
                ],
                "postProcess": "trim",
                "matchIndex": 1
            },
            "currency": {
                "method": "keyword",
                "keywords": {
                    "TRY": ["TL", "TRY", "₺"],
                    "USD": ["USD", "$"],
                    "EUR": ["EUR", "€"],
                    "GBP": ["GBP", "£"]
                }
            },
            "subtotal": {
                "method": "regex",
                "patterns": [
                    "(?:Ara\\s*Toplam|Mal\\s*Hizmet\\s*Toplamı|Sub\\s*Total)\\s*[:\\s]*([\\d.,]+)"
                ],
                "postProcess": "parseAmount"
            },
            "taxRate": {
                "method": "regex",
                "patterns": [
                    "(?:KDV\\s*(?:Oranı)?|Vergi\\s*Oranı|Tax\\s*Rate|VAT\\s*Rate)\\s*[:\\s]*%?\\s*(\\d+)"
                ],
                "postProcess": "parseInteger"
            },
            "taxAmount": {
                "method": "regex",
                "patterns": [
                    "(?:KDV\\s*(?:Tutarı)?|Vergi\\s*Tutarı|Tax\\s*Amount|VAT\\s*Amount)\\s*[:\\s]*([\\d.,]+)"
                ],
                "postProcess": "parseAmount"
            },
            "totalAmount": {
                "method": "regex",
                "patterns": [
                    "(?:Genel\\s*Toplam|Toplam\\s*Tutar|Net\\s*Toplam)\\s*[:\\s]*([\\d.,]+)",
                    "(?:Grand\\s*Total|Total\\s*Amount|Net\\s*Total)\\s*[:\\s]*([\\d.,]+)"
                ],
                "postProcess": "parseAmount"
            }
        },
        "lineItemRules": {
            "method": "table",
            "tableKeywords": {
                "description": ["açıklama", "description", "ürün", "product", "malzeme", "mal/hizmet"],
                "quantity": ["miktar", "quantity", "adet", "qty"],
                "unitPrice": ["birim fiyat", "unit price", "fiyat", "price"],
                "amount": ["tutar", "amount", "toplam", "total"],
                "taxRate": ["kdv", "tax", "vat", "vergi"]
            },
            "regexPattern": "(\\d+)\\s+(.+?)\\s+(\\d+(?:[.,]\\d+)?)\\s+([\\d.,]+)\\s+([\\d.,]+)",
            "regexGroups": ["lineNumber", "description", "quantity", "unitPrice", "amount"]
        }
    },
    {
        "id": "po_tr_standard",
        "name": "Standart TR Satin Alma Siparisi",
        "schemaId": "purchase_order_default",
        "description": "Turkiye standart satin alma siparisi formati",
        "builtIn": True,
        "headerRules": {
            "poNumber": {
                "method": "regex",
                "patterns": [
                    "(?:Sipariş\\s*(?:No|Numarası))\\s*[:\\s]*([A-Z0-9\\-/]+)",
                    "(?:Purchase\\s*Order\\s*(?:No|Number|#)|PO\\s*(?:No|Number|#))\\s*[:\\s]*([A-Z0-9\\-/]+)"
                ],
                "postProcess": "trim"
            },
            "poDate": {
                "method": "regex",
                "patterns": [
                    "(?:Sipariş\\s*Tarihi|Order\\s*Date)\\s*[:\\s]*(.+?)(?:\\n|$)"
                ],
                "postProcess": "parseDate"
            },
            "deliveryDate": {
                "method": "regex",
                "patterns": [
                    "(?:Teslimat\\s*Tarihi|Teslim\\s*Tarihi|Delivery\\s*Date)\\s*[:\\s]*(.+?)(?:\\n|$)"
                ],
                "postProcess": "parseDate"
            },
            "buyerName": {
                "method": "regex",
                "patterns": ["(?:Alıcı|Buyer|Satın\\s*Alan)\\s*[:\\s]*(.+?)(?:\\n|$)"],
                "postProcess": "trim"
            },
            "supplierName": {
                "method": "regex",
                "patterns": ["(?:Tedarikçi|Satıcı|Supplier|Vendor)\\s*[:\\s]*(.+?)(?:\\n|$)"],
                "postProcess": "trim"
            },
            "shipToAddress": {
                "method": "regex",
                "patterns": ["(?:Sevk\\s*Adresi|Teslimat\\s*Adresi|Ship\\s*To)\\s*[:\\s]*(.+?)(?:\\n|$)"],
                "postProcess": "trim"
            },
            "paymentTerms": {
                "method": "regex",
                "patterns": ["(?:Ödeme\\s*(?:Koşulları|Şartları)|Payment\\s*Terms)\\s*[:\\s]*(.+?)(?:\\n|$)"],
                "postProcess": "trim"
            },
            "currency": {
                "method": "keyword",
                "keywords": {"TRY": ["TL", "TRY", "₺"], "USD": ["USD", "$"], "EUR": ["EUR", "€"]}
            },
            "totalAmount": {
                "method": "regex",
                "patterns": ["(?:Genel\\s*Toplam|Toplam|Grand\\s*Total|Total)\\s*[:\\s]*([\\d.,]+)"],
                "postProcess": "parseAmount"
            }
        },
        "lineItemRules": {
            "method": "table",
            "tableKeywords": {
                "materialNumber": ["malzeme no", "material no", "part no"],
                "description": ["açıklama", "description", "ürün", "malzeme"],
                "quantity": ["miktar", "quantity", "adet", "qty"],
                "unit": ["birim", "unit", "uom"],
                "unitPrice": ["birim fiyat", "unit price", "fiyat"],
                "amount": ["tutar", "amount", "toplam"]
            }
        }
    },
    {
        "id": "payment_tr_standard",
        "name": "Standart TR Odeme Bildirimi",
        "schemaId": "payment_advice_default",
        "description": "Turkiye standart odeme bildirimi formati",
        "builtIn": True,
        "headerRules": {
            "paymentAdviceNumber": {
                "method": "regex",
                "patterns": [
                    "(?:Ödeme\\s*(?:Bildirimi)?\\s*(?:No|Numarası))\\s*[:\\s]*([A-Z0-9\\-/]+)",
                    "(?:Payment\\s*(?:Advice)?\\s*(?:No|Number))\\s*[:\\s]*([A-Z0-9\\-/]+)"
                ],
                "postProcess": "trim"
            },
            "paymentDate": {
                "method": "regex",
                "patterns": ["(?:Ödeme\\s*Tarihi|Payment\\s*Date)\\s*[:\\s]*(.+?)(?:\\n|$)"],
                "postProcess": "parseDate"
            },
            "payerName": {
                "method": "regex",
                "patterns": ["(?:Ödeyen|Payer|From)\\s*[:\\s]*(.+?)(?:\\n|$)"],
                "postProcess": "trim"
            },
            "payeeName": {
                "method": "regex",
                "patterns": ["(?:Alıcı|Payee|To|Lehtar)\\s*[:\\s]*(.+?)(?:\\n|$)"],
                "postProcess": "trim"
            },
            "bankName": {
                "method": "regex",
                "patterns": ["(?:Banka|Bank)\\s*[:\\s]*(.+?)(?:\\n|$)"],
                "postProcess": "trim"
            },
            "iban": {
                "method": "regex",
                "patterns": [
                    "(?:IBAN\\s*[:\\s]*)?(TR\\d{2}\\s?\\d{4}\\s?\\d{4}\\s?\\d{4}\\s?\\d{4}\\s?\\d{4}\\s?\\d{2})",
                    "(?:IBAN\\s*[:\\s]*)?([A-Z]{2}\\d{2}[\\s]?[\\dA-Z\\s]{10,30})"
                ],
                "postProcess": "parseIBAN"
            },
            "currency": {
                "method": "keyword",
                "keywords": {"TRY": ["TL", "TRY", "₺"], "USD": ["USD", "$"], "EUR": ["EUR", "€"]}
            },
            "totalAmount": {
                "method": "regex",
                "patterns": ["(?:Toplam|Ödeme\\s*Tutarı|Total\\s*Amount|Payment\\s*Amount)\\s*[:\\s]*([\\d.,]+)"],
                "postProcess": "parseAmount"
            },
            "paymentMethod": {
                "method": "regex",
                "patterns": ["(?:Ödeme\\s*(?:Şekli|Yöntemi)|Payment\\s*Method)\\s*[:\\s]*(.+?)(?:\\n|$)"],
                "postProcess": "trim"
            }
        },
        "lineItemRules": {
            "method": "table",
            "tableKeywords": {
                "invoiceReference": ["fatura", "invoice", "referans", "reference"],
                "amount": ["tutar", "amount", "toplam"],
                "description": ["açıklama", "description"]
            }
        }
    }
]


class TemplateManager:
    """Manages extraction templates - CRUD operations."""

    def __init__(self, templates_dir: str = TEMPLATES_DIR):
        self.templates_dir = templates_dir
        os.makedirs(self.templates_dir, exist_ok=True)
        self._ensure_defaults()

    def _ensure_defaults(self):
        for template in DEFAULT_TEMPLATES:
            path = os.path.join(self.templates_dir, f"{template['id']}.json")
            if not os.path.exists(path):
                self._save(template)

    def _save(self, template: dict):
        path = os.path.join(self.templates_dir, f"{template['id']}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(template, f, ensure_ascii=False, indent=2)

    def list_templates(self, schema_id: str = None) -> list:
        """List templates, optionally filtered by schema ID."""
        templates = []
        for filename in sorted(os.listdir(self.templates_dir)):
            if not filename.endswith('.json'):
                continue
            with open(os.path.join(self.templates_dir, filename), 'r', encoding='utf-8') as f:
                tmpl = json.load(f)
                if schema_id and tmpl.get("schemaId") != schema_id:
                    continue
                templates.append({
                    "id": tmpl["id"],
                    "name": tmpl["name"],
                    "schemaId": tmpl["schemaId"],
                    "description": tmpl.get("description", ""),
                    "builtIn": tmpl.get("builtIn", False),
                    "ruleCount": len(tmpl.get("headerRules", {})),
                })
        return templates

    def get_template(self, template_id: str) -> Optional[dict]:
        path = os.path.join(self.templates_dir, f"{template_id}.json")
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def create_template(self, data: dict) -> dict:
        """Create a new template."""
        template_id = data.get("id") or str(uuid.uuid4())[:8]
        template = {
            "id": template_id,
            "name": data["name"],
            "schemaId": data["schemaId"],
            "description": data.get("description", ""),
            "builtIn": False,
            "createdAt": datetime.utcnow().isoformat(),
            "headerRules": data.get("headerRules", {}),
            "lineItemRules": data.get("lineItemRules", {}),
        }
        self._save(template)
        return template

    def update_template(self, template_id: str, data: dict) -> Optional[dict]:
        existing = self.get_template(template_id)
        if not existing:
            return None
        if existing.get("builtIn"):
            raise ValueError("Built-in templates cannot be modified. Create a copy instead.")

        existing.update({
            "name": data.get("name", existing["name"]),
            "description": data.get("description", existing["description"]),
            "headerRules": data.get("headerRules", existing["headerRules"]),
            "lineItemRules": data.get("lineItemRules", existing["lineItemRules"]),
            "updatedAt": datetime.utcnow().isoformat(),
        })
        self._save(existing)
        return existing

    def delete_template(self, template_id: str) -> bool:
        existing = self.get_template(template_id)
        if not existing:
            return False
        if existing.get("builtIn"):
            raise ValueError("Built-in templates cannot be deleted.")
        path = os.path.join(self.templates_dir, f"{template_id}.json")
        os.remove(path)
        return True

    def duplicate_template(self, template_id: str, new_name: str) -> Optional[dict]:
        existing = self.get_template(template_id)
        if not existing:
            return None
        new_tmpl = {**existing}
        new_tmpl["id"] = str(uuid.uuid4())[:8]
        new_tmpl["name"] = new_name
        new_tmpl["builtIn"] = False
        new_tmpl["createdAt"] = datetime.utcnow().isoformat()
        self._save(new_tmpl)
        return new_tmpl

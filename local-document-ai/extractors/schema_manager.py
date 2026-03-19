"""
Schema Manager - Document schema definitions.
A schema defines WHAT fields to extract from a document type.
Similar to SAP Document AI schema concept.

Example schema:
{
    "id": "invoice_tr",
    "name": "Turkce Fatura",
    "documentType": "invoice",
    "headerFields": [
        {"name": "invoiceNumber", "label": "Fatura No", "type": "string", "required": true},
        {"name": "invoiceDate", "label": "Fatura Tarihi", "type": "date", "required": true},
        ...
    ],
    "lineItemFields": [
        {"name": "description", "label": "Aciklama", "type": "string"},
        {"name": "quantity", "label": "Miktar", "type": "number"},
        ...
    ]
}
"""
import json
import os
import uuid
from datetime import datetime
from typing import Optional


SCHEMAS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "schemas")


FIELD_TYPES = ["string", "number", "date", "currency", "tax_id", "iban", "email", "phone", "address"]


# Built-in default schemas
DEFAULT_SCHEMAS = [
    {
        "id": "invoice_default",
        "name": "Fatura / Invoice",
        "documentType": "invoice",
        "description": "Standart fatura sablonu - TR ve EN destekli",
        "builtIn": True,
        "headerFields": [
            {"name": "invoiceNumber", "label": "Fatura No", "type": "string", "required": True},
            {"name": "invoiceDate", "label": "Fatura Tarihi", "type": "date", "required": True},
            {"name": "dueDate", "label": "Vade Tarihi", "type": "date", "required": False},
            {"name": "vendorName", "label": "Satici", "type": "string", "required": True},
            {"name": "vendorTaxId", "label": "Satici VKN", "type": "tax_id", "required": False},
            {"name": "customerName", "label": "Musteri", "type": "string", "required": True},
            {"name": "customerTaxId", "label": "Musteri VKN", "type": "tax_id", "required": False},
            {"name": "currency", "label": "Para Birimi", "type": "currency", "required": False},
            {"name": "subtotal", "label": "Ara Toplam", "type": "number", "required": False},
            {"name": "taxRate", "label": "KDV Orani", "type": "number", "required": False},
            {"name": "taxAmount", "label": "KDV Tutari", "type": "number", "required": False},
            {"name": "totalAmount", "label": "Genel Toplam", "type": "number", "required": True},
        ],
        "lineItemFields": [
            {"name": "description", "label": "Aciklama", "type": "string"},
            {"name": "quantity", "label": "Miktar", "type": "number"},
            {"name": "unitPrice", "label": "Birim Fiyat", "type": "number"},
            {"name": "amount", "label": "Tutar", "type": "number"},
            {"name": "taxRate", "label": "KDV Orani", "type": "number"},
        ],
    },
    {
        "id": "purchase_order_default",
        "name": "Satin Alma Siparisi / Purchase Order",
        "documentType": "purchaseOrder",
        "description": "Standart satin alma siparisi sablonu",
        "builtIn": True,
        "headerFields": [
            {"name": "poNumber", "label": "Siparis No", "type": "string", "required": True},
            {"name": "poDate", "label": "Siparis Tarihi", "type": "date", "required": True},
            {"name": "deliveryDate", "label": "Teslimat Tarihi", "type": "date", "required": False},
            {"name": "buyerName", "label": "Alici", "type": "string", "required": True},
            {"name": "supplierName", "label": "Tedarikci", "type": "string", "required": True},
            {"name": "shipToAddress", "label": "Sevk Adresi", "type": "address", "required": False},
            {"name": "paymentTerms", "label": "Odeme Kosullari", "type": "string", "required": False},
            {"name": "currency", "label": "Para Birimi", "type": "currency", "required": False},
            {"name": "totalAmount", "label": "Genel Toplam", "type": "number", "required": True},
        ],
        "lineItemFields": [
            {"name": "materialNumber", "label": "Malzeme No", "type": "string"},
            {"name": "description", "label": "Aciklama", "type": "string"},
            {"name": "quantity", "label": "Miktar", "type": "number"},
            {"name": "unit", "label": "Birim", "type": "string"},
            {"name": "unitPrice", "label": "Birim Fiyat", "type": "number"},
            {"name": "amount", "label": "Tutar", "type": "number"},
        ],
    },
    {
        "id": "payment_advice_default",
        "name": "Odeme Bildirimi / Payment Advice",
        "documentType": "paymentAdvice",
        "description": "Standart odeme bildirimi sablonu",
        "builtIn": True,
        "headerFields": [
            {"name": "paymentAdviceNumber", "label": "Odeme Bildirimi No", "type": "string", "required": True},
            {"name": "paymentDate", "label": "Odeme Tarihi", "type": "date", "required": True},
            {"name": "payerName", "label": "Odeyen", "type": "string", "required": True},
            {"name": "payeeName", "label": "Alici", "type": "string", "required": True},
            {"name": "bankName", "label": "Banka", "type": "string", "required": False},
            {"name": "iban", "label": "IBAN", "type": "iban", "required": False},
            {"name": "currency", "label": "Para Birimi", "type": "currency", "required": False},
            {"name": "totalAmount", "label": "Toplam Tutar", "type": "number", "required": True},
            {"name": "paymentMethod", "label": "Odeme Yontemi", "type": "string", "required": False},
        ],
        "lineItemFields": [
            {"name": "invoiceReference", "label": "Fatura Referansi", "type": "string"},
            {"name": "amount", "label": "Tutar", "type": "number"},
            {"name": "description", "label": "Aciklama", "type": "string"},
        ],
    },
]


class SchemaManager:
    """Manages document schemas - CRUD operations."""

    def __init__(self, schemas_dir: str = SCHEMAS_DIR):
        self.schemas_dir = schemas_dir
        os.makedirs(self.schemas_dir, exist_ok=True)
        self._ensure_defaults()

    def _ensure_defaults(self):
        """Write default schemas if they don't exist."""
        for schema in DEFAULT_SCHEMAS:
            path = os.path.join(self.schemas_dir, f"{schema['id']}.json")
            if not os.path.exists(path):
                self._save(schema)

    def _save(self, schema: dict):
        path = os.path.join(self.schemas_dir, f"{schema['id']}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(schema, f, ensure_ascii=False, indent=2)

    def list_schemas(self) -> list:
        """List all available schemas."""
        schemas = []
        for filename in sorted(os.listdir(self.schemas_dir)):
            if filename.endswith('.json'):
                with open(os.path.join(self.schemas_dir, filename), 'r', encoding='utf-8') as f:
                    schema = json.load(f)
                    schemas.append({
                        "id": schema["id"],
                        "name": schema["name"],
                        "documentType": schema["documentType"],
                        "description": schema.get("description", ""),
                        "builtIn": schema.get("builtIn", False),
                        "headerFieldCount": len(schema.get("headerFields", [])),
                        "lineItemFieldCount": len(schema.get("lineItemFields", [])),
                    })
        return schemas

    def get_schema(self, schema_id: str) -> Optional[dict]:
        """Get a schema by ID."""
        path = os.path.join(self.schemas_dir, f"{schema_id}.json")
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def create_schema(self, data: dict) -> dict:
        """Create a new schema."""
        schema_id = data.get("id") or str(uuid.uuid4())[:8]
        schema = {
            "id": schema_id,
            "name": data["name"],
            "documentType": data.get("documentType", "custom"),
            "description": data.get("description", ""),
            "builtIn": False,
            "createdAt": datetime.utcnow().isoformat(),
            "headerFields": data.get("headerFields", []),
            "lineItemFields": data.get("lineItemFields", []),
        }

        # Validate field types
        for field in schema["headerFields"] + schema["lineItemFields"]:
            if field.get("type") and field["type"] not in FIELD_TYPES:
                raise ValueError(f"Invalid field type: {field['type']}. Allowed: {FIELD_TYPES}")

        self._save(schema)
        return schema

    def update_schema(self, schema_id: str, data: dict) -> Optional[dict]:
        """Update an existing schema."""
        existing = self.get_schema(schema_id)
        if not existing:
            return None
        if existing.get("builtIn"):
            raise ValueError("Built-in schemas cannot be modified. Create a copy instead.")

        existing.update({
            "name": data.get("name", existing["name"]),
            "description": data.get("description", existing["description"]),
            "headerFields": data.get("headerFields", existing["headerFields"]),
            "lineItemFields": data.get("lineItemFields", existing["lineItemFields"]),
            "updatedAt": datetime.utcnow().isoformat(),
        })
        self._save(existing)
        return existing

    def delete_schema(self, schema_id: str) -> bool:
        """Delete a schema."""
        existing = self.get_schema(schema_id)
        if not existing:
            return False
        if existing.get("builtIn"):
            raise ValueError("Built-in schemas cannot be deleted.")
        path = os.path.join(self.schemas_dir, f"{schema_id}.json")
        os.remove(path)
        return True

    def duplicate_schema(self, schema_id: str, new_name: str) -> Optional[dict]:
        """Duplicate a schema with a new name/ID."""
        existing = self.get_schema(schema_id)
        if not existing:
            return None
        new_schema = {**existing}
        new_schema["id"] = str(uuid.uuid4())[:8]
        new_schema["name"] = new_name
        new_schema["builtIn"] = False
        new_schema["createdAt"] = datetime.utcnow().isoformat()
        self._save(new_schema)
        return new_schema

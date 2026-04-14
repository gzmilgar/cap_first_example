"""
Template Builder - Generates extraction templates automatically.
No regex knowledge needed - just labels or sample text.

Two methods:
1. Label-based: User provides label texts per field (e.g., "Fatura No", "PO No")
2. Sample-based: User provides sample document + annotations (field -> value text)

Both methods auto-generate regex patterns behind the scenes.
"""
import re
from typing import Optional


# Value patterns per field type
VALUE_PATTERNS = {
    "string": r"(.+?)(?:\n|$)",
    "number": r"([\d.,]+)",
    "currency": r"(\w{3}|TL|USD|EUR|GBP|₺|\$|€|£)",
    "date": r"([\d]{1,4}[.\-/][\d]{1,2}[.\-/][\d]{1,4})",
    "tax_id": r"(\d{10,11})",
    "iban": r"([A-Z]{2}\d{2}[\s\d]{10,30})",
    "email": r"([\w\.\-]+@[\w\.\-]+\.\w+)",
    "phone": r"([\+\d][\d\s\-\(\)]{7,20})",
    "address": r"(.+?)(?:\n|$)",
}

# Post-process mapping per field type
POST_PROCESS_MAP = {
    "string": "trim",
    "number": "parseAmount",
    "currency": "trim",
    "date": "parseDate",
    "tax_id": "trim",
    "iban": "parseIBAN",
    "email": "trim",
    "phone": "trim",
    "address": "trim",
}


class TemplateBuilder:
    """Auto-generates template rules from labels or sample text."""

    @staticmethod
    def escape_label(label: str) -> str:
        """
        Escape a label for use in regex, making whitespace flexible.
        'Purchase Order No' -> 'Purchase\\s*Order\\s*No'
        """
        # Escape regex special chars but keep it readable
        escaped = re.escape(label.strip())
        # Make spaces flexible (one or more whitespace)
        escaped = re.sub(r'\\\s+|\\ ', r'\\s*', escaped)
        # Handle colons, dashes flexibly
        escaped = escaped.replace(r'\:', r'\s*[:\s]\s*')
        return escaped

    @classmethod
    def build_regex_from_labels(cls, labels: list, field_type: str = "string") -> str:
        """
        Build a regex pattern from a list of possible labels.

        Example:
        labels=["Purchase Order No", "PO No", "Siparis No"]
        field_type="string"
        -> (?:Purchase\\s*Order\\s*No|PO\\s*No|Siparis\\s*No)\\s*[:\\s]*(.+?)(?:\\n|$)
        """
        if not labels:
            return None

        escaped_labels = [cls.escape_label(lbl) for lbl in labels if lbl.strip()]
        if not escaped_labels:
            return None

        label_alternatives = "|".join(escaped_labels)
        value_pattern = VALUE_PATTERNS.get(field_type, VALUE_PATTERNS["string"])

        return f"(?:{label_alternatives})\\s*[:\\s]*{value_pattern}"

    @classmethod
    def build_rule_from_labels(cls, labels: list, field_type: str = "string") -> dict:
        """Build a complete rule dict from labels."""
        pattern = cls.build_regex_from_labels(labels, field_type)
        if not pattern:
            return None
        return {
            "method": "regex",
            "patterns": [pattern],
            "postProcess": POST_PROCESS_MAP.get(field_type, "trim"),
        }

    @classmethod
    def build_keyword_rule(cls, keyword_map: dict) -> dict:
        """
        Build a keyword-based rule (e.g., for currency).
        keyword_map = {"TRY": ["TL", "TRY"], "USD": ["USD", "$"]}
        """
        return {
            "method": "keyword",
            "keywords": keyword_map,
        }

    @classmethod
    def build_template_from_labels(cls, schema: dict, field_labels: dict,
                                    template_name: str, description: str = "",
                                    line_item_labels: dict = None) -> dict:
        """
        Build a complete template from field->labels mapping.

        Args:
            schema: The schema dict
            field_labels: {
                "invoiceNumber": ["Fatura No", "Invoice No"],
                "currency": ["Currency", "Para Birimi"],
                ...
            }
            template_name: Name for the new template
            description: Optional description
            line_item_labels: Optional {field_name: [column_headers]} for line items.
                e.g. {"description": ["Aciklama", "Description", "Urun"]}

        Returns:
            Complete template dict ready to save
        """
        header_rules = {}

        for field in schema.get("headerFields", []):
            field_name = field["name"]
            field_type = field.get("type", "string")
            labels = field_labels.get(field_name, [])

            # If no labels provided, try to use the field label itself
            if not labels and field.get("label"):
                labels = [field["label"]]

            if not labels:
                continue

            # Special handling for currency
            if field_type == "currency":
                header_rules[field_name] = {
                    "method": "keyword",
                    "keywords": {
                        "TRY": ["TL", "TRY", "₺"],
                        "USD": ["USD", "$"],
                        "EUR": ["EUR", "€"],
                        "GBP": ["GBP", "£"],
                    }
                }
            else:
                rule = cls.build_rule_from_labels(labels, field_type)
                if rule:
                    header_rules[field_name] = rule

        # Line item table keywords: user-provided labels override schema defaults
        line_item_labels = line_item_labels or {}
        table_keywords = {}
        for field in schema.get("lineItemFields", []):
            field_name = field["name"]

            # 1) user-provided labels take priority
            user_labels = line_item_labels.get(field_name, [])
            if user_labels:
                keywords = [lbl.lower().strip() for lbl in user_labels if lbl.strip()]
            else:
                # 2) fallback: schema label + name + synonyms
                keywords = [field.get("label", "").lower(), field_name.lower()]
                synonyms_map = {
                    "description": ["description", "aciklama", "açıklama", "ürün"],
                    "quantity": ["quantity", "miktar", "adet", "qty"],
                    "unitPrice": ["unit price", "birim fiyat", "fiyat"],
                    "amount": ["amount", "tutar", "toplam"],
                    "unit": ["unit", "birim", "uom"],
                    "materialNumber": ["material", "malzeme", "part no"],
                }
                for key, syns in synonyms_map.items():
                    if field_name.lower() == key.lower() or any(s in field_name.lower() for s in syns):
                        keywords.extend(syns)
                        break

            keywords = list(dict.fromkeys(k for k in keywords if k))
            if keywords:
                table_keywords[field_name] = keywords

        template = {
            "name": template_name,
            "schemaId": schema["id"],
            "description": description,
            "headerRules": header_rules,
            "lineItemRules": {
                "method": "table",
                "tableKeywords": table_keywords,
            }
        }
        return template

    @classmethod
    def learn_from_sample(cls, schema: dict, sample_text: str,
                          annotations: dict, template_name: str,
                          description: str = "",
                          line_item_annotations: dict = None) -> dict:
        """
        Learn extraction rules from a sample document.

        Args:
            schema: The schema dict
            sample_text: The full extracted text of the sample document
            annotations: {
                "fieldName": "exact value from text",
                ...
            }
                Example: {"invoiceNumber": "FTR-2024-001234"}
            template_name: Name for new template
            description: Optional description
            line_item_annotations: Optional {field_name: "column header text"}
                e.g. {"description": "Aciklama", "quantity": "Miktar"}

        Returns:
            Complete template dict with auto-generated rules

        Logic:
            For each annotation, find the value in the text, then look at the
            preceding label (text before the value) to build a regex rule.
        """
        field_labels = {}

        for field_name, value in annotations.items():
            if not value:
                continue
            labels = cls._extract_labels_for_value(sample_text, value)
            if labels:
                field_labels[field_name] = labels

        # Convert line item annotations (single column header per field) to list form
        line_item_labels = None
        if line_item_annotations:
            line_item_labels = {}
            for field_name, header in line_item_annotations.items():
                if header and header.strip():
                    line_item_labels[field_name] = [header.strip()]

        return cls.build_template_from_labels(
            schema, field_labels, template_name, description,
            line_item_labels=line_item_labels
        )

    @staticmethod
    def _extract_labels_for_value(text: str, value: str) -> list:
        """
        Find the value in text and extract the preceding label.

        Example:
        text = "Fatura No: FTR-2024-001234\nTarih: ..."
        value = "FTR-2024-001234"
        -> returns ["Fatura No"]
        """
        labels = []
        value = value.strip()
        if not value:
            return labels

        # Find all occurrences of value in text
        for match in re.finditer(re.escape(value), text):
            start = match.start()
            # Look at the text before the value (same line, up to 50 chars)
            line_start = text.rfind('\n', 0, start) + 1
            prefix = text[line_start:start].strip()

            # Remove trailing punctuation
            prefix = re.sub(r'[\s:=\-\.]+$', '', prefix).strip()

            if prefix and len(prefix) < 60:
                labels.append(prefix)

        # Return unique labels
        return list(dict.fromkeys(labels))

    @classmethod
    def suggest_labels_from_text(cls, text: str, max_per_field: int = 3) -> dict:
        """
        Analyze text and suggest potential labels with their following values.

        Returns:
            {
                "Fatura No": "FTR-2024-001234",
                "Tarih": "15.03.2024",
                ...
            }

        Useful for a "scan document and suggest fields" feature.
        """
        suggestions = {}
        # Pattern: LabelText: Value (on same line)
        pattern = re.compile(r'^([A-Za-z\u00C0-\u017F\u0100-\u024F\s]{2,40}?)\s*[:\s]\s*(.+?)$', re.MULTILINE)

        for match in pattern.finditer(text):
            label = match.group(1).strip()
            value = match.group(2).strip()
            # Filter out too short/long or numeric-only labels
            if (2 < len(label) < 40 and not label.isdigit() and value
                    and len(value) < 100 and label not in suggestions):
                suggestions[label] = value

        return suggestions

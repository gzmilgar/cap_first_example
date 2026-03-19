"""
Dynamic Extractor - Uses schema + template to extract fields.
This is the core engine that replaces hardcoded extractors.

Flow:
1. User selects a schema (defines WHAT fields)
2. User selects a template (defines HOW to find each field)
3. Document text is extracted (PDF/image)
4. Dynamic extractor applies template rules to text
5. Results are returned in schema-defined structure
"""
import re
from typing import Optional
from .base_extractor import BaseDocumentExtractor
from .schema_manager import SchemaManager
from .template_manager import TemplateManager


class DynamicExtractor(BaseDocumentExtractor):
    """
    Extracts fields from documents using schema + template definitions.
    No hardcoded logic - everything is driven by configuration.
    """

    def __init__(self, schema_manager: SchemaManager = None, template_manager: TemplateManager = None):
        self.schema_manager = schema_manager or SchemaManager()
        self.template_manager = template_manager or TemplateManager()

    def extract(self, text: str, schema_id: str, template_id: str, tables: list = None) -> dict:
        """
        Main extraction method.

        Args:
            text: Raw document text
            schema_id: Which schema to use (defines expected fields)
            template_id: Which template to use (defines extraction rules)
            tables: Optional table data from PDF

        Returns:
            Extraction result with header fields, line items, confidence
        """
        schema = self.schema_manager.get_schema(schema_id)
        if not schema:
            raise ValueError(f"Schema not found: {schema_id}")

        template = self.template_manager.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        if template["schemaId"] != schema_id:
            raise ValueError(
                f"Template '{template_id}' is for schema '{template['schemaId']}', "
                f"not '{schema_id}'"
            )

        # Extract header fields
        header_fields = self._extract_header(text, schema, template)

        # Extract line items
        line_items = self._extract_line_items(text, schema, template, tables)

        # Calculate confidence
        required_fields = [f["name"] for f in schema.get("headerFields", []) if f.get("required")]
        found_required = sum(1 for f in required_fields if header_fields.get(f) is not None)
        total_found = sum(1 for v in header_fields.values() if v is not None)
        total_fields = len(schema.get("headerFields", []))

        if required_fields:
            confidence = (found_required / len(required_fields)) * 0.7 + \
                         (total_found / max(total_fields, 1)) * 0.3
        else:
            confidence = total_found / max(total_fields, 1)

        return {
            "status": "DONE",
            "schemaId": schema_id,
            "templateId": template_id,
            "schemaName": schema["name"],
            "templateName": template["name"],
            "documentType": schema.get("documentType", "custom"),
            "confidence": round(min(confidence, 1.0), 2),
            "headerFields": header_fields,
            "lineItems": line_items,
            "lineItemCount": len(line_items),
            "extractionDetails": {
                "totalFields": total_fields,
                "extractedFields": total_found,
                "requiredFields": len(required_fields),
                "foundRequired": found_required,
            }
        }

    def _extract_header(self, text: str, schema: dict, template: dict) -> dict:
        """Extract header fields using template rules."""
        header = {}
        header_rules = template.get("headerRules", {})

        for field_def in schema.get("headerFields", []):
            field_name = field_def["name"]
            rule = header_rules.get(field_name)

            if not rule:
                header[field_name] = None
                continue

            value = self._apply_rule(text, rule)
            header[field_name] = value

        return header

    def _apply_rule(self, text: str, rule: dict):
        """Apply a single extraction rule to text."""
        method = rule.get("method", "regex")

        if method == "regex":
            return self._apply_regex_rule(text, rule)
        elif method == "keyword":
            return self._apply_keyword_rule(text, rule)
        elif method == "position":
            return self._apply_position_rule(text, rule)
        else:
            return None

    def _apply_regex_rule(self, text: str, rule: dict):
        """Extract using regex patterns."""
        patterns = rule.get("patterns", [])
        match_index = rule.get("matchIndex", 0)
        post_process = rule.get("postProcess", "trim")

        for pattern in patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
            if matches and match_index < len(matches):
                raw_value = matches[match_index].group(1).strip()
                return self._post_process(raw_value, post_process)

        return None

    def _apply_keyword_rule(self, text: str, rule: dict):
        """Extract by keyword matching (e.g., currency detection)."""
        keywords = rule.get("keywords", {})
        text_upper = text.upper()

        for value, kw_list in keywords.items():
            for kw in kw_list:
                if kw.upper() in text_upper:
                    return value
        return None

    def _apply_position_rule(self, text: str, rule: dict):
        """Extract by line/position (for fixed-layout documents)."""
        line_number = rule.get("lineNumber")
        char_start = rule.get("charStart", 0)
        char_end = rule.get("charEnd")
        post_process = rule.get("postProcess", "trim")

        lines = text.split('\n')
        if line_number is not None and line_number < len(lines):
            line = lines[line_number]
            if char_end:
                raw_value = line[char_start:char_end]
            else:
                raw_value = line[char_start:]
            return self._post_process(raw_value.strip(), post_process)
        return None

    def _post_process(self, value: str, method: str):
        """Apply post-processing to extracted value."""
        if not value:
            return None

        if method == "trim":
            return value.strip()
        elif method == "uppercase":
            return value.strip().upper()
        elif method == "lowercase":
            return value.strip().lower()
        elif method == "parseAmount":
            return self.parse_amount(value)
        elif method == "parseInteger":
            match = re.search(r'(\d+)', value)
            return int(match.group(1)) if match else None
        elif method == "parseDate":
            return value.strip()
        elif method == "parseIBAN":
            return re.sub(r'\s+', '', value)
        else:
            return value.strip()

    def _extract_line_items(self, text: str, schema: dict, template: dict, tables: list = None) -> list:
        """Extract line items using template rules."""
        line_item_rules = template.get("lineItemRules", {})
        method = line_item_rules.get("method", "table")
        schema_fields = schema.get("lineItemFields", [])

        items = []

        if method == "table" and tables:
            items = self._extract_items_from_tables(tables, line_item_rules, schema_fields)

        # Fallback to regex if no table items found
        if not items and line_item_rules.get("regexPattern"):
            items = self._extract_items_by_regex(text, line_item_rules, schema_fields)

        return items

    def _extract_items_from_tables(self, tables: list, rules: dict, schema_fields: list) -> list:
        """Extract line items from PDF tables using keyword column mapping."""
        items = []
        table_keywords = rules.get("tableKeywords", {})

        for table_data in tables:
            rows = table_data.get("rows", [])
            if len(rows) < 2:
                continue

            header_row = rows[0]
            if not header_row:
                continue

            # Map columns
            col_map = {}
            for i, col in enumerate(header_row):
                if col is None:
                    continue
                col_lower = str(col).lower().strip()
                for field_name, keywords in table_keywords.items():
                    if any(k in col_lower for k in keywords):
                        col_map[field_name] = i
                        break

            if not col_map:
                continue

            # Extract rows
            for row in rows[1:]:
                if not row or all(c is None or str(c).strip() == '' for c in row):
                    continue

                item = {}
                for field_name, col_idx in col_map.items():
                    if col_idx < len(row) and row[col_idx] is not None:
                        val = str(row[col_idx]).strip()
                        # Determine field type from schema
                        field_type = "string"
                        for sf in schema_fields:
                            if sf["name"] == field_name:
                                field_type = sf.get("type", "string")
                                break

                        if field_type == "number":
                            item[field_name] = self.parse_amount(val)
                        else:
                            item[field_name] = val

                if any(v for v in item.values()):
                    items.append(item)

        return items

    def _extract_items_by_regex(self, text: str, rules: dict, schema_fields: list) -> list:
        """Extract line items using regex pattern."""
        items = []
        pattern = rules.get("regexPattern")
        group_names = rules.get("regexGroups", [])

        if not pattern:
            return items

        for match in re.finditer(pattern, text, re.IGNORECASE):
            item = {}
            for i, group_name in enumerate(group_names):
                if i + 1 <= len(match.groups()):
                    val = match.group(i + 1)
                    # Check type from schema
                    field_type = "string"
                    for sf in schema_fields:
                        if sf["name"] == group_name:
                            field_type = sf.get("type", "string")
                            break

                    if field_type == "number":
                        item[group_name] = self.parse_amount(val)
                    else:
                        item[group_name] = val.strip() if val else None

            if any(v for v in item.values()):
                items.append(item)

        return items

    def auto_detect_template(self, text: str, schema_id: str) -> Optional[str]:
        """
        Try all templates for a schema and return the best match.
        Useful when user doesn't know which template to use.
        """
        templates = self.template_manager.list_templates(schema_id=schema_id)
        best_template_id = None
        best_confidence = 0

        for tmpl_info in templates:
            try:
                result = self.extract(text, schema_id, tmpl_info["id"])
                if result["confidence"] > best_confidence:
                    best_confidence = result["confidence"]
                    best_template_id = tmpl_info["id"]
            except Exception:
                continue

        return best_template_id

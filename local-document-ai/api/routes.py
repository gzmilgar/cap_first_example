"""
REST API routes - SAP Document AI compatible endpoints.
Includes schema/template management and dynamic extraction.
"""
import os
import json
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template

from extractors.text_extractor import TextExtractor
from extractors.schema_manager import SchemaManager
from extractors.template_manager import TemplateManager
from extractors.dynamic_extractor import DynamicExtractor
from extractors.template_builder import TemplateBuilder

api = Blueprint('api', __name__)

# Managers (initialized once)
schema_manager = SchemaManager()
template_manager = TemplateManager()
dynamic_extractor = DynamicExtractor(schema_manager, template_manager)

# In-memory job storage
_jobs = {}

ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}

# Default schema-template mapping for backward compatibility
DEFAULT_MAPPING = {
    "invoice": ("invoice_default", "invoice_tr_standard"),
    "purchaseOrder": ("purchase_order_default", "po_tr_standard"),
    "paymentAdvice": ("payment_advice_default", "payment_tr_standard"),
}


def _allowed_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================
#  PAGES
# ============================================================

@api.route('/')
def index():
    return render_template('index.html')


# ============================================================
#  SCHEMA ENDPOINTS
# ============================================================

@api.route('/api/v1/schemas', methods=['GET'])
def list_schemas():
    return jsonify({"schemas": schema_manager.list_schemas()})


@api.route('/api/v1/schemas/<schema_id>', methods=['GET'])
def get_schema(schema_id):
    schema = schema_manager.get_schema(schema_id)
    if not schema:
        return jsonify({"error": "Schema not found"}), 404
    return jsonify(schema)


@api.route('/api/v1/schemas', methods=['POST'])
def create_schema():
    """
    Create a new schema.
    Body JSON:
    {
        "name": "Ozel Fatura Tipi",
        "documentType": "custom_invoice",
        "description": "...",
        "headerFields": [
            {"name": "invoiceNo", "label": "Fatura No", "type": "string", "required": true},
            ...
        ],
        "lineItemFields": [...]
    }
    """
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "name is required"}), 400
    try:
        schema = schema_manager.create_schema(data)
        return jsonify(schema), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@api.route('/api/v1/schemas/<schema_id>', methods=['PUT'])
def update_schema(schema_id):
    data = request.get_json()
    try:
        schema = schema_manager.update_schema(schema_id, data)
        if not schema:
            return jsonify({"error": "Schema not found"}), 404
        return jsonify(schema)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@api.route('/api/v1/schemas/<schema_id>', methods=['DELETE'])
def delete_schema(schema_id):
    try:
        if schema_manager.delete_schema(schema_id):
            return jsonify({"message": "Deleted"})
        return jsonify({"error": "Schema not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@api.route('/api/v1/schemas/<schema_id>/duplicate', methods=['POST'])
def duplicate_schema(schema_id):
    data = request.get_json() or {}
    new_name = data.get("name", "Copy")
    schema = schema_manager.duplicate_schema(schema_id, new_name)
    if not schema:
        return jsonify({"error": "Schema not found"}), 404
    return jsonify(schema), 201


# ============================================================
#  TEMPLATE ENDPOINTS
# ============================================================

@api.route('/api/v1/templates', methods=['GET'])
def list_templates():
    schema_id = request.args.get('schemaId')
    return jsonify({"templates": template_manager.list_templates(schema_id)})


@api.route('/api/v1/templates/<template_id>', methods=['GET'])
def get_template(template_id):
    tmpl = template_manager.get_template(template_id)
    if not tmpl:
        return jsonify({"error": "Template not found"}), 404
    return jsonify(tmpl)


@api.route('/api/v1/templates', methods=['POST'])
def create_template():
    """
    Create a new template.
    Body JSON:
    {
        "name": "Ozel Fatura Template",
        "schemaId": "invoice_default",
        "headerRules": {
            "invoiceNumber": {
                "method": "regex",
                "patterns": ["Fatura\\s*No\\s*[:\\s]*([A-Z0-9-]+)"],
                "postProcess": "trim"
            },
            ...
        },
        "lineItemRules": {
            "method": "table",
            "tableKeywords": { ... }
        }
    }
    """
    data = request.get_json()
    if not data or not data.get("name") or not data.get("schemaId"):
        return jsonify({"error": "name and schemaId are required"}), 400

    # Verify schema exists
    if not schema_manager.get_schema(data["schemaId"]):
        return jsonify({"error": f"Schema not found: {data['schemaId']}"}), 400

    tmpl = template_manager.create_template(data)
    return jsonify(tmpl), 201


@api.route('/api/v1/templates/<template_id>', methods=['PUT'])
def update_template(template_id):
    data = request.get_json()
    try:
        tmpl = template_manager.update_template(template_id, data)
        if not tmpl:
            return jsonify({"error": "Template not found"}), 404
        return jsonify(tmpl)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@api.route('/api/v1/templates/<template_id>', methods=['DELETE'])
def delete_template(template_id):
    try:
        if template_manager.delete_template(template_id):
            return jsonify({"message": "Deleted"})
        return jsonify({"error": "Template not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@api.route('/api/v1/templates/<template_id>/duplicate', methods=['POST'])
def duplicate_template(template_id):
    data = request.get_json() or {}
    new_name = data.get("name", "Copy")
    tmpl = template_manager.duplicate_template(template_id, new_name)
    if not tmpl:
        return jsonify({"error": "Template not found"}), 404
    return jsonify(tmpl), 201


# ============================================================
#  SMART TEMPLATE BUILDER (no regex needed!)
# ============================================================

@api.route('/api/v1/templates/from-labels', methods=['POST'])
def create_template_from_labels():
    """
    Create a template by providing labels per field (no regex needed).

    Body JSON:
    {
        "name": "Retail Template",
        "schemaId": "retail",
        "description": "...",
        "fieldLabels": {
            "PurchaseOrderNo": ["Purchase Order No", "PO No", "Siparis No"],
            "PurchaseOrderDate": ["Purchase Order Date", "Date", "Tarih"],
            ...
        }
    }

    System will auto-generate regex based on labels + field types from schema.
    """
    data = request.get_json()
    if not data or not data.get("name") or not data.get("schemaId"):
        return jsonify({"error": "name and schemaId are required"}), 400

    schema = schema_manager.get_schema(data["schemaId"])
    if not schema:
        return jsonify({"error": f"Schema not found: {data['schemaId']}"}), 400

    field_labels = data.get("fieldLabels", {})
    if not field_labels:
        return jsonify({"error": "fieldLabels is required and cannot be empty"}), 400

    template_data = TemplateBuilder.build_template_from_labels(
        schema, field_labels, data["name"], data.get("description", "")
    )

    created = template_manager.create_template(template_data)
    return jsonify(created), 201


@api.route('/api/v1/templates/from-sample', methods=['POST'])
def create_template_from_sample():
    """
    Create a template by learning from a sample document.

    Form data:
    - file: sample document (PDF or image)
    - schemaId: target schema ID
    - name: template name
    - description: (optional)
    - annotations: JSON string like
        {"invoiceNumber": "FTR-2024-001234", "totalAmount": "99.000,00"}
    - lang: OCR language (default eng+tur)

    System will:
    1. Extract text from sample
    2. Find each annotation value in text
    3. Identify the preceding label
    4. Auto-generate extraction rules
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if not file.filename or not _allowed_file(file.filename):
        return jsonify({"error": "Invalid or unsupported file"}), 400

    schema_id = request.form.get('schemaId')
    name = request.form.get('name')
    description = request.form.get('description', '')
    annotations_raw = request.form.get('annotations', '{}')
    lang = request.form.get('lang', 'eng+tur')

    if not schema_id or not name:
        return jsonify({"error": "schemaId and name are required"}), 400

    schema = schema_manager.get_schema(schema_id)
    if not schema:
        return jsonify({"error": f"Schema not found: {schema_id}"}), 400

    try:
        annotations = json.loads(annotations_raw)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid annotations JSON"}), 400

    if not annotations:
        return jsonify({"error": "annotations is required"}), 400

    try:
        file_bytes = file.read()
        extraction = TextExtractor.extract_from_bytes(file_bytes, file.filename, lang=lang)
        sample_text = extraction["text"]

        template_data = TemplateBuilder.learn_from_sample(
            schema, sample_text, annotations, name, description
        )

        created = template_manager.create_template(template_data)
        return jsonify({
            "template": created,
            "sampleText": sample_text,
            "learnedLabels": {
                fname: rule.get("patterns", [])
                for fname, rule in created.get("headerRules", {}).items()
            }
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route('/api/v1/templates/suggest-from-text', methods=['POST'])
def suggest_from_text():
    """
    Analyze document text and suggest label->value pairs.
    Useful for showing the user what fields could be extracted.

    Form data:
    - file: document file
    - lang: OCR language
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if not file.filename or not _allowed_file(file.filename):
        return jsonify({"error": "Invalid file"}), 400

    lang = request.form.get('lang', 'eng+tur')

    try:
        file_bytes = file.read()
        extraction = TextExtractor.extract_from_bytes(file_bytes, file.filename, lang=lang)
        text = extraction["text"]
        suggestions = TemplateBuilder.suggest_labels_from_text(text)
        return jsonify({
            "text": text,
            "suggestions": suggestions,
            "fileName": file.filename,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
#  EXTRACTION ENDPOINTS
# ============================================================

@api.route('/api/v1/document/extract', methods=['POST'])
def extract_sync():
    """
    Synchronous extraction.
    Form data:
    - file: document file
    - schemaId: schema to use (or documentType for backward compat)
    - templateId: template to use (auto-detect if omitted)
    - documentType: backward compat (invoice|purchaseOrder|paymentAdvice)
    - lang: OCR language (default: eng+tur)
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if not file.filename or not _allowed_file(file.filename):
        return jsonify({"error": "Invalid or unsupported file"}), 400

    schema_id = request.form.get('schemaId')
    template_id = request.form.get('templateId')
    doc_type = request.form.get('documentType')
    lang = request.form.get('lang', 'eng+tur')

    # Backward compat: map documentType to schema+template
    if not schema_id and doc_type and doc_type in DEFAULT_MAPPING:
        schema_id, template_id = DEFAULT_MAPPING[doc_type]
    elif not schema_id:
        schema_id, template_id = DEFAULT_MAPPING["invoice"]

    try:
        file_bytes = file.read()
        extraction_data = TextExtractor.extract_from_bytes(file_bytes, file.filename, lang=lang)
        text = extraction_data["text"]
        tables = extraction_data.get("tables", [])

        # Auto-detect template if not specified
        if not template_id:
            template_id = dynamic_extractor.auto_detect_template(text, schema_id)
            if not template_id:
                return jsonify({"error": f"No matching template found for schema '{schema_id}'"}), 400

        result = dynamic_extractor.extract(text, schema_id, template_id, tables)
        result["rawText"] = text
        result["fileName"] = file.filename

        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e), "status": "FAILED"}), 500


@api.route('/api/v1/document/jobs', methods=['POST'])
def create_extraction_job():
    """Create an async extraction job."""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if not file.filename or not _allowed_file(file.filename):
        return jsonify({"error": "Invalid file"}), 400

    schema_id = request.form.get('schemaId')
    template_id = request.form.get('templateId')
    doc_type = request.form.get('documentType')
    lang = request.form.get('lang', 'eng+tur')

    if not schema_id and doc_type and doc_type in DEFAULT_MAPPING:
        schema_id, template_id = DEFAULT_MAPPING[doc_type]
    elif not schema_id:
        schema_id, template_id = DEFAULT_MAPPING["invoice"]

    job_id = str(uuid.uuid4())
    file_bytes = file.read()
    filename = file.filename

    try:
        extraction_data = TextExtractor.extract_from_bytes(file_bytes, filename, lang=lang)
        text = extraction_data["text"]
        tables = extraction_data.get("tables", [])

        if not template_id:
            template_id = dynamic_extractor.auto_detect_template(text, schema_id)

        result = dynamic_extractor.extract(text, schema_id, template_id, tables)

        _jobs[job_id] = {
            "id": job_id,
            "status": "DONE",
            "fileName": filename,
            "schemaId": schema_id,
            "templateId": template_id,
            "createdAt": datetime.utcnow().isoformat(),
            "result": result,
            "rawText": text,
        }
    except Exception as e:
        _jobs[job_id] = {
            "id": job_id,
            "status": "FAILED",
            "fileName": filename,
            "createdAt": datetime.utcnow().isoformat(),
            "error": str(e),
        }

    return jsonify({"id": job_id, "status": _jobs[job_id]["status"]}), 201


@api.route('/api/v1/document/jobs/<job_id>', methods=['GET'])
def get_job_result(job_id):
    if job_id not in _jobs:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(_jobs[job_id])


@api.route('/api/v1/document/jobs', methods=['GET'])
def list_jobs():
    jobs = [
        {"id": j["id"], "status": j["status"], "fileName": j["fileName"],
         "createdAt": j["createdAt"]}
        for j in _jobs.values()
    ]
    return jsonify({"jobs": jobs, "count": len(jobs)})


@api.route('/api/v1/document/text', methods=['POST'])
def extract_text_only():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if not file.filename or not _allowed_file(file.filename):
        return jsonify({"error": "Invalid or unsupported file"}), 400

    lang = request.form.get('lang', 'eng+tur')

    try:
        file_bytes = file.read()
        extraction_data = TextExtractor.extract_from_bytes(file_bytes, file.filename, lang=lang)
        return jsonify({
            "text": extraction_data["text"],
            "tables": extraction_data.get("tables", []),
            "source": extraction_data["source"],
            "fileName": file.filename,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route('/api/v1/capabilities', methods=['GET'])
def capabilities():
    return jsonify({
        "service": "Local Document AI",
        "version": "2.0.0",
        "description": "SAP Document AI compatible local extraction service with schema & template support",
        "supportedFileTypes": list(ALLOWED_EXTENSIONS),
        "supportedLanguages": ["eng", "tur", "deu", "fra"],
        "schemas": schema_manager.list_schemas(),
        "templates": template_manager.list_templates(),
        "features": [
            "Custom schema creation (define WHAT to extract)",
            "Custom template creation (define HOW to extract)",
            "PDF text extraction",
            "Image OCR (Tesseract)",
            "Table extraction from PDFs",
            "Auto template detection",
            "Turkish & English document support",
            "Regex, keyword, and position-based extraction rules",
        ],
    })

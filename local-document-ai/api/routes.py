"""
REST API routes - SAP Document AI compatible endpoints.
"""
import os
import json
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template

from extractors.text_extractor import TextExtractor
from extractors.invoice_extractor import InvoiceExtractor
from extractors.purchase_order_extractor import PurchaseOrderExtractor
from extractors.payment_advice_extractor import PaymentAdviceExtractor

api = Blueprint('api', __name__)

# In-memory job storage
_jobs = {}

EXTRACTORS = {
    "invoice": InvoiceExtractor(),
    "purchaseOrder": PurchaseOrderExtractor(),
    "paymentAdvice": PaymentAdviceExtractor(),
}

ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}


def _allowed_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


@api.route('/')
def index():
    """UI landing page."""
    return render_template('index.html')


@api.route('/api/v1/document/jobs', methods=['POST'])
def create_extraction_job():
    """
    Create a document extraction job.
    Accepts multipart form data with:
    - file: the document file (PDF or image)
    - documentType: invoice | purchaseOrder | paymentAdvice (optional, auto-detect if omitted)
    - lang: OCR language (default: eng+tur)

    Returns a job ID for polling results.
    Compatible with SAP Document AI API structure.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file provided", "code": "NO_FILE"}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({"error": "Empty filename", "code": "EMPTY_FILENAME"}), 400

    if not _allowed_file(file.filename):
        return jsonify({
            "error": f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
            "code": "UNSUPPORTED_TYPE"
        }), 400

    doc_type = request.form.get('documentType', 'invoice')
    lang = request.form.get('lang', 'eng+tur')

    if doc_type not in EXTRACTORS:
        return jsonify({
            "error": f"Unknown document type: {doc_type}. Supported: {', '.join(EXTRACTORS.keys())}",
            "code": "UNKNOWN_DOC_TYPE"
        }), 400

    job_id = str(uuid.uuid4())
    file_bytes = file.read()
    filename = file.filename

    # Process synchronously (for local use, no queue needed)
    try:
        extraction_data = TextExtractor.extract_from_bytes(file_bytes, filename, lang=lang)
        text = extraction_data["text"]
        tables = extraction_data.get("tables", [])

        extractor = EXTRACTORS[doc_type]
        result = extractor.extract(text, tables)

        _jobs[job_id] = {
            "id": job_id,
            "status": "DONE",
            "fileName": filename,
            "documentType": doc_type,
            "createdAt": datetime.utcnow().isoformat(),
            "result": result,
            "rawText": text,
        }
    except Exception as e:
        _jobs[job_id] = {
            "id": job_id,
            "status": "FAILED",
            "fileName": filename,
            "documentType": doc_type,
            "createdAt": datetime.utcnow().isoformat(),
            "error": str(e),
        }

    return jsonify({"id": job_id, "status": _jobs[job_id]["status"]}), 201


@api.route('/api/v1/document/jobs/<job_id>', methods=['GET'])
def get_job_result(job_id):
    """Get extraction job result by ID."""
    if job_id not in _jobs:
        return jsonify({"error": "Job not found", "code": "NOT_FOUND"}), 404
    return jsonify(_jobs[job_id])


@api.route('/api/v1/document/jobs', methods=['GET'])
def list_jobs():
    """List all extraction jobs."""
    jobs = [
        {"id": j["id"], "status": j["status"], "fileName": j["fileName"],
         "documentType": j["documentType"], "createdAt": j["createdAt"]}
        for j in _jobs.values()
    ]
    return jsonify({"jobs": jobs, "count": len(jobs)})


@api.route('/api/v1/document/extract', methods=['POST'])
def extract_sync():
    """
    Synchronous extraction endpoint - returns results immediately.
    Same parameters as /jobs but returns result directly.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file provided", "code": "NO_FILE"}), 400

    file = request.files['file']
    if not file.filename or not _allowed_file(file.filename):
        return jsonify({"error": "Invalid or unsupported file", "code": "INVALID_FILE"}), 400

    doc_type = request.form.get('documentType', 'invoice')
    lang = request.form.get('lang', 'eng+tur')

    if doc_type not in EXTRACTORS:
        return jsonify({"error": f"Unknown document type: {doc_type}"}), 400

    try:
        file_bytes = file.read()
        extraction_data = TextExtractor.extract_from_bytes(file_bytes, file.filename, lang=lang)
        text = extraction_data["text"]
        tables = extraction_data.get("tables", [])

        extractor = EXTRACTORS[doc_type]
        result = extractor.extract(text, tables)
        result["rawText"] = text
        result["fileName"] = file.filename

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "status": "FAILED"}), 500


@api.route('/api/v1/document/text', methods=['POST'])
def extract_text_only():
    """Extract only raw text from a document (no field parsing)."""
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
    """List supported document types and capabilities."""
    return jsonify({
        "service": "Local Document AI",
        "version": "1.0.0",
        "description": "SAP Document AI compatible local extraction service",
        "supportedDocumentTypes": list(EXTRACTORS.keys()),
        "supportedFileTypes": list(ALLOWED_EXTENSIONS),
        "supportedLanguages": ["eng", "tur", "deu", "fra"],
        "features": [
            "PDF text extraction",
            "Image OCR (Tesseract)",
            "Table extraction from PDFs",
            "Invoice header & line item extraction",
            "Purchase order extraction",
            "Payment advice extraction",
            "Turkish & English document support",
        ],
    })

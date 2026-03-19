#!/usr/bin/env python3
"""
Local Document AI Service
=========================
SAP Document AI (Document Information Extraction) compatible local service.

Supports:
- Invoice (Fatura) extraction
- Purchase Order (Satınalma Siparişi) extraction
- Payment Advice (Ödeme Bildirimi) extraction

Usage:
    python app.py                    # Start web server on port 5000
    python app.py --port 8080        # Custom port
    python app.py --file invoice.pdf # CLI mode - extract from file
"""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_server(host: str = "0.0.0.0", port: int = 5000, debug: bool = True):
    """Start the Flask web server."""
    from flask import Flask
    from api.routes import api

    app = Flask(__name__, template_folder="templates")
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
    app.register_blueprint(api)

    print(f"""
╔══════════════════════════════════════════════════════╗
║          Local Document AI Service v1.0.0            ║
║──────────────────────────────────────────────────────║
║  SAP Document AI compatible local extraction         ║
║                                                      ║
║  Web UI:    http://{host}:{port}/                     ║
║  API Docs:  http://{host}:{port}/api/v1/capabilities  ║
║                                                      ║
║  Endpoints:                                          ║
║    POST /api/v1/document/extract  (sync)             ║
║    POST /api/v1/document/jobs     (async)            ║
║    GET  /api/v1/document/jobs/:id (result)           ║
║    POST /api/v1/document/text     (text only)        ║
║    GET  /api/v1/capabilities      (info)             ║
╚══════════════════════════════════════════════════════╝
""")
    app.run(host=host, port=port, debug=debug)


def run_cli(file_path: str, doc_type: str = "invoice", lang: str = "eng+tur"):
    """CLI mode - extract from a file and print JSON result."""
    from extractors.text_extractor import TextExtractor
    from extractors.invoice_extractor import InvoiceExtractor
    from extractors.purchase_order_extractor import PurchaseOrderExtractor
    from extractors.payment_advice_extractor import PaymentAdviceExtractor

    extractors = {
        "invoice": InvoiceExtractor(),
        "purchaseOrder": PurchaseOrderExtractor(),
        "paymentAdvice": PaymentAdviceExtractor(),
    }

    if doc_type not in extractors:
        print(f"Error: Unknown document type '{doc_type}'. Supported: {', '.join(extractors.keys())}")
        sys.exit(1)

    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    print(f"Extracting from: {file_path}")
    print(f"Document type: {doc_type}")
    print(f"OCR language: {lang}")
    print("-" * 50)

    extraction_data = TextExtractor.extract(file_path, lang=lang)
    text = extraction_data["text"]
    tables = extraction_data.get("tables", [])

    extractor = extractors[doc_type]
    result = extractor.extract(text, tables)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Local Document AI Service - SAP Document AI compatible"
    )
    parser.add_argument('--file', '-f', help='Extract from file (CLI mode)')
    parser.add_argument('--type', '-t', default='invoice',
                        choices=['invoice', 'purchaseOrder', 'paymentAdvice'],
                        help='Document type (default: invoice)')
    parser.add_argument('--lang', '-l', default='eng+tur',
                        help='OCR language (default: eng+tur)')
    parser.add_argument('--port', '-p', type=int, default=5000,
                        help='Server port (default: 5000)')
    parser.add_argument('--host', default='0.0.0.0',
                        help='Server host (default: 0.0.0.0)')
    parser.add_argument('--no-debug', action='store_true',
                        help='Disable Flask debug mode')

    args = parser.parse_args()

    if args.file:
        run_cli(args.file, args.type, args.lang)
    else:
        run_server(args.host, args.port, debug=not args.no_debug)


if __name__ == '__main__':
    main()

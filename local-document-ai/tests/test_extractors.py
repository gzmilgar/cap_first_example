"""
Unit tests for document extractors.
Tests with sample invoice/PO/payment text.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractors.invoice_extractor import InvoiceExtractor
from extractors.purchase_order_extractor import PurchaseOrderExtractor
from extractors.payment_advice_extractor import PaymentAdviceExtractor
from extractors.base_extractor import BaseDocumentExtractor
from extractors.schema_manager import SchemaManager
from extractors.template_manager import TemplateManager
from extractors.dynamic_extractor import DynamicExtractor


SAMPLE_INVOICE_TR = """
ABC Ticaret A.Ş.
Vergi Kimlik No: 1234567890

FATURA
Fatura No: FTR-2024-001234
Fatura Tarihi: 15.03.2024
Vade Tarihi: 15.04.2024

Müşteri: XYZ Ltd. Şti.
Vergi Kimlik No: 0987654321

Açıklama             Miktar    Birim Fiyat    Tutar
Laptop HP ProBook    5         15.000,00      75.000,00
Mouse Logitech       10        250,00         2.500,00
Klavye Mekanik       10        500,00         5.000,00

Ara Toplam: 82.500,00
KDV Oranı: %20
KDV Tutarı: 16.500,00
Genel Toplam: 99.000,00 TL
"""

SAMPLE_INVOICE_EN = """
INVOICE
Invoice Number: INV-2024-5678
Invoice Date: 2024-03-15
Due Date: 2024-04-15

Vendor: Global Tech Inc.
Customer: Local Corp Ltd.

Description          Quantity   Unit Price   Amount
Server Rack Unit     2          5,000.00     10,000.00
Network Cable 10m    50         25.00        1,250.00

Subtotal: 11,250.00
Tax Amount: 2,250.00
Grand Total: 13,500.00 USD
"""

SAMPLE_PO = """
SATIN ALMA SİPARİŞİ
Sipariş No: PO-2024-9876
Sipariş Tarihi: 01.02.2024
Teslimat Tarihi: 15.03.2024

Alıcı: ABC Holding A.Ş.
Tedarikçi: DEF Malzeme Ltd.

Ödeme Koşulları: 30 gün vadeli

Genel Toplam: 45.000,00 TL
"""

SAMPLE_PAYMENT = """
ÖDEME BİLDİRİMİ
Ödeme Bildirimi No: PAY-2024-111
Ödeme Tarihi: 20.03.2024

Ödeyen: ABC Ticaret A.Ş.
Alıcı: DEF Tedarik Ltd.
Banka: Garanti BBVA
IBAN: TR330006100519786457841326

Ödeme Tutarı: 99.000,00 TL
Ödeme Yöntemi: Havale/EFT
"""


class TestBaseExtractor(unittest.TestCase):

    def test_parse_amount_turkish(self):
        self.assertAlmostEqual(BaseDocumentExtractor.parse_amount("15.000,00"), 15000.0)
        self.assertAlmostEqual(BaseDocumentExtractor.parse_amount("1.234.567,89"), 1234567.89)

    def test_parse_amount_english(self):
        self.assertAlmostEqual(BaseDocumentExtractor.parse_amount("15,000.00"), 15000.0)
        self.assertAlmostEqual(BaseDocumentExtractor.parse_amount("1,234,567.89"), 1234567.89)

    def test_parse_amount_simple(self):
        self.assertAlmostEqual(BaseDocumentExtractor.parse_amount("250"), 250.0)
        self.assertAlmostEqual(BaseDocumentExtractor.parse_amount("99.50"), 99.50)

    def test_extract_dates(self):
        text = "Tarih: 15.03.2024 ve 01/02/2024"
        dates = BaseDocumentExtractor.extract_dates(text)
        self.assertTrue(len(dates) >= 2)

    def test_extract_tax_id(self):
        text = "Vergi Kimlik No: 1234567890"
        tax_id = BaseDocumentExtractor.extract_tax_id(text)
        self.assertEqual(tax_id, "1234567890")


class TestInvoiceExtractor(unittest.TestCase):

    def setUp(self):
        self.extractor = InvoiceExtractor()

    def test_turkish_invoice_header(self):
        result = self.extractor.extract(SAMPLE_INVOICE_TR)
        header = result["headerFields"]

        self.assertEqual(header["invoiceNumber"], "FTR-2024-001234")
        self.assertEqual(header["customerName"], "XYZ Ltd. Şti.")
        self.assertEqual(header["currency"], "TRY")
        self.assertAlmostEqual(header["totalAmount"], 99000.0)
        self.assertAlmostEqual(header["taxAmount"], 16500.0)
        self.assertEqual(header["taxRate"], 20)

    def test_english_invoice_header(self):
        result = self.extractor.extract(SAMPLE_INVOICE_EN)
        header = result["headerFields"]

        self.assertEqual(header["invoiceNumber"], "INV-2024-5678")
        self.assertEqual(header["vendorName"], "Global Tech Inc.")
        self.assertEqual(header["customerName"], "Local Corp Ltd.")
        self.assertEqual(header["currency"], "USD")
        self.assertAlmostEqual(header["totalAmount"], 13500.0)

    def test_confidence_score(self):
        result = self.extractor.extract(SAMPLE_INVOICE_TR)
        self.assertGreater(result["confidence"], 0)
        self.assertLessEqual(result["confidence"], 1.0)

    def test_status(self):
        result = self.extractor.extract(SAMPLE_INVOICE_TR)
        self.assertEqual(result["status"], "DONE")
        self.assertEqual(result["documentType"], "invoice")


class TestPurchaseOrderExtractor(unittest.TestCase):

    def setUp(self):
        self.extractor = PurchaseOrderExtractor()

    def test_po_header(self):
        result = self.extractor.extract(SAMPLE_PO)
        header = result["headerFields"]

        self.assertEqual(header["poNumber"], "PO-2024-9876")
        self.assertEqual(header["buyerName"], "ABC Holding A.Ş.")
        self.assertEqual(header["supplierName"], "DEF Malzeme Ltd.")
        self.assertEqual(header["currency"], "TRY")
        self.assertAlmostEqual(header["totalAmount"], 45000.0)


class TestPaymentAdviceExtractor(unittest.TestCase):

    def setUp(self):
        self.extractor = PaymentAdviceExtractor()

    def test_payment_header(self):
        result = self.extractor.extract(SAMPLE_PAYMENT)
        header = result["headerFields"]

        self.assertEqual(header["paymentAdviceNumber"], "PAY-2024-111")
        self.assertEqual(header["payerName"], "ABC Ticaret A.Ş.")
        self.assertEqual(header["bankName"], "Garanti BBVA")
        self.assertIn("TR33", header["iban"])
        self.assertEqual(header["currency"], "TRY")
        self.assertAlmostEqual(header["totalAmount"], 99000.0)
        self.assertEqual(header["paymentMethod"], "Havale/EFT")


class TestSchemaManager(unittest.TestCase):

    def setUp(self):
        import tempfile
        self.tmpdir = tempfile.mkdtemp()
        self.manager = SchemaManager(schemas_dir=self.tmpdir)

    def test_default_schemas_created(self):
        schemas = self.manager.list_schemas()
        self.assertTrue(len(schemas) >= 3)
        ids = [s["id"] for s in schemas]
        self.assertIn("invoice_default", ids)
        self.assertIn("purchase_order_default", ids)
        self.assertIn("payment_advice_default", ids)

    def test_create_custom_schema(self):
        schema = self.manager.create_schema({
            "name": "Test Schema",
            "documentType": "test",
            "headerFields": [
                {"name": "field1", "label": "Field 1", "type": "string", "required": True}
            ],
            "lineItemFields": [],
        })
        self.assertEqual(schema["name"], "Test Schema")
        self.assertFalse(schema["builtIn"])

        fetched = self.manager.get_schema(schema["id"])
        self.assertEqual(fetched["name"], "Test Schema")

    def test_delete_custom_schema(self):
        schema = self.manager.create_schema({"name": "To Delete", "headerFields": []})
        self.assertTrue(self.manager.delete_schema(schema["id"]))
        self.assertIsNone(self.manager.get_schema(schema["id"]))

    def test_cannot_delete_builtin(self):
        with self.assertRaises(ValueError):
            self.manager.delete_schema("invoice_default")

    def test_duplicate_schema(self):
        dup = self.manager.duplicate_schema("invoice_default", "My Invoice Copy")
        self.assertIsNotNone(dup)
        self.assertEqual(dup["name"], "My Invoice Copy")
        self.assertFalse(dup["builtIn"])
        self.assertNotEqual(dup["id"], "invoice_default")


class TestTemplateManager(unittest.TestCase):

    def setUp(self):
        import tempfile
        self.tmpdir = tempfile.mkdtemp()
        self.manager = TemplateManager(templates_dir=self.tmpdir)

    def test_default_templates_created(self):
        templates = self.manager.list_templates()
        self.assertTrue(len(templates) >= 3)

    def test_filter_by_schema(self):
        templates = self.manager.list_templates(schema_id="invoice_default")
        self.assertTrue(all(t["schemaId"] == "invoice_default" for t in templates))

    def test_create_custom_template(self):
        tmpl = self.manager.create_template({
            "name": "Test Template",
            "schemaId": "invoice_default",
            "headerRules": {
                "invoiceNumber": {
                    "method": "regex",
                    "patterns": ["No:\\s*(\\w+)"],
                    "postProcess": "trim"
                }
            },
        })
        self.assertEqual(tmpl["name"], "Test Template")
        self.assertFalse(tmpl["builtIn"])


class TestDynamicExtractor(unittest.TestCase):

    def setUp(self):
        import tempfile
        self.schema_dir = tempfile.mkdtemp()
        self.template_dir = tempfile.mkdtemp()
        self.schema_mgr = SchemaManager(schemas_dir=self.schema_dir)
        self.template_mgr = TemplateManager(templates_dir=self.template_dir)
        self.extractor = DynamicExtractor(self.schema_mgr, self.template_mgr)

    def test_invoice_extraction_with_default_schema_template(self):
        result = self.extractor.extract(
            SAMPLE_INVOICE_TR,
            schema_id="invoice_default",
            template_id="invoice_tr_standard"
        )
        self.assertEqual(result["status"], "DONE")
        self.assertEqual(result["headerFields"]["invoiceNumber"], "FTR-2024-001234")
        self.assertAlmostEqual(result["headerFields"]["totalAmount"], 99000.0)
        self.assertEqual(result["headerFields"]["currency"], "TRY")
        self.assertGreater(result["confidence"], 0.3)

    def test_po_extraction_with_default_schema_template(self):
        result = self.extractor.extract(
            SAMPLE_PO,
            schema_id="purchase_order_default",
            template_id="po_tr_standard"
        )
        self.assertEqual(result["headerFields"]["poNumber"], "PO-2024-9876")
        self.assertAlmostEqual(result["headerFields"]["totalAmount"], 45000.0)

    def test_payment_extraction_with_default_schema_template(self):
        result = self.extractor.extract(
            SAMPLE_PAYMENT,
            schema_id="payment_advice_default",
            template_id="payment_tr_standard"
        )
        self.assertEqual(result["headerFields"]["paymentAdviceNumber"], "PAY-2024-111")
        self.assertEqual(result["headerFields"]["payerName"], "ABC Ticaret A.Ş.")

    def test_auto_detect_template(self):
        template_id = self.extractor.auto_detect_template(SAMPLE_INVOICE_TR, "invoice_default")
        self.assertIsNotNone(template_id)

    def test_schema_template_mismatch_raises(self):
        with self.assertRaises(ValueError):
            self.extractor.extract(
                SAMPLE_INVOICE_TR,
                schema_id="invoice_default",
                template_id="po_tr_standard"
            )

    def test_extraction_details(self):
        result = self.extractor.extract(
            SAMPLE_INVOICE_TR,
            schema_id="invoice_default",
            template_id="invoice_tr_standard"
        )
        details = result["extractionDetails"]
        self.assertIn("totalFields", details)
        self.assertIn("extractedFields", details)
        self.assertIn("requiredFields", details)
        self.assertIn("foundRequired", details)
        self.assertGreater(details["extractedFields"], 0)


if __name__ == '__main__':
    unittest.main()

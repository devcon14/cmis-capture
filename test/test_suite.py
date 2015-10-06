import re
import yaml
import os
import shutil
from flow import CaptureFlow, BarcodeFlow, recursive_transforms
from flow import OCRFlow, PDFTextFlow
from processing import tr_png, tr_zxing, maketr_get_field_zones
from processing import tr_tesseract_txt
from cmislib import CmisClient


class ExampleBarcodeFlow(CaptureFlow):

    def transform_document(self, document_absolutepath):
        recursive_transforms(document_absolutepath, [tr_png, tr_zxing])
        recursive_transforms(document_absolutepath, [tr_png, maketr_get_field_zones(self.settings["field_zones"]), tr_zxing])


class ExampleOCRFlow(OCRFlow):

    def extract_field(self, zone_info, field_zones_dir):
        extracted_txt = ""
        ocr_txt = self.get_ocr_text(field_zones_dir, engine_name="tr_tesseract_txt")
        m = re.match(r".*\$(\d+\.\d+) .*", ocr_txt)
        if m:
            extracted_txt = m.group(1)
        zone_info["raw_text"] = ocr_txt
        zone_info["text"] = extracted_txt
        self.LOGGER.debug(zone_info)


def setup_func():
    for datadir in ["data-barcode", "data-ocr", "data-pdf-text"]:
        try:
            shutil.rmtree("test/" + datadir)
        except:
            pass
        if os.path.exists("test/" + datadir + "-skeleton"):
            shutil.copytree("test/" + datadir + "-skeleton", "test/" + datadir)


def test_barcode():
    flow = BarcodeFlow("test/barcode.yaml")
    flow.transform_documents()
    for doc_id in os.listdir("test/data-barcode"):
        base_filename = "test/data-barcode/" + doc_id
        with open(base_filename + "/tr_png/tr_zxing/tr_zxing.txt") as fh:
            page_barcode = fh.read()
        with open(base_filename + "/tr_png/get_field_zones_0/tr_zxing/tr_zxing.txt") as fh:
            zone_barcode = fh.read()
        print page_barcode
        if doc_id == "doc001":
            assert '[10,"$",112.435]' in page_barcode
            assert '[10,"$",112.435]' in zone_barcode


def test_ocr():
    flow = ExampleOCRFlow("test/ocr.yaml")
    flow.download_from_cmis()
    flow.transform_documents()
    flow.extract_fields()


def test_pdf_text():
    flow = PDFTextFlow("test/nuxeo_pdf_text.yaml")
    flow.download_from_cmis()
    flow.transform_documents()

if __name__ == "__main__":
    import logging
    with open("logging.yaml") as fh:
        log_settings = yaml.load(fh)
    logging.config.dictConfig(log_settings)
    setup_func()
    test_barcode()
    # test_ocr()
    # test_nuxeo()
    # test_pdf_text()
    print "tests complete"

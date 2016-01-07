import logging
import re
import yaml
import os
import shutil
from flow import CaptureFlow, recursive_transforms
from flow import OCRFlow, PDFTextFlow
from processing import tr_png, tr_zxing, maketr_get_field_zones
from processing import tr_tesseract_txt
from cmislib import CmisClient


'''
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
'''


def setup_func():
    for datadir in ["data-excel", "data-nuxeo", "data-advanced", "data-multipage", "data-pdftext"]:
        try:
            shutil.rmtree("test/" + datadir)
        except:
            pass
        if os.path.exists("test/" + datadir + "-skeleton"):
            shutil.copytree("test/" + datadir + "-skeleton", "test/" + datadir)


def test_nuxeo():
    flow = OCRFlow("test/nuxeo_demo.yaml")
    flow.download_from_cmis()
    flow.transform_documents()
    flow.extract_fields()


def test_excel():
    # flow = ExampleOCRFlow("test/excel_demo.yaml")
    flow = OCRFlow("test/excel_demo.yaml")
    flow.download_from_excel()
    flow.transform_documents()
    flow.extract_fields()
    return flow


def test_advanced():
    flow = OCRFlow("test/advanced.yaml")
    # flow = ExampleOCRFlow("test/advanced.yaml")
    flow.download_from_excel()
    flow.transform_documents()
    flow.extract_fields()
    return flow


def test_multipage():
    flow = OCRFlow("test/multipage.yaml")
    flow.download_from_excel()
    flow.transform_documents()
    flow.extract_fields()
    return flow


def test_pdftext():
    # flow = OCRFlow("test/pdftext.yaml")
    flow = OCRFlow("test/edcon.yaml")
    flow.download_from_excel()
    flow.transform_documents()
    return flow


if __name__ == "__main__":
    with open("logging.yaml") as fh:
        log_settings = yaml.load(fh)
    logging.config.dictConfig(log_settings)
    setup_func()
    # flow = test_multipage()
    # flow = test_advanced()
    # flow = test_excel()
    # flow = test_nuxeo()
    flow = test_pdftext()
    print "tests complete"

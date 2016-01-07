import shutil
import sys
import pandas as pd
from urlparse import urlparse
from processing import tr_zxing, get_hocr_zones
from processing import tr_get_pdf_text, maketr_get_field_zones
from processing import tr_png, tr_threshold
from processing import tr_tesseract_txt, tr_tesseract_hocr, tr_cuneiform_txt, tr_ocropus_hocr
from wand.image import Image
import re
import os
import io
from cmislib import CmisClient
import yaml
import json
import logging
import logging.config


def get_action_files(output_folder):
    action_files = []
    for action_file in os.listdir(output_folder):
        action_file_absolute = os.path.join(output_folder, action_file)
        if os.path.isfile(action_file_absolute):
            action_files.append(action_file_absolute)
    if len(action_files) == 1:
        return action_files[0]
    else:
        return action_files


def apply_transforms(next_object, transforms):
    transform_objects = []
    final_outputs = recursive_transforms(next_object, transforms, transform_objects)
    return final_outputs, transform_objects


def recursive_transforms(next_object, transforms, transform_objects):
    if len(transforms) == 0:
        return next_object
    trans = transforms[0]
    # logging.debug(("enter recursion", next_object, trans))
    if hasattr(next_object, "__iter__"):
        iter_objects = []
        for filename_in_list in next_object:
            next_object = transform(filename_in_list, trans)
            result = recursive_transforms(next_object, transforms[1:], transform_objects)
            iter_objects.append(result)
        transform_objects.append(iter_objects)
        return iter_objects
    else:
        transform_objects.append(next_object)
        next_object = transform(next_object, trans)
        filename = next_object
        return recursive_transforms(filename, transforms[1:], transform_objects)


def transform(filename, action):
    output_folder = os.path.join(os.path.dirname(filename), action.__name__)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        logging.debug(("transforming", filename, output_folder))
        return action(filename, output_folder)
    else:
        # logging.debug(("skipping existing transform", filename, output_folder))
        # existing_files = get_action_files(output_folder)
        # return existing_files
        # FIXME checking for the existing output_folder is buggy when there is for instance multipage png outputs
        logging.debug(("running existing transform just in case", filename, output_folder))
        return action(filename, output_folder)


class CaptureFlow:

    def __init__(self, config_file):
        self.LOGGER = logging.getLogger(__name__)
        with open(config_file) as fh:
            self.settings = yaml.load(fh)
        if not os.path.exists(self.settings["datadir"]):
            os.makedirs(self.settings["datadir"])

    def upload_sample_documents(self):
        repo = CmisClient(self.settings["cmis_url"], self.settings["cmis_username"], self.settings["cmis_password"]).defaultRepository
        try:
            repo.getObjectByPath(self.settings["capture_folder"])
            self.LOGGER.debug("Capture folder available")
        except:
            self.LOGGER.debug("CMIS folder not present. Uploading demo files.")
            parent_folder_name = "/".join(self.settings["capture_folder"].split("/")[:-1])
            parent_folder = repo.getObjectByPath(parent_folder_name)
            demoFolder = repo.createFolder(parent_folder, self.settings["capture_folder"].split("/")[-1])
            demoFolder.createDocument('Invoice01.pdf', contentFile=open("test/data-barcode-skeleton/doc001/Invoice01.pdf"))
            demoFolder.createDocument('Invoice02.pdf', contentFile=open("test/data-barcode-skeleton/doc002/Invoice02.pdf"))

    def download_from_cmis(self):
        if "cmis_url" not in self.settings:
            self.LOGGER.warn("No CMIS repo specified. Processing documents is datadir.")
            return
        repo = CmisClient(self.settings["cmis_url"], self.settings["cmis_username"], self.settings["cmis_password"]).defaultRepository
        for document in repo.getObjectByPath(self.settings["capture_folder"]).getChildren():
            document_name = document.getName()
            docid = document.getObjectId()
            docid = docid.replace("workspace://SpacesStore/", "")
            # remove version identifier ;1.0
            if ";" in docid:
                docid = docid.split(";")[0]
            document_workdir = os.path.join(self.settings["datadir"], docid)
            if not os.path.exists(document_workdir):
                os.makedirs(document_workdir)
            local_document_path = os.path.join(document_workdir, document_name)
            if os.path.exists(local_document_path):
                self.LOGGER.debug("{} exists. skipping download from CMIS".format(local_document_path))
            else:
                self.LOGGER.debug("downloading {}".format(document_name))
                with open(local_document_path, "w") as fh:
                    fh.write(document.getContentStream().read())

    def download_from_excel(self):
        if "excel_file" not in self.settings:
            self.LOGGER.warn("No excel file. Skipping excel download.")
            return
        df = pd.read_excel(self.settings["excel_file"])
        for docid, row in df.iterrows():
            document_name = os.path.basename(row["location"])
            document_workdir = os.path.join(self.settings["datadir"], str(docid))
            if not os.path.exists(document_workdir):
                os.makedirs(document_workdir)
            local_document_path = os.path.join(document_workdir, document_name)
            if os.path.exists(local_document_path):
                self.LOGGER.debug("{} exists. skipping download from Excel".format(local_document_path))
            else:
                self.LOGGER.debug("downloading {}".format(document_name))
                shutil.copy(row["location"], local_document_path)

    def transform_document(self, document_absolutepath):
        recursive_transforms(document_absolutepath, [tr_png])

    def transform_documents(self):
        for doc_id in os.listdir(self.settings["datadir"]):
            document_workdir = os.path.join(self.settings["datadir"], doc_id)
            # avoid master.js files in data
            if os.path.isdir(document_workdir):
                for document_filename in os.listdir(document_workdir):
                    document_absolutepath = os.path.join(document_workdir, document_filename)
                    # process any file that isn't json, should be pdf or image
                    if os.path.isfile(document_absolutepath) and not document_filename.endswith(".json"):
                        logging.info(document_filename)
                        self.transform_document(document_absolutepath)

    def build_repo_url(self, doc_id):
        if "cmis_url" in self.settings:
            parsed_uri = urlparse(self.settings["cmis_url"])
            if "nuxeo" in self.settings["cmis_url"]:
                return "{}://{}/nuxeo/nxfile/default/{}/blobholder:0/".format(parsed_uri.scheme, parsed_uri.netloc, doc_id)
            elif "alfresco" in self.settings["cmis_url"]:
                return "{}://{}/share/page/document-details?nodeRef=workspace://SpacesStore/{}".format(parsed_uri.scheme, parsed_uri.netloc, doc_id)
        else:
            # TODO provide an internal pdf.js viewer, built on top of hocr2pdf
            # TODO excel URL
            return ""

    '''
    def load_field_zone(self, field_zones_dir):
        for fzone in os.listdir(field_zones_dir):
            if fzone.endswith(".json"):
                with io.open(os.path.join(field_zones_dir, fzone), encoding="utf8") as fh:
                    zone_info = json.loads(fh.read())
                zone_info["text"] = ""
                # modify local path to reflect REST path
                zone_info["image"] = zone_info["image"].replace(self.settings["datadir"], "data")
                return zone_info

    def get_ocr_text(self, field_zones_dir, engine_name="tr_tesseract_txt"):
        ocr_txt_filename = os.path.join(field_zones_dir, "{0}/{0}.txt".format(engine_name))
        # self.LOGGER.debug(ocr_txt_filename)
        if os.path.exists(ocr_txt_filename):
            with open(ocr_txt_filename) as fh:
                ocr_txt = fh.read()
                self.LOGGER.debug(("ocr", ocr_txt))
            return ocr_txt
        else:
            return ""
    '''

    def extract_fields(self, frame_start=0, frame_end=20):
        self.LOGGER.debug("loading frame from {} to {}".format(frame_start, frame_end))
        field_zones = []
        doc_ids = os.listdir(self.settings["datadir"])[frame_start:frame_end]
        for row_index, doc_id in enumerate(doc_ids):
            # self.LOGGER.debug(("row", row_index))
            document_workdir = os.path.join(self.settings["datadir"], doc_id)
            # avoid master.js files in data
            if os.path.isdir(document_workdir):
                with io.open(document_workdir + "/info/document.json", encoding="utf8") as fh:
                    json_text = fh.read()
                    document_zones = json.loads(json_text)
                    for document_zone in document_zones:
                        document_zone["repo_url"] = self.build_repo_url(doc_id)
                        document_zone["doc_id"] = doc_id
                        # modify local path to reflect REST path
                        document_zone["image"] = document_zone["image"].replace(self.settings["datadir"], "data")
                        if "hidden" in document_zone:
                            logging.info((document_zone, "hidden field"))
                        else:
                            field_zones.append(document_zone)
        with open(os.path.join(self.settings["datadir"], "field_zones.json"), "w") as fh:
            fh.write(json.dumps(field_zones))
        with open(os.path.join(self.settings["datadir"], "field_zones.js"), "w") as fh:
            fh.write("var regions = \n")
            fh.write(json.dumps(field_zones))


class OCRFlow(CaptureFlow):

    def extract_ocr(self, ocr_output, out_zone, zone_info):
        with io.open(ocr_output, encoding="utf8") as fh:
            out_zone["ocr_text"] = fh.read()
            out_zone["text"] = out_zone["ocr_text"]
        if "regex" in zone_info:
            m = re.match(zone_info["regex"], out_zone["ocr_text"])
            if m:
                out_zone["text"] = m.group(1)
        logging.debug(("new zone extract", out_zone))

    def transform_document(self, document_absolutepath):
        if "pdftext" in self.settings:
            pages, _ = apply_transforms(document_absolutepath, [tr_get_pdf_text])
        if ("page-0") not in self.settings:
            return
        pages, _ = apply_transforms(document_absolutepath, [tr_png])
        if isinstance(pages, basestring):
            pages = [pages]
        zones = []
        for page_number, page in enumerate(pages):
            if not "page-{}".format(page_number) in self.settings:
                logging.warn("no zones defined for page {}".format(page_number))
                continue
            field_zones = self.settings["page-{}".format(page_number)]["field_zones"]
            zone_images, _ = apply_transforms(page, [maketr_get_field_zones(field_zones, page_number)])
            for index, field_zone in enumerate(zone_images):
                zone_settings = self.settings["page-{}".format(page_number)]["field_zones"][index]
                field_zones_dir = os.path.dirname(field_zone)
                out_zone = {}
                out_zone["field_name"] = zone_settings["field_name"]
                out_zone["repo_name"] = zone_settings["repo_name"]
                out_zone["image"] = field_zones_dir + "/get_field_zones.png"
                if "hidden" in zone_settings:
                    out_zone["hidden"] = ""
                logging.debug(field_zones_dir)
                if zone_settings["extractor"]["class"] == "OCR":
                    ocr_transform_paths = []
                    ocr_output = recursive_transforms(field_zone, [tr_tesseract_txt], ocr_transform_paths)
                    self.extract_ocr(ocr_output, out_zone, zone_settings)
                if zone_settings["extractor"]["class"] == "Barcode":
                    barcode_transform_paths = []
                    zxing_output = recursive_transforms(field_zone, [tr_zxing], barcode_transform_paths)
                    logging.debug("ZXING: " + zxing_output)
                    with open(zxing_output) as fh:
                        lines = fh.readlines()
                        barcode_text = lines[2]
                        barcode_dict = json.loads(barcode_text)
                        out_zone["text"] = barcode_text
                        logging.debug(barcode_dict)
                zones.append(out_zone)
        # write document info
        info_folder = os.path.join(os.path.dirname(document_absolutepath), "info")
        if not os.path.exists(info_folder):
            os.makedirs(info_folder)
        with io.open("{}/document.json".format(info_folder), "w", encoding="utf8") as fh:
            data = json.dumps(zones, ensure_ascii=False)
            logging.debug(data)
            fh.write(unicode(data))


class PDFTextFlow(CaptureFlow):

    def transform_document(self, document_absolutepath):
        recursive_transforms(document_absolutepath, [tr_get_pdf_text])

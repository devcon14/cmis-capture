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


def recursive_transforms(next_object, transforms, transform_objects):
    # TODO allow applying an extractor method to the final transform
    # method will update a dictionary
    if len(transforms) == 0:
        return next_object
    trans = transforms[0]
    logging.debug(("enter recursion", next_object, trans))
    if hasattr(next_object, "__iter__"):
        iter_objects = []
        for filename_in_list in next_object:
            logging.info(filename_in_list)
            next_object = transform(filename_in_list, trans)
            # logging.debug(("in iter transform", next_object))
            # result = recursive_transforms(filename_in_list, transforms[1:], transform_objects)
            result = recursive_transforms(next_object, transforms[1:], transform_objects)
            logging.debug(result)
            iter_objects.append(result)
        # transforms.pop(0)
        transform_objects.append(iter_objects)
        return iter_objects
    else:
        # transforms.pop(0)
        transform_objects.append(next_object)
        next_object = transform(next_object, trans)
        filename = next_object
        # logging.debug(filename)
        return recursive_transforms(filename, transforms[1:], transform_objects)


def transform(filename, action):
    output_folder = os.path.join(os.path.dirname(filename), action.__name__)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        logging.debug(("transforming", filename, output_folder))
        return action(filename, output_folder)
    else:
        logging.debug(("skipping existing transform", output_folder))
        existing_files = get_action_files(output_folder)
        # logging.debug((list(action_files), list(act2)))
        return existing_files


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

        self.df = df

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

    def extract_field(self, zone_info, field_zones_dir):
        """Main customizable extraction method.
        """
        return zone_info

    def extract_fields(self, frame_start=0, frame_end=20):
        self.LOGGER.debug("loading frame from {} to {}".format(frame_start, frame_end))
        field_zones = []
        doc_ids = os.listdir(self.settings["datadir"])[frame_start:frame_end]
        for row_index, doc_id in enumerate(doc_ids):
            # self.LOGGER.debug(("row", row_index))
            document_workdir = os.path.join(self.settings["datadir"], doc_id)
            # avoid master.js files in data
            if os.path.isdir(document_workdir):
                png_folder = os.path.join(document_workdir, "tr_png")
                for document_subfolder in os.listdir(png_folder):
                    if document_subfolder.startswith("get_field_zones_"):
                        field_zones_dir = os.path.join(png_folder, document_subfolder)
                        zone_info = self.load_field_zone(field_zones_dir)
                        zone_info["repo_url"] = self.build_repo_url(doc_id)
                        zone_info["doc_id"] = doc_id
                        # self.LOGGER.debug("Extracting field" + document_subfolder)
                        zone_info = self.extract_field(zone_info, field_zones_dir)
                        field_zones.append(zone_info)
        with open(os.path.join(self.settings["datadir"], "field_zones.json"), "w") as fh:
            fh.write(json.dumps(field_zones))
        with open(os.path.join(self.settings["datadir"], "field_zones.js"), "w") as fh:
            fh.write("var regions = \n")
            fh.write(json.dumps(field_zones))


class BarcodeFlow(CaptureFlow):

    def transform_document(self, document_absolutepath):
        recursive_transforms(document_absolutepath, [tr_png, tr_zxing])
        recursive_transforms(document_absolutepath, [tr_png, maketr_get_field_zones(self.settings["field_zones"]), tr_zxing])


class OCRFlow(CaptureFlow):

    def transform_document(self, document_absolutepath):
        # FIXME extra tr_png to debug with
        transform_paths = []
        end_result = recursive_transforms(document_absolutepath, [tr_png, maketr_get_field_zones(self.settings["field_zones"]), tr_png, tr_tesseract_txt], transform_paths)
        logging.debug(("result tr", transform_paths, end_result))


class DemoFlow(OCRFlow):

    def extract_field(self, zone_info, field_zones_dir):
        zone_info["text"] = self.get_ocr_text(field_zones_dir)
        zone_info = self.regex_filter(zone_info)
        logging.info(zone_info)
        return zone_info

    def regex_filter(self, zone_info):
        if (zone_info["field_name"] == "Sub Total"):
            m = re.match(r".*Total \$(\d+\.\d+).*", zone_info["text"])
            if m:
                logging.info(("match total", m.groups(1)))
                zone_info["text"] = m.groups(1)
                return zone_info
        if (zone_info["field_name"] == "Invoice Number"):
            m = re.match(r".*Invoice #(\d+).*", zone_info["text"])
            if m:
                logging.info(("match invno", m.groups(1)))
                zone_info["text"] = m.groups(1)
                return zone_info
        return zone_info


class PDFTextFlow(CaptureFlow):

    def transform_document(self, document_absolutepath):
        recursive_transforms(document_absolutepath, [tr_get_pdf_text])

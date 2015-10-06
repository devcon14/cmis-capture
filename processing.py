# http://www.danvk.org/2015/01/09/extracting-text-from-an-image-using-ocropus.html
# for character level confidence
# https://github.com/tmbdev/ocropy/pull/25
import io
import json
import os
import subprocess
from wand.image import Image
import logging
from PIL import Image as PillowImage
from bs4 import BeautifulSoup
from pdfminer_transform import PdfminerTransform
from os.path import expanduser
import urllib


def tr_get_pdf_text(pdf_filename_absolute, pdfminer_folder):
    LOGGER = logging.getLogger(__name__)
    # processing_folder = os.path.dirname(pdf_filename_absolute)
    pdf_filename = os.path.basename(pdf_filename_absolute)
    transformer = PdfminerTransform()
    text_filename = pdfminer_folder + "/" + pdf_filename + ".txt"
    html_filename = pdfminer_folder + "/" + pdf_filename + ".html"
    pdf_dict = transformer.transform_file(pdf_filename_absolute)
    # LOGGER.debug(pdf_dict)
    if "markup" in pdf_dict:
        with io.open(html_filename, "w", encoding="utf8") as f:
            f.write(pdf_dict["markup"]["innerHTML"])
        with io.open(text_filename, "w", encoding="utf8") as f:
            f.write(unicode(pdf_dict["markup"]["innerText"]))
    else:
        LOGGER.warn("Pdfminer extraction failure.")


def maketr_get_field_zones(zones):
    def get_field_zones(image_filename, output_folder):
        LOGGER = logging.getLogger(__name__)
        LOGGER.info(image_filename)
        image = PillowImage.open(image_filename)
        for index, field_zone in enumerate(zones):
            field_zone_folder = "{0}_{1}".format(output_folder, index)
            if not os.path.exists(field_zone_folder):
                os.makedirs(field_zone_folder)
            zone_percent = field_zone["region"]
            width, height = image.size
            bbox = [
                zone_percent[0] * width / 100,
                zone_percent[1] * height / 100,
                zone_percent[2] * width / 100,
                zone_percent[3] * height / 100
            ]
            zone_image = image.crop(bbox)
            image_path = "{0}/get_field_zones.png".format(field_zone_folder)
            zone_image.save(image_path)
            field_zone["image"] = image_path
            field_zone["text"] = ""
            with io.open("{0}/get_field_zones.json".format(field_zone_folder), "w", encoding="utf8") as fh:
                data = json.dumps(field_zone, ensure_ascii=False)
                fh.write(unicode(data))
                # json.dump(text, fh, ensure_ascii=False)
            yield image_path
    return get_field_zones


def tr_zxing(png_filename, output_folder):
    libs = "extern/zxing/core-3.2.1.jar"
    libs += ":extern/zxing/javase-3.2.1.jar"
    libs += ":extern/zxing/jcommander-1.48.jar"
    png_filename = os.path.abspath(png_filename)
    png_filename = urllib.pathname2url(png_filename)
    command_array = [
        "java",
        "-cp",
        libs,
        "com.google.zxing.client.j2se.CommandLineRunner",
        png_filename,
        "--try_harder"
        # "--crop", "ileft", "top", "width", "height"
    ]
    result = subprocess.check_output(command_array)
    logging.debug(" ".join(command_array))
    logging.info(result)
    with open("{}/tr_zxing.txt".format(output_folder), "w") as fh:
        fh.write(result)


def tr_cuneiform_txt(png_filename, output_folder):
    LOGGER = logging.getLogger(__name__)
    output_filename_absolute = output_folder + "/tr_cuneiform_txt.txt"
    out = subprocess.check_output([
        "cuneiform",
        "-o", output_filename_absolute,
        png_filename
    ])
    LOGGER.debug(out)
    return output_filename_absolute


def tr_cuneiform_hocr(png_filename, output_folder):
    LOGGER = logging.getLogger(__name__)
    output_filename_absolute = output_folder + "/tr_cuneiform_hocr.html"
    out = subprocess.check_output([
        "cuneiform",
        "-f", "hocr",
        "-o", output_filename_absolute,
        png_filename
    ])
    LOGGER.debug(out)
    return output_filename_absolute


def tr_threshold(png_filename, output_folder):
    LOGGER = logging.getLogger(__name__)
    out = subprocess.check_output([
        "ocropus-nlbin",
        png_filename,
        "-o", output_folder
    ])
    LOGGER.debug(out)
    return os.path.join(output_folder, "0001.bin.png")


def tr_png(local_document_path, output_folder):
    with Image(
            filename=local_document_path,
            resolution=200) as img:
        img.compression_quality = 100
        basename = os.path.basename(local_document_path)
        out_filename = os.path.join(output_folder, basename + ".png")
        img.save(filename=out_filename)
        if len(img.sequence) > 1:
            logging.info("multipage {}".format(local_document_path))
        return out_filename


def tr_tesseract_txt(png_absolutepath, output_folder):
    LOGGER = logging.getLogger(__name__)
    hocr_filename = os.path.join(output_folder, "tr_tesseract_txt")
    out = subprocess.check_output([
        "tesseract",
        png_absolutepath,
        hocr_filename
    ])
    LOGGER.debug(out)
    return hocr_filename + ".txt"


def tr_tesseract_hocr(png_absolutepath, output_folder):
    LOGGER = logging.getLogger(__name__)
    hocr_filename = os.path.join(output_folder, "recognition_tesseract")
    out = subprocess.check_output([
        "tesseract",
        png_absolutepath,
        hocr_filename,
        "hocr"
    ])
    LOGGER.debug(out)
    return hocr_filename + ".hocr"


def tr_ocropus_words(png_filename, output_folder):
    LOGGER = logging.getLogger(__name__)
    processing_folder = os.path.dirname(png_filename)
    # layout analysis
    out = subprocess.check_output([
        "ocropus-gpageseg",
        png_filename
    ])
    # predict
    LOGGER.debug(out)
    out = subprocess.check_output([
        "ocropus-rpred",
        "-m", "en-default.pyrnn.gz",
        os.path.join(processing_folder, "0001/*.png")
    ])
    LOGGER.debug(out)


def tr_ocropus_hocr(png_filename, output_folder):
    LOGGER = logging.getLogger(__name__)
    # layout analysis
    out = subprocess.check_output([
        "ocropus-gpageseg",
        png_filename
    ])
    LOGGER.debug(out)
    hocr_filename_absolute = os.path.join(output_folder, "tr_ocropus_hocr.html")
    out = subprocess.check_output([
        "ocropus-hocr",
        png_filename,
        "-o", hocr_filename_absolute
    ])
    LOGGER.debug(out)
    return hocr_filename_absolute


def read_hocr_tesseract(soup, image):
    # hocr actually differs wildly between engines in features used and format
    # TODO with ocropus the attribute is ocr_word, with tesseract it's ocrx_word
    # a few other things seemed to change
    # so much for standards
    for index, word in enumerate(soup.find_all("span", "ocrx_word")):
        logging.info(word)
        # bbox = [int(x) for x in word["title"].split()[1:]]
        bbox = [int(x.replace(";", "")) for x in word["title"].split()[1:5]]
        zone = image.crop(bbox)
        # text = word.span.contents[0]
        if len(word.contents) > 0:
            # text = word.contents[0]
            text = word.text
        else:
            text = ""
        try:
            text = text.replace("/", "")
            region = {
                "id": word["id"],
                "image": word["id"] + ".bin.png",
                "text": unicode(text),
                "width": unicode(zone.size[0]),
                "height": unicode(zone.size[1])
            }
        except Exception as e:
            logging.error(e, exc_info=True)
        yield zone, region


def get_hocr_zones(processing_folder, png_filename, engine="tesseract"):
    image_filename = processing_folder + "/" + png_filename
    logging.info(image_filename)
    image = PillowImage.open(image_filename)
    if engine == "tesseract":
        engine_filename = engine + ".hocr"
    else:
        engine_filename = engine + ".hocr.html"
    hocr_filename = "{0}/{1}/{2}".format(processing_folder, engine, engine_filename)
    soup = BeautifulSoup(open(hocr_filename))
    logging.info("opened " + hocr_filename)
    logging.info(soup.getText())
    regions = []
    for zone, region in read_hocr_tesseract(soup, image):
        regions.append(region)
        # TODO page number folder
        zone.save("{0}/{1}/{2}.bin.png".format(processing_folder, engine, region["id"]))
        with io.open(
                "{0}/{1}/{2}.txt".format(processing_folder, engine, region["id"]),
                "w", encoding="utf8") as fh:
            fh.write(region["text"])
    with io.open(
            "{0}/{1}/master.json".format(processing_folder, engine),
            "w", encoding="utf8") as fh:
        fh.write(u"var regions = \n")
        fh.write(json.dumps(regions, ensure_ascii=False))
    logging.info("Done")


def main():
    pdf_folder = "/shared/projects/seeker/data/oldpdfjs/pdf"
    processing_folder = "/shared/projects/seeker/data/oldpdfjs/ocropus"
    # pdf_to_png(pdf_folder, processing_folder)
    pngs = [f for f in os.listdir(processing_folder) if f.endswith(".png")]
    for png_filename in pngs[:3]:
        ocropus_png(processing_folder, png_filename, make_snippets=True)
        # tesseract_png(processing_folder, png_filename)

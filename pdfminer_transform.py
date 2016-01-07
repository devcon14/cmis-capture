from bs4 import BeautifulSoup
from base_transform import BaseTransform
from subprocess import check_output

from datetime import datetime
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter, HTMLConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from cStringIO import StringIO
import logging


class PdfminerTransform(BaseTransform):

    def __init__(self):
        self.LOGGER = logging.getLogger(__name__)
        # defaults as per: https://euske.github.io/pdfminer/index.html
        self.laparams = LAParams()
        self.laparams.word_margin = 0.2
        self.laparams.line_margin = 0.3
        self.laparams.char_margin = 1.0
        # self.laparams.line_margin = 1.1
        # self.laparams.word_margin = 5.2
        # self.laparams.char_margin = 5.2
        self.laparams.boxes_flow = 0.5
        self.laparams.all_texts = False

    def transform_file(self, pdfpath):
        try:
            self.LOGGER.debug(pdfpath)
            rsrcmgr = PDFResourceManager()
            retstr = StringIO()
            codec = 'utf-8'

            device = HTMLConverter(rsrcmgr, retstr, codec=codec, laparams=self.laparams)
            fp = file(pdfpath, 'rb')
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            password = ""
            maxpages = 0
            caching = True
            pagenos = set()
            # NOTE check_extractable seems to allow overriding text extraction locks
            for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages, password=password, caching=caching, check_extractable=False):
                interpreter.process_page(page)
            fp.close()
            device.close()
            html = retstr.getvalue()
            # otherwise html is str at this point, not unicode
            html = html.decode('utf8')
            retstr.close()
            soup = BeautifulSoup(html)
            # LOGGER.debug(soup.text)
            text_size = len(soup.text)
            stub_data = {
                # "URL": uri,
                "markup": {
                    "innerHTML": unicode(html),
                    "innerText": unicode(soup.text)
                },
                "workflow": {
                    "is_stub": True
                },
                "__text_size": text_size,
                # __fields are ignored by kibana
                "timestamp": datetime.now()
            }
        except Exception as e:
            stub_data = {
                "error": str(e),
                "workflow": {
                    "is_stub": True
                },
                "__text_size": -1
            }
        return stub_data

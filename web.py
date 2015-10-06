import yaml
import cmislib
from cmislib import CmisClient
import os
import json
from flask import Flask
from flask import send_from_directory
from flask import redirect, request
import logging
import logging.config
import sys
from flow import BarcodeFlow, OCRFlow, DemoFlow
flaskapp = Flask(__name__)


def update_cmis(doc_id, cmis_name, text):
    repo = CmisClient(flow.settings["cmis_url"], flow.settings["cmis_username"], flow.settings["cmis_password"]).defaultRepository
    document = repo.getObject(doc_id)
    logging.debug(document)
    update_dict = {}
    update_dict[cmis_name] = text
    logging.debug(update_dict)
    document.updateProperties(update_dict)


@flaskapp.route('/')
def homepage():
    return redirect("/static/index.html", code=302)
    # return flaskapp.send_static_file('index.html')


@flaskapp.route('/static/data/<path:filename>')
def custom_static(filename):
    return send_from_directory(flow.settings["datadir"], filename)


@flaskapp.route("/api/regions/<frame_start>/<frame_end>")
def get_regions(frame_start, frame_end):
    logging.info("getting frame {} to  {}".format(frame_start, frame_end))
    flow.extract_fields(int(frame_start), int(frame_end))
    with open(flow.settings["datadir"] + "/field_zones.json") as fh:
        region_text = fh.read()
    LOGGER.debug(region_text)
    return region_text


@flaskapp.route("/api/<verb>", methods=["GET", "POST"])
def update(verb):
    params = request.get_json()
    logging.info(params)
    update_cmis(params["doc_id"], params["cmis_name"], params["text"])
    params["status"] = "Success"
    return json.dumps(params)


def serve_gevent():
    from gevent.wsgi import WSGIServer
    http_server = WSGIServer(('', 5000), flaskapp)
    http_server.serve_forever()


def serve_flask():
    flaskapp.run(
        host="0.0.0.0",
        port=5000)


if __name__ == "__main__":
    try:
        config_filename = sys.argv[1]
    except:
        config_filename = "test/demo.yaml"
    with open("logging.yaml") as fh:
        log_settings = yaml.load(fh)
    logging.config.dictConfig(log_settings)
    LOGGER = logging.getLogger(__name__)
    LOGGER.info("Logging enabled")
    flaskapp.secret_key = 'super secret key'
    flow = DemoFlow(config_filename)
    flow.upload_sample_documents()
    flow.download_from_cmis()
    flow.transform_documents()
    serve_gevent()
    LOGGER.info("Web server started")

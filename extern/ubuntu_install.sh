# set -e
# apt-get update
apt-get install -y wget python-pip
apt-get install -y imagemagick tesseract-ocr
# ocropus
# sudo apt-get install curl python-tables imagemagick python-opencv firefox
# sudo apt-get install imagemagick tesseract-ocr
# sudo apt-get install tesseract-ocr-eng
# sudo apt-get install cuneiform
# sudo apt-get install ghostscript

# gcc, needed by pyyaml, Pillow
apt-get install -y python-imaging python-yaml
# libjpeg, zlib needed by Pillow
apt-get install -y lib1g-dev zlib1g-dev libpng-dev
apt-get install -y build-essential
pip install -r extern/py_requirements.txt

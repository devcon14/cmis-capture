FROM ubuntu:14.04

COPY . /opt/cmis-capture
WORKDIR /opt/cmis-capture
RUN /opt/cmis-capture/extern/ubuntu_install.sh
RUN /opt/cmis-capture/extern/install_zxing.sh

CMIS Capture
============

Overview
--------

This project aims to provide a robust and simple interface for capturing data from documents on a [CMIS](https://en.wikipedia.org/wiki/Content_Management_Interoperability_Services) repository.

It's still very much in alpha (more for early hackers to try out), but issues and pull requests are welcome.

Some open source [ECMS](https://en.wikipedia.org/wiki/Enterprise_content_management) systems supporting CMIS includes:

* Alfresco
* Nuxeo

Commercial examples include:

* Microsoft Sharepoint
* IBM Content Manager
* SAP

Advantages of the CMIS approach include:

* Use the ECMS to manage batches in folders, with folder properties and ECMS workflow used for batch tracking.
* Utilize the built in ECMS features for loading emails via IMAP or SMTP.
* Utilize built in features for document upload for remote scanning and distributed capture.
* It's possible to have searchable OCR results even before data entry is complete.


Current Capabilities
--------------------

* Editing documents directly on the ECMS.
* Editing documents linked by an excel spreadsheet.
* 1D barcode recognition (Code 128, Code 39, EAN, UPC)
* 2D barcode recognition (Datamatrix, QR)
* Zonal OCR.
* Zonal field capture in the web browser.
* Support for reading PDF, TIFF, JPG and PNG images.
* Extracting embedded text from electronic PDF (as well as by image OCR).

Currently mostly a demo project.
Bieng used to prototype quick tests for internal projects.


Installation
------------

cmis-capture is configured to run from a docker container.

To run from docker hub use:

    docker run --name capture -d -p 5000:5000 devcon/cmis-capture

To build the docker image from source:
    
    docker build -t devcon/cmis-capture .

The Dockerfile references extern/ubuntu_install.sh for installing dependencies if you would like to try a local install.

But it is preferable to install in a virtual environment.

Usage
-----

By default the docker image runs the excel demo as a web service by running:

    python web.py

You can point your browser to http://localhost:5000 to start capturing.

To run a different configuration specify the configuration file eg.

    python web.py test/nuxeo_demo.yaml

The nuxeo_demo.yaml points to an instance of Nuxeo on localhost by default.

You will need to edit this yaml file to point to your own running CMIS repo.


The test subdirectory contains example python code.

Modify the different yaml config files to:

* Point to your own ECMS.
* Configure zone coordinates as a percentage of the page size.

Roadmap
-------

* Larger range of document capture features similar to that of Kofax or ReadSoft.
* Smart form registration.
* Add OCR on the fly.
* Handwriting recognition.
* Machine learning based unstructured data extraction.
* Integrate other engines such as ABBY online SDK.

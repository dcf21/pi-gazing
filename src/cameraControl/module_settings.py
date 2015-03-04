# module_settings.py
# $Id: module_settings.py 1174 2015-02-06 00:48:26Z pyxplot $

import os

PYTHON_PATH = os.path.split( os.path.abspath(__file__) )[0]
BINARY_PATH = os.path.join(PYTHON_PATH , "../videoRec/bin")
I_AM_A_RPI  = os.uname()[4].startswith("arm")
DATA_PATH   = "/mnt/harddisk/pi/meteorCam"


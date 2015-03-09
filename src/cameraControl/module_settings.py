# module_settings.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os

PYTHON_PATH = os.path.split( os.path.abspath(__file__) )[0]
BINARY_PATH = os.path.join(PYTHON_PATH , "../videoRec/bin")
I_AM_A_RPI  = os.uname()[4].startswith("arm")
DATA_PATH   = "/mnt/harddisk/pi/meteorCam"


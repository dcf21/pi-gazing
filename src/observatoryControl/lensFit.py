#!../../virtual-env/bin/python
# lensFit.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Attempt to calculate the barrel distortion of the lens, to produce a better model for correcting recorded images.

# First we run orientationCalc.py. This uses astrometry.net to calculate the orientation of the camera based on recent
# images.

# It also produces a data file listing the 20-50 images used to calculate the orientation, together with the position
# of each image on the sky.

# We then call the program gnomonicStack/bin/camfit. This attempts to stack the 20-50 images, measuring the degree of
# mismatch between the images.

# It tries different barrel distortion coefficients to maximise the degree to which the images overlay one another.

from math import *
import orientationCalc
from mod_settings import *
from mod_time import *

STACKER_PATH = "%s/../gnomonicStack" % PYTHON_PATH

cameraId = my_installation_id()
utcNow = time.time()
if len(sys.argv) > 1:
    cameraId = sys.argv[1]
if len(sys.argv) > 2:
    utcNow = float(sys.argv[2])
imgListFpath = orientationCalc.orientationCalc(cameraId, utcNow, 0)

if not imgListFpath:
    sys.exit(0)

[tmpDir, imgListFname] = os.path.split(imgListFpath)

cwd = os.getcwd()
pid = os.getpid()
os.chdir(tmpDir)

os.system("%s/bin/camfit %s > camFitOutput" % (STACKER_PATH, imgListFname))

camFitOutput = open("camFitOutput").readlines()
camFitLastLine = camFitOutput[-1]

print "Best fitting barrel distortion parameters were:\n%s\n\n" % camFitLastLine

os.chdir(cwd)

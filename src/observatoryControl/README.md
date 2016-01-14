The python scripts in this directory are used in the daily automated cycle of observing.

The main entry point is the shell script `observe.sh`.

This starts two child scripts. `loadMonitor.py` is a background task which flashes two LEDs which may optionally be connected to a Raspberry Pi's GPIO lines. One pulses at varying speed depending how heavily loaded the CPU is. The other comes on the ten seconds whenever an event is recorded in the observatory's log file. Together, these LEDs provide some visual feedback as to whether the camera is observing properly.

The script `main.py` is the one which actually observes the night sky.

The first thing it does is to run `gpsFix.py` which attempts to communicate with a USB GPS dongle (if one has been connected to the system) to get an accurate time signal and position for the observatory. It's not the end of the world if no GPS fix is achieved, but bear in mind that Raspberry Pis forget what the time is when you switch them off. So if you don't have a GPS dongle, you *must* have a network connection so we can look up the time from internet time servers. Otherwise your observatory will have absolutely no idea what time of day it is!

The C program stored in videoAnalysis is run during the hours of darkness. This monitors the video stream from the camera, and records still images and video clips of moving objects. It does not do any compression on the images and videos, because CPU resources are extremely tight on a Raspberry Pi.

During the daytime, the script `dayTimeJobs.py` runs. This compresses the images into PNG format, and the videos into MP4s. The exact mechanism for doing this depends on the platform the code is running on. On a standard PC, libavtools is used. On a Raspberry Pi, this would be incredibly slow, so the RPi's inbuilt video encoder is used (i.e. OpenMAX).

Once the images have been turned into a standard format, they are imported into the observations database (using `dbImport.py`). The observatory will then run the script `orientationCalc.py`, which uses astrometry.net to attempt to automatically determine which direction the camera is pointing from the stars that are visible. Finally, the script `exportData.py` is run, which transmits observations to an external server, if one has been configured in `installation_info.py`.


#!/usr/bin/python
# daytimeJobsClean.py
# $Id: daytimeJobsClean.py 1174 2015-02-06 00:48:26Z pyxplot $

import os,time

from module_log import logTxt,getUTC
from module_settings import *

logTxt("Running daytimeJobsClean")
os.chdir (DATA_PATH)
os.system("rm -f */*.jpg */*.mp4 finishedDays.dat")
logTxt("Finished daytimeJobsClean")


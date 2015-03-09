#!/usr/bin/python
# daytimeJobsClean.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os,time

from module_log import logTxt,getUTC
from module_settings import *

logTxt("Running daytimeJobsClean")
os.chdir (DATA_PATH)
os.system("rm -f */*.jpg */*.mp4 finishedDays.dat")
logTxt("Finished daytimeJobsClean")


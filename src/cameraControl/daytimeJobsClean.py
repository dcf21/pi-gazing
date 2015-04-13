#!/usr/bin/python
# daytimeJobsClean.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os,time

from module_log import logTxt,getUTC
from module_settings import *
from module_daytimejobs import *
import module_hwm

logTxt("Running daytimeJobsClean")
CWD = os.getcwd()
os.chdir (DATA_PATH)

# Clean up any file products which are newer than high water mark
highWaterMarks = module_hwm.fetchHWM()

# Work on each task in turn
for taskGroup in dayTimeTasks:
  [HWMout, Nmax, taskList] = taskGroup;
  if HWMout not in highWaterMarks: highWaterMarks[HWMout]=0
  for task in taskList:
    [inDir,outDirs,inExt,outExt,cmd] = task

    # Remove any output which is newer than HWM
    for outDir in outDirs:
      for dirName, subdirList, fileList in os.walk(outDir):
        for f in fileList:
          utc = module_hwm.filenameToUTC(f)
          if (utc < 0): continue
          if (utc > highWaterMarks[HWMout]): os.system("rm -f %s"%os.path.join(dirName,f))

os.chdir(CWD)
logTxt("Finished daytimeJobsClean")


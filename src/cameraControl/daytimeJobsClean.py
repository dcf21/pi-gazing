#!/usr/bin/python
# daytimeJobsClean.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os,time

from module_log import logTxt,getUTC
from module_settings import *
from module_daytimejobs import *

logTxt("Running daytimeJobsClean")
os.chdir (DATA_PATH)

# Clean up any file products which are newer than high water mark
highWaterMarks = fetchHWM()

# Work on each task in turn
for taskGroup in dayTimeTasks:
  [HWMout, taskList] = taskGroup;
  if HWMout not in highWaterMarks: highWaterMarks[HWMout]=0
  for task in taskList:
    [inDir,outDirs,inExt,HWMin,cmd] = tasks

    # Remove any output which is newer than HWM
    for outDir in outDirs:
      for dirName, subdirList, fileList in os.walk(outDir):
        for f in fileList:
          utc = module_hwm.filenameToUTC(f)
          if (utc > highWaterMarks[HWMout]): os.system("rm -f %s"%os.path.join(dirName,f))

logTxt("Finished daytimeJobsClean")


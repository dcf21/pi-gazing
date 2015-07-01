#!../../pythonenv/bin/python
# daytimeJobsClean.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os,time

from mod_log import logTxt,getUTC
from mod_settings import *
from mod_daytimejobs import *
import mod_hwm

logTxt("Running daytimeJobsClean")
CWD = os.getcwd()
os.chdir (DATA_PATH)

# Clean up any file products which are newer than high water mark
highWaterMarks = mod_hwm.fetchHWM()

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
          utc = mod_hwm.filenameToUTC(f)
          if (utc < 0): continue
          if (utc > highWaterMarks[HWMout]): os.system("rm -f %s"%os.path.join(dirName,f))

os.chdir(CWD)
logTxt("Finished daytimeJobsClean")


#!../../pythonenv/bin/python
# daytimeJobsStatus.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# This gives a status update on what dayTimeJobs need doing, and how a running
# script is getting on

import os,time,sys,glob,datetime,operator

from mod_settings import *
from mod_daytimejobs import *
import mod_hwm

pid = os.getpid()

# Read our high water mark, and only analyse more recently-created data
os.chdir(DATA_PATH)
highWaterMarks = mod_hwm.fetchHWM()

fileCensus = {}

# Get list of files in each directory
for dirName, subdirList, fileList in os.walk("."):
  leafName = os.path.split(dirName)[1]
  if (leafName=='rawvideo' or leafName.startswith("20")):
    rootDir = dirName.split('/')[1]
    if rootDir not in fileCensus: fileCensus[rootDir]={}
    for f in fileList:
      utc = mod_hwm.filenameToUTC(f)
      if (utc<0): continue
      fileCensus[rootDir][utc] = f

jobCensus = {}
jobCensus['behindHwmDone'] = {}
jobCensus['behindHwmUndone'] = {}
jobCensus['aheadHwmDone'] = {}
jobCensus['aheadHwmUndone'] = {}

# Cycle through all jobs which need to be done
for taskGroup in dayTimeTasks:
  [HWMout, Nmax , taskList] = taskGroup;
  if HWMout not in highWaterMarks: highWaterMarks[HWMout]=0
  for i in jobCensus.itervalues():
    if HWMout not in i: i[HWMout]=0
  for task in taskList:
    [inDir,outDirs,inExt,outExt,cmd] = task

    # Cycle through all input files for each job, and look to see whether we have output files with a matching timestamp
    for dirName, subdirList, fileList in os.walk(inDir):
      for f in fileList:
        if f.endswith(".%s"%inExt):
          utc = mod_hwm.filenameToUTC(f)
          if (utc<0): continue
          behindHWM = (utc <= highWaterMarks[HWMout])
          done = False
          for outDir in outDirs:
            if outDir in fileCensus:
              if (inExt != 'h264'): # Most files produce output with the same timestamp as the input; except overnight videos...
                if (utc in fileCensus[outDir]): done=True
              else:
                for u in fileCensus[outDir].keys():
                 if ((u>utc)and(u<utc+VIDEO_MAXRECTIME)): # For files in rawvideo, assume they are processed if we have an output file within some duration of the video's start time
                   done=True
                   break
          if ((    done) and (not behindHWM)): jobCensus['aheadHwmDone']   [HWMout]+=1
          if ((not done) and (not behindHWM)): jobCensus['aheadHwmUndone'] [HWMout]+=1
          if ((    done) and (    behindHWM)): jobCensus['behindHwmDone']  [HWMout]+=1
          if ((not done) and (    behindHWM)): jobCensus['behindHwmUndone'][HWMout]+=1

# Render quick and dirty table
out  = sys.stdout
cols = jobCensus.keys()          ; cols.sort()
rows = jobCensus[cols[0]].keys() ; rows.sort()
for colHead in ['']+cols: out.write("%25s "%colHead)
out.write("\n")
for rowHead in rows:
  out.write("%25s "%rowHead)
  for colHead in cols:
    if rowHead in jobCensus[colHead]: out.write("%25s "%jobCensus[colHead][rowHead])
    else                            : out.write("%25s "%"-----")
  out.write("\n")


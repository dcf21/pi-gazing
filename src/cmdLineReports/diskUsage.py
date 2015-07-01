#!../../pythonenv/bin/python
# diskUsage.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# This gives a breakdown of the disk usage of different kinds of files by observation day

import os,time,sys,glob,datetime,operator

from mod_settings import *
import mod_hwm

pid = os.getpid()
os.chdir(DATA_PATH)

fileCensus = {}

# Get list of files in each directory
for dirName, subdirList, fileList in os.walk("."):
  leafName = os.path.split(dirName)[1]
  if (leafName=='rawvideo' or leafName.startswith("20")):
    rootDir = dirName.split('/')[1]
    for f in fileList:
      if f.startswith("20"):
        dayName = mod_hwm.fetchDayNameFromFilename(f)
        if rootDir not in fileCensus         : fileCensus[rootDir]={}
        if dayName not in fileCensus[rootDir]: fileCensus[rootDir][dayName]=0
        fileCensus[rootDir][dayName] += os.path.getsize(os.path.join(dirName,f))

def renderDataSizeList(data):
  totalFileSize = sum(data)
  output = []
  for d in data:
    output.append("%6.2f GB (%5.1f%%)"%(d/1.e9 , d*100./totalFileSize))
  return output

# Render quick and dirty table
out  = sys.stdout
cols = fileCensus.keys()          ; cols.sort()
rows = []
for colHead in cols:
 for rowHead in fileCensus[colHead]:
   if rowHead not in rows: rows.append(rowHead)
rows.sort()
for colHead in ['']+cols: out.write("%25s "%colHead)
out.write("\n")
for rowHead in rows:
  out.write("%25s "%rowHead)
  data = []
  for colHead in cols:    
    if rowHead in fileCensus[colHead]: data.append(fileCensus[colHead][rowHead])
    else                             : data.append(0)
  dataStr = renderDataSizeList(data)
  for i in range(len(cols)): out.write("%25s "%dataStr[i])
  out.write("\n")


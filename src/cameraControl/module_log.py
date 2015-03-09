# module_log.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os,time

pid = os.getpid()

toffset = 0

def getUTC():
  return time.time()-toffset

def getUTCoffset():
  return -toffset

logfile = open("piInSky.log","a")

def logTxt(txt):
 output = "[%s py] %s"%(time.strftime("%b %d %Y %H:%M:%S", time.gmtime(getUTC())),txt)
 print output
 logfile.write("%s\n"%output)
 logfile.flush()


# mod_log.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os,time
import mod_settings

pid = os.getpid()

toffset = 0

def getUTC():
  return time.time()-toffset

def getUTCoffset():
  return -toffset

logfile = open( os.path.join(mod_settings.DATA_PATH,"meteorPi.log") , "a" )

def logTxt(txt):
 output = "[%s py] %s"%(time.strftime("%b %d %Y %H:%M:%S", time.gmtime(getUTC())),txt)
 print output
 logfile.write("%s\n"%output)
 logfile.flush()


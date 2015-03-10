# timelapse.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

from __future__ import division
from math import *
import os,sys,time,re

PERIOD = 60

pid = os.getpid()

def utc():
  return time.time()

logfile = open("log.txt","a")

def logtxt(txt):
 logfile.write("[%s] %s\n"%(time.strftime("%b %d %Y %H:%M:%S", time.gmtime(utc())),txt))
 logfile.flush()

logtxt("timelapse launched")

# Start time for time lapse sequence
timeTarget = floor((utc() + 10)/10)*10;

# Make directory
# dirname = time.strftime("/mnt/harddisk/pi/%Y%m%d_%H%M%S" , time.gmtime(utc()))
dirname = "/mnt/harddisk/pi/daveSky"
os.system("mkdir -p %s"%dirname)
os.chdir(dirname)

frNum=1

while True:
  logtxt("Waiting for next exposure")
  wait = timeTarget - utc()
  if (wait>0): time.sleep(wait)

  # Filename
  while 1:
   fname = "frame%06d.jpg"%(frNum)
   if os.path.exists(fname): frNum+=1
   else: break

  # Take exposure
  logtxt("Taking photo")
  os.system("rm -f tmp.jpg")
  os.system("/home/pi/meteor-pi/src/videoProcess/bin/snapshot tmp.jpg 500")
  os.system("""convert tmp.jpg -background black -rotate -180 tmp2.jpg""")
  os.system("""convert tmp2.jpg -gravity South -background Green -splice 0x26 -pointsize 16 -font Ubuntu-Bold -annotate +0+2 '%s' %s"""%(time.strftime("%b %d %Y %H:%M:%S", time.gmtime(utc())),fname))
  #os.system("""rm -f daveShed.mp4""")
  #os.system("""avconv -r 10 -i frame%06d.jpg -codec:v libx264 daveShed.mp4""")
  os.system("""rsync -av * dcf21@sandbox.britastro.com:public_html/daveSky/""")

  timeTarget += PERIOD


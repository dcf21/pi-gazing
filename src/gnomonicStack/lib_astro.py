# lib_astro.py
# Dominic Ford
# $Id: lib_astro.py 1155 2015-01-09 02:07:13Z pyxplot $

import time,datetime,os,subprocess
from math import *

def siderealTime(utc):
  # See pages 87-88 of Astronomical Algorithms, by Jean Meeus
  u = utc;
  j = 40587.5 + u / 86400.0; # Julian date - 2400000
  T = (j - 51545.0) / 36525.0; # Julian century (no centuries since 2000.0)
  st = (( \
         280.46061837 + \
         360.98564736629 * (j - 51545.0) + \
         0.000387933     * T*T + \
         T*T*T / 38710000.0 \
        ) % 360) * 12 / 180;
  return st; # sidereal time, in hours. RA at zenith in Greenwich.

def altAz(ra,dec,utc,latitude,longitude):
  ra *= pi/12;
  dec*= pi/180;
  st  = siderealTime(utc)*pi/12 + longitude*pi/180;
  xyz = [ sin(ra)*cos(dec) , -sin(dec) , cos(ra)*cos(dec) ]; # y-axis = north/south pole; z-axis (into screen) = vernal equinox

  # Rotate by hour angle around y-axis
  xyz2=[0,0,0];
  xyz2[0] = xyz[0]*cos(st) - xyz[2]*sin(st);
  xyz2[1] = xyz[1];
  xyz2[2] = xyz[0]*sin(st) + xyz[2]*cos(st);

  # Rotate by latitude around x-axis
  xyz3=[0,0,0];
  t = pi/2 - latitude*pi/180;
  xyz3[0] = xyz2[0];
  xyz3[1] = xyz2[1]*cos(t) - xyz2[2]*sin(t);
  xyz3[2] = xyz2[1]*sin(t) + xyz2[2]*cos(t);

  alt= -asin(xyz3[1]);
  az = atan2(xyz3[0],-xyz3[2]);
  return [alt*180/pi,az*180/pi]; # [altitude, azimuth] of object in degrees

def positionAngle(lng1,lat1,lng2,lat2):
  lat1*=pi/180 ; lat2*=pi/180
  lng1*=pi/ 12 ; lng2*=pi/ 12
  y = sin(lng2-lng1) * cos(lat2);
  x = cos(lat1)*sin(lat2) - sin(lat1)*cos(lat2)*cos(lng2-lng1);
  bearing = atan2(y, x);
  return bearing

def ImageTime(fname):
  os.environ['TZ'] = 'UTC'
  time.tzset()

  fs = os.path.split(fname)[1]
  if len(fs)>14:
   indate = [fs[0:4],fs[4:6],fs[6:8],fs[8:10],fs[10:12],fs[12:14]]
   if False not in [x.isdigit() for x in indate]:
     indate = [int(x) for x in indate]
     t = datetime.datetime(indate[0],indate[1],indate[2],indate[3],indate[4],indate[5])
     return float(t.strftime("%s"))

  pid = os.getpid()
  os.system("identify -verbose %s | grep exif:DateTime: > /tmp/it_%d"%(fname,pid))
  imageTime = open("/tmp/it_%d"%pid).read()
  os.system("rm -f /tmp/it_%d"%pid)
  words = imageTime.split()
  if len(words)<3: return 0
  indate = [ int(i) for i in words[-2].split(":") ]
  intime = [ int(i) for i in words[-1].split(":") ]

  t = datetime.datetime(indate[0],indate[1],indate[2],intime[0],intime[1],intime[2])
  return float(t.strftime("%s"))

def ImageDimensions(f):
  d = subprocess.check_output(["identify", f]).split()[2].split("x") ; d = [int(i) for i in d]
  return d

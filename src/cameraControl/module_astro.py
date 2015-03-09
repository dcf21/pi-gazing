# module_astro.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

from math import *
import time,datetime

from module_log import logTxt,getUTC

deg = pi/180

# See Astronomical Algorithms, pp 163-4
def sunPos(utc=0):
 if not utc: utc = getUTC()

 JD= utc / 86400.0 + 2440587.5

 T = (JD-2451545.0) / 36525.
 L0= 280.46646 + 36000.76983*T + 0.0003032*T*T
 M = 357.52911 + 35999.05029*T + 0.0001537*T*T
 e = 0.016708634 - 0.000042037*T - 0.0000001267*T*T

 C = ( (1.914602 - 0.004817*T - 0.000014*T*T)*sin(  M*deg)
      +(0.019993 - 0.000101*T               )*sin(2*M*deg)
      +(0.000289                            )*sin(3*M*deg) )

 tl= L0+C # true longitude
 v = M +C # true anomaly

 epsilon = 23+26./60+21.448/3600  +  46.8150/3600*T  +  0.00059/3600*T*T  +  0.001813/3600*T*T*T

 RA  =  12/pi*atan2(cos(epsilon*deg)*sin(tl*deg) , cos(tl*deg)) # hours
 Dec = 180/pi*asin (sin(epsilon*deg)*sin(tl*deg)) # degrees

 return [RA,Dec]

def rs_riseculmgap(decObj,latObs,angBelowHorizon): # all inputs are in radians
  angBelowHorizon = -angBelowHorizon;
  z     = sin(decObj);
  alpha = (pi/2-latObs);
  sinO  = (z - sin(angBelowHorizon)*cos(alpha)) / (cos(angBelowHorizon)*sin(alpha));
  cosO  = sqrt(1 - pow(sinO,2));
  B     = atan2(cosO*cos(angBelowHorizon) , (sinO*cos(angBelowHorizon)*cos(alpha)-sin(angBelowHorizon)*sin(alpha)));
  if (isnan(B)): return -1; # Return -1 if requested declination is circumpolar or below horizon
  return 3600*12*(1-abs(B / pi)); # Return number of second between rising and culmination time. Each day, object is above horizon for 2x time period.

def siderealTime(utc):
  u = utc;
  j = 40587.5 + u / 86400.0; # Julian date - 2400000
  T = (j - 51545.0) / 36525.0; # Julian century (no centuries since 2000.0)
  st = ((
          280.46061837 +
          360.98564736629 * (j - 51545.0) + # See pages 87-88 of Astronomical Algorithms, by Jean Meeus
          0.000387933     * T*T +
          T*T*T / 38710000.0
         ) % 360) * 12 / 180;
  return st; # sidereal time, in hours. RA at zenith in Greenwich.

def rs_time_s(unixtime,ra,dec,longitude,latitude,angBelowHorizon):
  unixtime = floor(unixtime/3600/24)*3600*24 # midnight

  utmin = unixtime-3600*24*0.75
  r     = []
  for i in range(48):
    u=utmin+i*3600
    r.append([u,siderealTime(u)])

  lhr    = longitude / 180 * 12;
  hourang= 0;
  gap    = rs_riseculmgap(dec*pi/180,latitude*pi/180,angBelowHorizon*pi/180);
  rcount = len(r);

  utcrise = 0;
  utcculm = 0;
  utcset  = 0;

  for i in range(rcount-1):
    st0 = r[i][1];
    st1 = r[i+1][1];
    if (st1<st0): st1+=24;
    if (ra < (st0+lhr)):
     st0-=24; st1-=24;
    if (ra > (st1+lhr)):
     st0+=24; st1+=24;
    tculm = (ra-(st0+lhr)) / (st1-st0);
    if ((tculm<0)or(tculm>=1)): continue;
    tculm = r[i][0] + (r[i+1][0]-r[i][0]) * tculm;
    hourang = fmod((tculm-unixtime)/3600,24);
    utcrise=tculm-gap; utcculm=tculm; utcset=tculm+gap;

  return [utcrise , utcculm , utcset]

def sunTimes(unixtime=0,longitude=0.12,latitude=52.2):
  if not unixtime: unixtime=getUTC()
 
  s = sunPos(unixtime)
  r = rs_time_s(unixtime,s[0],s[1],longitude,latitude,-0.5)

  logTxt("Sunrise at %s"%(datetime.datetime.fromtimestamp(r[0]).strftime('%Y-%m-%d %H:%M:%S')))
  logTxt("Sunset  at %s"%(datetime.datetime.fromtimestamp(r[2]).strftime('%Y-%m-%d %H:%M:%S')))

  return r


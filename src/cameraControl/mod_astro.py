# mod_astro.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

from math import *
import time,datetime

from mod_log import logTxt,getUTC

deg = pi/180

# Return the [RA, Dec] of the Sun at a given Unix time. See Jean Meeus, Astronomical Algorithms, pp 163-4
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

# Returns the number of seconds between an object at a given declination rising and culminating
def rs_riseculmgap(decObj,latObs,angBelowHorizon): # all inputs are in radians
  angBelowHorizon = -angBelowHorizon;
  z     = sin(decObj);
  alpha = (pi/2-latObs);
  sinO  = (z - sin(angBelowHorizon)*cos(alpha)) / (cos(angBelowHorizon)*sin(alpha));
  cosO  = sqrt(1 - pow(sinO,2));
  B     = atan2(cosO*cos(angBelowHorizon) , (sinO*cos(angBelowHorizon)*cos(alpha)-sin(angBelowHorizon)*sin(alpha)));
  if (isnan(B)): return -1; # Return -1 if requested declination is circumpolar or below horizon
  return 3600*12*(1-abs(B / pi)); # Return number of second between rising and culmination time. Each day, object is above horizon for 2x time period.

# Turns a unix time into a sidereal time (in hours, at Greenwich)
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

# Returns the UTC times for the rising, culmination and setting of an astronomical object at position [RA,Dec]
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

# Returns unix times for [sunrise , sun culmination , sunset]
def sunTimes(unixtime=0,longitude=0.12,latitude=52.2):
  if not unixtime: unixtime=getUTC()
 
  s = sunPos(unixtime)
  r = rs_time_s(unixtime,s[0],s[1],longitude,latitude,-0.5)

  logTxt("Sunrise at %s"%(datetime.datetime.fromtimestamp(r[0]).strftime('%Y-%m-%d %H:%M:%S')))
  logTxt("Sunset  at %s"%(datetime.datetime.fromtimestamp(r[2]).strftime('%Y-%m-%d %H:%M:%S')))

  return r

# Converts an RA and Dec into an altitude and an azimuth
# RA should be in hours; all other angles should be in degrees.
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

# Returns the Julian Day number of a calendar date (British calendar)
def JulianDay(year, month, day, hour, min, sec):
  LastJulian     = 17520902.0
  FirstGregorian = 17520914.0
  ReqDate        = 10000.0*year + 100*month + day

  if (month<=2):
   month+=12
   year-=1

  if (ReqDate <= LastJulian):
   b = -2 + ((year+4716)/4) - 1179 # Julian calendar
  elif (ReqDate >= FirstGregorian):
   b = (year/400) - (year/100) + (year/4) # Gregorian calendar
  else:
   raise InputError, "The requested date never happened"

  JD = 365.0*year - 679004.0 + 2400000.5 + b + floor(30.6001*(month+1)) + day
  DayFraction = (fabs(hour) + fabs(min)/60.0 + fabs(sec)/3600.0) / 24.0
  return JD + DayFraction

def InvJulianDay(JD):
  DayFraction = (JD+0.5) - floor(JD+0.5)
  hour = int(floor(        24*DayFraction      ))
  min  = int(floor(fmod( 1440*DayFraction , 60)))
  sec  =           fmod(86400*DayFraction , 60)

  # Number of whole Julian days. b = Number of centuries since the Council of Nicaea. c = Julian Day number as if century leap years happened.
  a = int(JD + 0.5)
  if (a < 2361222.0):
   b=0; c=int(a+1524) # Julian calendar
  else:
   b=int((a-1867216.25)/36524.25); c=int(a+b-(b/4)+1525) # Gregorian calendar
  d = int((c-122.1)/365.25);   # Number of 365.25 periods, starting the year at the end of February
  e = int(365*d + d/4); # Number of days accounted for by these
  f = int((c-e)/30.6001);      # Number of 30.6001 days periods (a.k.a. months) in remainder
  day   = int(floor(c-e-(int)(30.6001*f)));
  month = int(floor(f-1-12*(f>=14)));
  year  = int(floor(d-4715-int(month>=3)));
  return [year,month,day,hour,min,sec]

# Returns a UTC timestamp from a Julian Day number
def UTCfromJD(jd):
  return 86400.0 * (jd - 2440587.5)

def JDfromUTC(utc):
  return (utc/86400.0) + 2440587.5

# Average of multiple angles; well behaved at 0/360 degree wrap-around. Input in radians.
def meanAngle(angleList):
 xlist = [ sin(a) for a in angleList ] # Project angles onto a circle
 ylist = [ cos(a) for a in angleList ]
 xmean = sum(xlist) / len(angleList) # Find centroid
 ymean = sum(ylist) / len(angleList)
 amean = atan2(xmean,ymean) # Find angle of centroid from centre
 sd    = sqrt( sum( [hypot(xlist[i]-xmean , ylist[i]-ymean)**2 for i in range(len(xlist)) ] ))
 asd   = atan(sd) # Find angular spread of points as seen from centre
 return [amean,asd] # [Mean,SD] in radians

# Average of multiple polar coordinate positions
def meanAngle2D(posList):
 xlist = [ sin(a[1])*sin(a[0]) for a in posList ] # Project angles onto a circle
 ylist = [ cos(a[1])*sin(a[0]) for a in posList ]
 zlist = [ cos(a[0])           for a in posList ]
 xmean = sum(xlist) / len(posList) # Find centroid
 ymean = sum(ylist) / len(posList)
 zmean = sum(zlist) / len(posList)
 pmean = [ atan2(hypot(xmean,ymean),zmean) , atan2(xmean,ymean) ]
 sd    = sqrt( sum( [ (xlist[i]-xmean)**2 + (ylist[i]-ymean)**2 + (zlist[i]-zmean)**2 for i in range(len(xlist)) ] ) / len(posList) )
 asd   = atan(sd) # Find angular spread of points as seen from centre
 return [pmean,asd] # [Mean,SD] in radians


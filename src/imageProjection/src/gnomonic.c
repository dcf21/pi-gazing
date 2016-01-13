// gnomonic.c
// Meteor Pi, Cambridge Science Centre 
// Dominic Ford

#include <stdlib.h>
#include <math.h>
#include <gsl/gsl_math.h>
#include "gnomonic.h"

void rotate_xy(double *a, double theta)
 {
  double a0 = a[0]*cos(theta) + a[1]*-sin(theta);
  double a1 = a[0]*sin(theta) + a[1]* cos(theta);
  double a2 = a[2];
  a[0] = a0; a[1] = a1; a[2] = a2;
  return;
 }
void rotate_xz(double *a, double theta)
 {
  double a0 = a[0]*cos(theta) + a[2]*-sin(theta);
  double a1 = a[1];
  double a2 = a[0]*sin(theta) + a[2]* cos(theta);
  a[0] = a0; a[1] = a1; a[2] = a2;
  return;
 }

void make_zenithal(double ra, double dec, double ra0, double dec0, double *za, double *az)
 {
  double altitude, azimuth, zenith_angle;
  double x = cos(ra)*cos(dec);
  double y = sin(ra)*cos(dec);
  double z = sin(dec);
  double a[3] = {x,y,z};
  rotate_xy(a , -ra0);
  rotate_xz(a , (M_PI/2)-dec0);
  if (a[2]> 0.999999999) a[2]= 1.0;
  if (a[2]<-0.999999999) a[2]=-1.0;
  altitude = asin(a[2]);
  if (fabs(cos(altitude))<1e-7) azimuth = 0.0; // Ignore azimuth at pole!
  else                          azimuth = atan2( a[1]/cos(altitude) , a[0]/cos(altitude));
  zenith_angle = (M_PI/2) - altitude;

  *za = zenith_angle;
  *az = azimuth;
  return;
 }

double AngDist(double RA0, double Dec0, double RA1, double Dec1)
 {
  double x0 = cos(RA0) * cos(Dec0);
  double y0 = sin(RA0) * cos(Dec0);
  double z0 =            sin(Dec0);
  double x1 = cos(RA1) * cos(Dec1);
  double y1 = sin(RA1) * cos(Dec1);
  double z1 =            sin(Dec1);
  double d  = sqrt(pow(x0-x1,2) + pow(y0-y1,2) + pow(z0-z1,2));
  return 2*asin(d/2);
 }

void FindMeanPosition(double *RAm, double *DECm, double RA0, double DEC0, double RA1, double DEC1, double RA2, double DEC2)
 {
  double x0 = cos(RA0) * cos(DEC0);
  double y0 = sin(RA0) * cos(DEC0);
  double z0 =            sin(DEC0);
  double x1 = cos(RA1) * cos(DEC1);
  double y1 = sin(RA1) * cos(DEC1);
  double z1 =            sin(DEC1);
  double x2 = cos(RA2) * cos(DEC2);
  double y2 = sin(RA2) * cos(DEC2);
  double z2 =            sin(DEC2);
  double x3 = (x0+x1+x2)/3;
  double y3 = (y0+y1+y2)/3;
  double z3 = (z0+z1+z2)/3;
  *DECm = asin(z3);
  *RAm  = atan2(y3,x3);
  return;
 }

void GnomonicProject(double RA, double Dec, double RA0, double Dec0, int SizeX, int SizeY, double ScaleX, double ScaleY, double *x, double *y, double posang, double bca, double bcb, double bcc)
 {
  double dist = AngDist(RA, Dec, RA0, Dec0);
  double za, az, radius, xd, yd;

  if (dist>M_PI/2) { *x=-1; *y=-1; return; }
  make_zenithal(RA, Dec, RA0, Dec0, &za, &az);
  radius = tan(za);
  az    -= posang;

  // Correction for barrel distortion
  double r  = radius / tan(ScaleY/2);
  double bcd= 1.-bca-bcb-bcc;
  double R  = (((bca*r+bcb)*r+bcc)*r+bcd)*r;
  radius = R * tan(ScaleY/2);

  yd     =  radius * cos(az) * (SizeY/2./tan(ScaleY/2.)) + SizeY/2.;
  xd     =  radius *-sin(az) * (SizeX/2./tan(ScaleX/2.)) + SizeX/2.;

  //if ((xd>=0)&&(xd<=SizeX)) *x=(int)xd; else *x=-1;
  //if ((yd>=0)&&(yd<=SizeY)) *y=(int)yd; else *y=-1;
  *x=xd;
  *y=yd;
  return;
 }

// Includes correction for barrel distortion
void InvGnomProject (double*RA, double*Dec, double RA0, double Dec0, int SizeX, int SizeY, double ScaleX, double ScaleY, double x, double y, double posang, double bca, double bcb, double bcc)
 {
  double x2 = (x - SizeX/2.) / (SizeX/2./tan(ScaleX/2.));
  double y2 = (y - SizeY/2.) / (SizeY/2./tan(ScaleY/2.));

  double za = atan(hypot(x2,y2));
  double az = atan2(-x2,y2) + posang;

  // Correction for barrel distortion
  double r  = za / tan(ScaleY/2.);
  double bcd= 1.-bca-bcb-bcc;
  double R  = (((bca*r+bcb)*r+bcc)*r+bcd)*r;
  za = R * tan(ScaleY/2.);

  double altitude = M_PI/2 - za;
  double a[3] = { cos(altitude)*cos(az) , cos(altitude)*sin(az) , sin(altitude) };

  rotate_xz(a , -(M_PI/2)+Dec0);
  rotate_xy(a ,  RA0);

  *RA  = atan2(a[1],a[0]);
  *Dec = asin(a[2]);
  return;
 }


// gnomonic.h
// Meteor Pi, Cambridge Science Centre 
// Dominic Ford

#ifndef GNOMONIC_H
#define GNOMONIC_H 1

double AngDist         (double RA0, double Dec0, double RA1, double Dec1);
void   FindMeanPosition(double *RAm, double *DECm, double RA0, double DEC0, double RA1, double DEC1, double RA2, double DEC2);
void   GnomonicProject (double RA, double Dec, double RA0, double Dec0, int SizeX, int SizeY, double ScaleX, double ScaleY, double *x, double *y, double posang, double bca, double bcb, double bcc);
void   InvGnomProject  (double*RA, double*Dec, double RA0, double Dec0, int SizeX, int SizeY, double ScaleX, double ScaleY, double  x, double  y, double posang, double bca, double bcb, double bcc);

#endif


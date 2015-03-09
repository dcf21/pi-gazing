// JulianDate.h
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#ifndef JULIANDATE_H
#define JULIANDATE_H 1

void    SwitchOverCalDate(double *LastJulian, double *FirstGregorian);
double  SwitchOverJD();
char   *GetMonthName(int i);
char   *GetWeekDayName(int i);
double  JulianDay(int year, int month, int day, int hour, int min, int sec, int *status, char *errtext);
void    InvJulianDay(double JD, int *year, int *month, int *day, int *hour, int *min, double *sec, int *status, char *errtext);

#endif


// JulianDate.h
// Dominic Ford
// $Id: JulianDate.h 1170 2015-02-05 17:55:31Z pyxplot $
// --------------------------------------

#ifndef JULIANDATE_H
#define JULIANDATE_H 1

void    SwitchOverCalDate(double *LastJulian, double *FirstGregorian);
double  SwitchOverJD();
char   *GetMonthName(int i);
char   *GetWeekDayName(int i);
double  JulianDay(int year, int month, int day, int hour, int min, int sec, int *status, char *errtext);
void    InvJulianDay(double JD, int *year, int *month, int *day, int *hour, int *min, double *sec, int *status, char *errtext);

#endif


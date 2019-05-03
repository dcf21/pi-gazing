// julianDate.h
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2019 Dominic Ford.

// This file is part of Pi Gazing.

// Pi Gazing is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Pi Gazing is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Pi Gazing.  If not, see <http://www.gnu.org/licenses/>.
// -------------------------------------------------

#ifndef JULIANDATE_H
#define JULIANDATE_H 1

void switchOverCalDate(double *lastJulian, double *firstGregorian);

double switchOverJD();

char *getMonthName(int i);

char *getWeekDayName(int i);

double julianDay(int year, int month, int day, int hour, int min, int sec, int *status, char *errtext);

void invJulianDay(double JD, int *year, int *month, int *day, int *hour, int *min, double *sec, int *status,
                  char *errtext);

#endif

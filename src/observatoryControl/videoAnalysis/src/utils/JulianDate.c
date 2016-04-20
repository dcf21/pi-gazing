// JulianDate.c
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

// -------------------------------------------------
// Copyright 2016 Cambridge Science Centre.

// This file is part of Meteor Pi.

// Meteor Pi is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Meteor Pi is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Meteor Pi.  If not, see <http://www.gnu.org/licenses/>.
// -------------------------------------------------

#include <stdlib.h>
#include <stdio.h>
#include <math.h>

#include <gsl/gsl_math.h>

#include "utils/JulianDate.h"

// Routines for looking up the dates when the transition between the Julian calendar and the Gregorian calendar occurred

void SwitchOverCalDate(double *LastJulian, double *FirstGregorian) {
    *LastJulian = 17520902.0;
    *FirstGregorian = 17520914.0; // British
    return;
}

double SwitchOverJD() {
    return 2361222.0; // British
}

// Functions for looking up the names of the Nth calendar month and the Nth day of the week

char *GetMonthName(int i) {
    switch (i) {
        case 1:
            return "January";
        case 2:
            return "February";
        case 3:
            return "March";
        case 4:
            return "April";
        case 5:
            return "May";
        case 6:
            return "June";
        case 7:
            return "July";
        case 8:
            return "August";
        case 9:
            return "September";
        case 10:
            return "October";
        case 11:
            return "November";
        case 12:
            return "December";
        default:
            return "???";
    }
    return "???";
}

char *GetWeekDayName(int i) {
    switch (i) {
        case 0:
            return "Monday";
        case 1:
            return "Tuesday";
        case 2:
            return "Wednesday";
        case 3:
            return "Thursday";
        case 4:
            return "Friday";
        case 5:
            return "Saturday";
        case 6:
            return "Sunday";
    }
    return "???";
}

// Routines for converting between Julian Day numbers and Calendar Dates in Gregorian and Julian calendars

double JulianDay(int year, int month, int day, int hour, int min, int sec, int *status, char *errtext) {
    double JD, DayFraction, LastJulian, FirstGregorian, ReqDate;
    int b;

    if ((year < -1e6) || (year > 1e6) || (!gsl_finite(year))) {
        *status = 1;
        sprintf(errtext, "Supplied year is too big.");
        return 0.0;
    }
    if ((day < 1) || (day > 31)) {
        *status = 1;
        sprintf(errtext, "Supplied day number should be in the range 1-31.");
        return 0.0;
    }
    if ((hour < 0) || (hour > 23)) {
        *status = 1;
        sprintf(errtext, "Supplied hour number should be in the range 0-23.");
        return 0.0;
    }
    if ((min < 0) || (min > 59)) {
        *status = 1;
        sprintf(errtext, "Supplied minute number should be in the range 0-59.");
        return 0.0;
    }
    if ((sec < 0) || (sec > 59)) {
        *status = 1;
        sprintf(errtext, "Supplied second number should be in the range 0-59.");
        return 0.0;
    }
    if ((month < 1) || (month > 12)) {
        *status = 1;
        sprintf(errtext, "Supplied month number should be in the range 1-12.");
        return 0.0;
    }

    SwitchOverCalDate(&LastJulian, &FirstGregorian);
    ReqDate = 10000.0 * year + 100 * month + day;

    if (month <= 2) {
        month += 12;
        year--;
    }

    if (ReqDate <= LastJulian) { b = -2 + ((year + 4716) / 4) - 1179; } // Julian calendar
    else if (ReqDate >= FirstGregorian) { b = (year / 400) - (year / 100) + (year / 4); } // Gregorian calendar
    else {
        *status = 1;
        sprintf(errtext,
                "The requested date never happened in the British calendar: it was lost in the transition from the Julian to the Gregorian calendar.");
        return 0.0;
    }

    JD = 365.0 * year - 679004.0 + 2400000.5 + b + floor(30.6001 * (month + 1)) + day;

    DayFraction = (fabs(hour) + fabs(min) / 60.0 + fabs(sec) / 3600.0) / 24.0;

    return JD + DayFraction;
}

void InvJulianDay(double JD, int *year, int *month, int *day, int *hour, int *min, double *sec, int *status,
                  char *errtext) {
    long a, b, c, d, e, f;
    double DayFraction;
    int temp;
    if (month == NULL) month = &temp; // Dummy placeholder, since we need month later in the calculation

    if ((JD < -1e8) || (JD > 1e8) || (!gsl_finite(JD))) {
        *status = 1;
        sprintf(errtext, "Supplied Julian Day number is too big.");
        return;
    }

    // Work out hours, minutes and seconds
    DayFraction = (JD + 0.5) - floor(JD + 0.5);
    if (hour != NULL) *hour = (int) floor(24 * DayFraction);
    if (min != NULL) *min = (int) floor(fmod(1440 * DayFraction, 60));
    if (sec != NULL) *sec = fmod(86400 * DayFraction, 60);

    // Now work out calendar date
    a = JD +
        0.5; // Number of whole Julian days. b = Number of centuries since the Council of Nicaea. c = Julian Day number as if century leap years happened.
    if (a < SwitchOverJD()) {
        b = 0;
        c = a + 1524;
    } // Julian calendar
    else {
        b = (a - 1867216.25) / 36524.25;
        c = a + b - (b / 4) + 1525;
    } // Gregorian calendar
    d = (c - 122.1) / 365.25;   // Number of 365.25 periods, starting the year at the end of February
    e = 365 * d + d / 4; // Number of days accounted for by these
    f = (c - e) / 30.6001;      // Number of 30.6001 days periods (a.k.a. months) in remainder
    if (day != NULL) *day = (int) floor(c - e - (int) (30.6001 * f));
    *month = (int) floor(f - 1 - 12 * (f >= 14));
    if (year != NULL) *year = (int) floor(d - 4715 - (*month >= 3));

    return;
}


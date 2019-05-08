// julianDate.c
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

#include <stdlib.h>
#include <stdio.h>
#include <math.h>

#include <gsl/gsl_math.h>

#include "utils/julianDate.h"

// Routines for looking up the dates when the transition between the Julian calendar and the Gregorian calendar occurred

void switch_over_calendar_date(double *lastJulian, double *firstGregorian) {
    *lastJulian = 17520902.0;
    *firstGregorian = 17520914.0; // British
}

double switch_over_jd() {
    return 2361222.0; // British
}

// Functions for looking up the names of the Nth calendar month and the Nth day of the week

char *get_month_name(int i) {
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
}

char *get_week_day_name(int i) {
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
        default:
            return "???";
    }
}

// Routines for converting between Julian Day numbers and Calendar Dates in Gregorian and Julian calendars

double julian_day(int year, int month, int day, int hour, int min, int sec, int *status, char *err_text) {
    double jd, day_fraction, last_julian, first_gregorian, required_date;
    int b;

    if ((year < -1e6) || (year > 1e6) || (!gsl_finite(year))) {
        *status = 1;
        sprintf(err_text, "Supplied year is too big.");
        return 0.0;
    }
    if ((day < 1) || (day > 31)) {
        *status = 1;
        sprintf(err_text, "Supplied day number should be in the range 1-31.");
        return 0.0;
    }
    if ((hour < 0) || (hour > 23)) {
        *status = 1;
        sprintf(err_text, "Supplied hour number should be in the range 0-23.");
        return 0.0;
    }
    if ((min < 0) || (min > 59)) {
        *status = 1;
        sprintf(err_text, "Supplied minute number should be in the range 0-59.");
        return 0.0;
    }
    if ((sec < 0) || (sec > 59)) {
        *status = 1;
        sprintf(err_text, "Supplied second number should be in the range 0-59.");
        return 0.0;
    }
    if ((month < 1) || (month > 12)) {
        *status = 1;
        sprintf(err_text, "Supplied month number should be in the range 1-12.");
        return 0.0;
    }

    switch_over_calendar_date(&last_julian, &first_gregorian);
    required_date = 10000.0 * year + 100 * month + day;

    if (month <= 2) {
        month += 12;
        year--;
    }

    if (required_date <= last_julian) { b = -2 + ((year + 4716) / 4) - 1179; } // Julian calendar
    else if (required_date >= first_gregorian) { b = (year / 400) - (year / 100) + (year / 4); } // Gregorian calendar
    else {
        *status = 1;
        sprintf(err_text,
                "The requested date never happened in the British calendar: it was lost in the transition from the Julian to the Gregorian calendar.");
        return 0.0;
    }

    jd = 365.0 * year - 679004.0 + 2400000.5 + b + floor(30.6001 * (month + 1)) + day;

    day_fraction = (fabs(hour) + fabs(min) / 60.0 + fabs(sec) / 3600.0) / 24.0;

    return jd + day_fraction;
}

void inv_julian_day(double jd, int *year, int *month, int *day, int *hour, int *min, double *sec, int *status,
                    char *err_text) {
    long a, b, c, d, e, f;
    double day_fraction;
    int temp;
    if (month == NULL) month = &temp; // Dummy placeholder, since we need month later in the calculation

    if ((jd < -1e8) || (jd > 1e8) || (!gsl_finite(jd))) {
        *status = 1;
        sprintf(err_text, "Supplied Julian Day number is too big.");
        return;
    }

    // Work out hours, minutes and seconds
    day_fraction = (jd + 0.5) - floor(jd + 0.5);
    if (hour != NULL) *hour = (int) floor(24 * day_fraction);
    if (min != NULL) *min = (int) floor(fmod(1440 * day_fraction, 60));
    if (sec != NULL) *sec = fmod(86400 * day_fraction, 60);

    // Now work out calendar date
    a = jd +
        0.5; // Number of whole Julian days. b = Number of centuries since the Council of Nicaea. c = Julian Day number as if century leap years happened.
    if (a < switch_over_jd()) {
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
}

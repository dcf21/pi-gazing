define([], function () {

    var dcftime = {};

    dcftime.monthday = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 999];
    dcftime.monthname = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

    dcftime.JDtoUnix = function (JD) {
        return 86400.0 * (JD - 2440587.5);
    };
    dcftime.unixToJD = function (unix) {
        return unix / 86400.0 + 2440587.5;
    };

    dcftime.calendarToJD = function (year, month, day, hour, min, sec) {
        var b, JD, dayFraction;
        var LastJulian = 17520902.0;
        var firstGregorian = 17520914.0;
        var reqDate = 10000.0 * year + 100 * month + day;

        if (month <= 2) {
            month += 12;
            year -= 1;
        }

        if (reqDate <= LastJulian) {
            b = -2 + (Math.floor(year + 4716) / 4) - 1179; // Julian calendar
        } else if (reqDate >= firstGregorian) {
            b = Math.floor(year / 400) - Math.floor(year / 100) + Math.floor(year / 4); // Gregorian calendar
        } else {
            return 0;
        }

        JD = 365.0 * Math.floor(year) - 679004.0 + 2400000.5 + b + Math.floor(30.6001 * (month + 1)) + day;
        dayFraction = (Math.abs(hour) + Math.abs(min) / 60.0 + Math.abs(sec) / 3600.0) / 24.0;
        return JD + dayFraction;
    };

    dcftime.calendarToUnix = function (year, month, day, hour, min, sec) {
        var JD = calendarToJD(year, month, day, hour, min, sec);
        return JDtoUnix(JD);
    };

    dcftime.JDtoCalendar = function (JD) {
        var dayFraction = (JD + 0.5) - Math.floor(JD + 0.5);
        var hour = Math.floor(24 * dayFraction);
        var min = Math.floor((1440 * dayFraction)%60);
        var sec = (86400 * dayFraction)%60;

        // Number of whole Julian days. b = Number of centuries since the Council of Nicaea. c = Julian Day number as if century leap years happened.
        var a, b, c, d, e, f, day, month, year;
        a = Math.floor(JD + 0.5);
        if (a < 2361222.0) {
            b = 0;
            c = Math.floor(a + 1524); // Julian calendar
        }
        else {
            b = Math.floor((a - 1867216.25) / 36524.25);
            c = Math.floor(a + b - Math.floor(b / 4) + 1525); // Gregorian calendar
        }
        d = Math.floor((c - 122.1) / 365.25);   // Number of 365.25 periods, starting the year at the end of February
        e = Math.floor(365 * d + Math.floor(d / 4)); // Number of days accounted for by these
        f = Math.floor((c - e) / 30.6001);      // Number of 30.6001 days periods (a.k.a. months) in remainder
        day = Math.floor(c - e - Math.floor(30.6001 * f));
        month = Math.floor(f - 1 - 12 * (f >= 14 ? 1 : 0));
        year = Math.floor(d - 4715 - (month >= 3 ? 1 : 0));
        return [year, month, day, hour, min, sec];
    };

    dcftime.unixToCalendar = function (unix) {
        var JD = dcftime.unixToJD(unix);
        return dcftime.JDtoCalendar(JD);
    };

    return dcftime;
});


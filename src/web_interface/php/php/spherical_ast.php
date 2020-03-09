<?php

class sphericalAst
{
    static public function siderealTime($utc)
    {
        $u = $utc;
        $j = 40587.5 + $u / 86400.0; // Julian date - 2400000
        $T = ($j - 51545.0) / 36525.0; // Julian century (no centuries since 2000.0)
        $st = ((
                    280.46061837 +
                    360.98564736629 * ($j - 51545.0) + // See pages 87-88 of Astronomical Algorithms, by Jean Meeus
                    0.000387933 * $T * $T +
                    $T * $T * $T / 38710000.0
                ) % 360) * 12 / 180;
        return $st; // sidereal time, in hours. RA at zenith in Greenwich.
    }

    static public function altAz($ra, $dec, $utc, $latitude, $longitude)
    {
        $ra *= pi() / 12;
        $dec *= pi() / 180;
        $st = sphericalAst::siderealTime($utc) * pi() / 12 + $longitude * pi() / 180;
        $xyz = [sin($ra) * cos($dec), -sin($dec), cos($ra) * cos($dec)]; // y-axis = north/south pole; z-axis (into screen) = vernal equinox

        // Rotate by hour angle around y-axis
        $xyz2 = [0, 0, 0];
        $xyz2[0] = $xyz[0] * cos($st) - $xyz[2] * sin($st);
        $xyz2[1] = $xyz[1];
        $xyz2[2] = $xyz[0] * sin($st) + $xyz[2] * cos($st);

        // Rotate by latitude around x-axis
        $xyz3 = [0, 0, 0];
        $t = pi() / 2 - $latitude * pi() / 180;
        $xyz3[0] = $xyz2[0];
        $xyz3[1] = $xyz2[1] * cos($t) - $xyz2[2] * sin($t);
        $xyz3[2] = $xyz2[1] * sin($t) + $xyz2[2] * cos($t);

        $alt = -asin($xyz3[1]);
        $az = atan2($xyz3[0], -$xyz3[2]);
        return [$alt * 180 / pi(), $az * 180 / pi()]; // [altitude, azimuth] of object in degrees
    }

    static public function RaDec($alt, $az, $utc, $latitude, $longitude)
    {
        $alt *= pi() / 180;
        $az *= pi() / 180;
        $st = sphericalAst::siderealTime($utc) * pi() / 12 + $longitude * pi() / 180;
        $xyz = [sin($az) * cos($alt), -sin($alt), -cos($az) * cos($alt)];

        // Rotate by latitude around x-axis
        $xyz3 = [0, 0, 0];
        $t = pi() / 2 - $latitude * pi() / 180;
        $xyz3[0] = $xyz[0];
        $xyz3[1] = $xyz[1] * cos(-$t) - $xyz[2] * sin(-$t);
        $xyz3[2] = $xyz[1] * sin(-$t) + $xyz[2] * cos(-$t);

        // Rotate by hour angle around y-axis
        $xyz2 = [0, 0, 0];
        $xyz2[0] = $xyz3[0] * cos(-$st) - $xyz3[2] * sin(-$st);
        $xyz2[1] = $xyz3[1];
        $xyz2[2] = $xyz3[0] * sin(-$st) + $xyz3[2] * cos(-$st);

        $dec = -asin($xyz2[1]);
        $ra = atan2($xyz2[0], $xyz2[2]);
        return [$ra * 12 / pi(), $dec * 180 / pi()];
    }

}

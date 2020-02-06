<?php

// utils.php
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2015-2020 Dominic Ford.

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

class utils
{

    public static function is_cli()
    {
        return (!isset($_SERVER['SERVER_SOFTWARE']) &&
            (php_sapi_name() == 'cli' || (is_numeric($_SERVER['argc']) && $_SERVER['argc'] > 0)));
    }

    public static function dcf_sgn($num)
    {
        if ($num < 0) return -1;
        if ($num == 0) return 0;
        return 1;
    }

    public static function startsWith($haystack, $needle)
    {
        return $needle === "" || strrpos($haystack, $needle, -strlen($haystack)) !== FALSE;
    }

    public static function endsWith($haystack, $needle)
    {
        return $needle === "" || strpos($haystack, $needle, strlen($haystack) - strlen($needle)) !== FALSE;
    }

    public static function joinPaths()
    {
        $paths = array();

        foreach (func_get_args() as $arg) {
            if ($arg !== '') {
                $paths[] = $arg;
            }
        }

        return preg_replace('#/+#', '/', join('/', $paths));
    }

    public static function getRelativeTime($tdiff, $minuteNull)
    {
        $midnight = strtotime("today", strtotime("now"));
        $dayFrac = (strtotime("now") - $midnight) / 24 / 3600;
        $tdiff2 = $tdiff + $dayFrac;
        if ($tdiff2 >= 2) {
            return sprintf("%d&nbsp;days&nbsp;away", floor($tdiff2));
        } else if ($tdiff2 < -1) {
            return sprintf("%d&nbsp;days&nbsp;ago", ceil(-$tdiff2));
        }

        if ($minuteNull) {
            if ($tdiff2 >= 1) {
                return "Tomorrow";
            }
            if ($tdiff2 <= -1) {
                return "Yesterday";
            }
            return "Today";
        } else if ($tdiff > 1) {
            return "Tomorrow";
        } else if ($tdiff < -1) {
            return "Yesterday";
        } else if ($tdiff > 2. / 24.) {
            return sprintf("%d&nbsp;hours&nbsp;away", $tdiff * 24);
        } else if ($tdiff > 1. / 24.) {
            return sprintf("1&nbsp;hour&nbsp;away");
        } else if ($tdiff < -2. / 24.) {
            return sprintf("%d&nbsp;hours&nbsp;ago", -$tdiff * 24);
        } else if ($tdiff < -1. / 24.) {
            return sprintf("1&nbsp;hour&nbsp;ago");
        } else if ($tdiff > 1. / 1440.) {
            return sprintf("%d&nbsp;minutes&nbsp;away", $tdiff * 24 * 60);
        } else if ($tdiff > 0) {
            return sprintf("1&nbsp;minute&nbsp;away");
        } else if ($tdiff < -2. / 1440.) {
            return sprintf("%d&nbsp;minutes&nbsp;ago", -$tdiff * 24 * 60);
        } else {
            return sprintf("1&nbsp;minute&nbsp;ago");
        }
    }

}

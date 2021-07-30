<?php

// html_getargs.php
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2015-2021 Dominic Ford.

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

$php_path = realpath(dirname(__FILE__));

require_once $php_path . "/constants.php";

class html_getargs
{

    public static function makeFormSelect($elementName, $selectedValue, $optionList, $escapeHTML)
    {
        print "<select class=\"slt $elementName\" name=\"$elementName\">";
        foreach ($optionList as $o) {
            if (!is_array($o)) $o = [$o, $o];
            print "<option value=\"$o[0]\" " . (($selectedValue == $o[0]) ? " selected=\"selected\"" : "") . ">";
            print $escapeHTML ? htmlentities($o[1], ENT_QUOTES) : $o[1];
            print "</option>";
        }
        print "</select>";
        return;
    }

    public function __construct($allow_any_camera)
    {
        global $const;

        if (!isset($allow_any_camera)) $allow_any_camera = false;

        // Create list of hours and minutes
        $this->hours = [];
        $this->mins = [];
        foreach (range(0, 23) as $h) $this->hours[$h] = [$h, sprintf("%02d", $h)];
        foreach (range(0, 59, 30) as $m) $this->mins [$m] = [$m, sprintf("%02d", $m)];

        // Create list of months
        $output = [];
        for ($i = 1; $i <= 12; $i++) $output[$i] = [$i, $const->shortMonthNames[$i]];
        $this->months = $output;

        // Create list of event categories
        $this->category_list = array_merge(["Any", "Exclude binned observations"], $const->item_categories);

        // Fetch list of observatories from database
        $stmt = $const->db->prepare("
SELECT publicId, name, ST_X(location) AS longitude, ST_Y(location) AS latitude FROM archive_observatories;
");
        $stmt->execute([]);
        $results = $stmt->fetchAll();
        $this->allow_any_camera = $allow_any_camera;
        $this->obstory_list = [];
        $this->obstory_objlist = [];
        $this->obstory_objs = [];
        $this->obstories = [];

        if ($allow_any_camera) {
            $this->obstory_list[] = "Any";
            $this->obstories["Any"] = ["Any", "Any"];
        }
        foreach ($results as $r) {
            $this->obstory_list[] = $r["publicId"];
            $this->obstory_objlist[] = $r;
            $this->obstory_objs[$r["publicId"]] = $r;
            $this->obstories[$r["publicId"]] = [$r["publicId"], $r["name"]];
        }
    }

    public function readMonth($argName, $utc_default = null)
    {
        global $const;
        $months = $const->shortMonthNames;
        if (is_null($utc_default)) $utc_default = time();

        if (array_key_exists($argName, $_GET) && is_string($_GET[$argName])) $mc = $_GET[$argName];
        else                                   $mc = intval(date("m", $utc_default));
        if (!array_key_exists($mc, $months)) $mc = intval(date("m", $utc_default));
        return $mc;
    }

    public function readObservatory($argName)
    {
        if (array_key_exists($argName, $_GET) && is_string($_GET[$argName])) $obs = $_GET[$argName];
        else if ($this->allow_any_camera) $obs = "Any";
        else $obs = $this->obstory_list[0];
        if (!array_key_exists($obs, $this->obstories)) $obs = $this->obstory_list[0];
        if (!array_key_exists($obs, $this->obstories)) die ("Could not find any observatories.");
        return $obs;
    }

    public function readCategory($argName)
    {
        if (array_key_exists($argName, $_GET) && is_string($_GET[$argName])) $category = $_GET[$argName];
        else $category = "Exclude binned observations";
        if (!in_array($category, $this->category_list)) $category = $this->category_list[0];
        if (!in_array($category, $this->category_list)) die ("Could not find any event categories.");
        return $category;
    }

    public function readMetadataField($argName)
    {
        global $const;
        $field = "0";
        if (array_key_exists($argName, $_GET) && is_string($_GET[$argName])) $field = $_GET[$argName];
        if (!array_key_exists($field, $const->metadataFields)) $field = "0";
        return $field;
    }

    public function readTime($argYear, $argMonth, $argDay, $argHour, $argMinute, $argSecond, $yearMin, $yearMax, $defaultUTC = null)
    {

        if (is_null($defaultUTC)) $defaultUTC = time();
        $mc = $this->readMonth($argMonth, $defaultUTC);

        if ($argDay && array_key_exists($argDay, $_GET) && is_numeric($_GET[$argDay]) &&
            $_GET[$argDay] >= 1 && $_GET[$argDay] <= 31
        )
            $day = intval($_GET[$argDay]);
        else if ($argDay)
            $day = date("d", $defaultUTC);
        else
            $day = 1;

        if ($argYear && array_key_exists($argYear, $_GET) && is_numeric($_GET[$argYear])) $year = $_GET[$argYear];
        else $year = date("Y", $defaultUTC);

        // If date is out of allowed range, use today's date
        if (($year < $yearMin) or ($year > $yearMax)) {
            $year = date("Y", $defaultUTC);
            $mc = date("m", $defaultUTC);
            $day = date("d", $defaultUTC);
        }

        // Midnight local time
        $tmin = mktime(0, 0, 1, $mc, $day, $year);

        // Read time
        if ($argHour && array_key_exists($argHour, $_GET) &&
            is_numeric($_GET[$argHour]) && $_GET[$argHour] >= 0 && $_GET[$argHour] <= 23
        )
            $hour = intval($_GET[$argHour]);
        else if ($argHour) $hour = date("H", $defaultUTC);
        else $hour = 0;

        if ($argMinute && array_key_exists($argMinute, $_GET) &&
            is_numeric($_GET[$argMinute]) && $_GET[$argMinute] >= 0 && $_GET[$argMinute] <= 59
        )
            $min = intval($_GET[$argMinute]);
        else if ($argMinute) $min = date("i", $defaultUTC);
        else $min = 0;

        if ($argSecond && array_key_exists($argSecond, $_GET) &&
            is_numeric($_GET[$argSecond]) && $_GET[$argSecond] >= 0 && $_GET[$argSecond] <= 59
        )
            $sec = intval($_GET[$argSecond]);
        else if ($argSecond) $sec = date("s", $defaultUTC);
        else $sec = 0;

        $utc = $tmin + $hour * 3600 + $min * 60 + $sec;

        return $this->readTimeFromUTC($utc);
    }

    public function readTimeFromUTC($utc)
    {
        $output = [];
        $output["utc"] = $utc;
        $output["day"] = intval(date("d", $utc));
        $output["mc"] = intval(date("m", $utc));
        $output["year"] = intval(date("Y", $utc));
        $output["monthname"] = date("F", $utc);
        $output["hour"] = date("H", $utc);
        $output["min"] = date("i", $utc);
        $output["sec"] = date("s", $utc);
        $output["localMidnight"] = mktime(0, 0, 1, $output["mc"], $output["day"], $output["year"]);
        return $output;
    }
}

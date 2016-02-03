<?php

// html_getargs.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

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

    public function __construct()
    {
        global $const;

        // Create list of hours and minutes
        $this->hours = [];
        $this->mins = [];
        foreach (range(0, 23) as $h) $this->hours[$h] = [$h, sprintf("%02d", $h)];
        foreach (range(0, 59, 30) as $m) $this->mins [$m] = [$m, sprintf("%02d", $m)];

        // Create list of months
        $output = [];
        for ($i=1; $i<=12; $i++) $output[$i] = [$i, $const->shortMonthNames[$i]];
        $this->months = $output;

        // Fetch list of observatories from database
        $stmt = $const->db->prepare("SELECT publicId,name FROM archive_observatories;");
        $stmt->execute([]);
        $results = $stmt->fetchAll();
        $this->obstory_list = [];
        $this->obstory_objlist = [];
        $this->obstory_objs = [];
        $this->obstories = [];
        foreach ($results as $r)
        {
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

        if (array_key_exists($argName, $_GET)) $mc = $_GET[$argName];
        else                                   $mc = intval(date("m", $utc_default));
        if (!array_key_exists($mc, $months)) $mc = intval(date("m", $utc_default));
        return $mc;
    }

    public function readObservatory($argName)
    {
        if (array_key_exists($argName, $_GET)) $obs = $_GET[$argName];
        else                                   $obs = $obs = $this->obstory_list[0];
        if (!array_key_exists($obs, $this->obstories)) $obs = $this->obstory_list[0];
        if (!array_key_exists($obs, $this->obstories)) die ("Could not find any observatories.");
        return $obs;
    }

    public function readTime($argYear, $argMonth, $argDay, $argHour, $argMinute, $argSecond, $yearMin, $yearMax, $defaultUTC=null)
    {

        if (is_null($defaultUTC)) $defaultUTC = time();
        $mc = $this->readMonth($argMonth);

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

<?php

// observatory_activity.php
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

require_once "php/imports.php";
require_once "php/html_getargs.php";
require_once "php/observatory_info.php";

$getargs = new html_getargs(false);

// Fetch list of observatories
$obstories = $getargs->obstory_objlist;
$obstory = $getargs->readObservatory("id");
$obstory_name = $getargs->obstory_objs[$obstory]['name'];

$obstory_info = observatory_info::obstory_info($obstory);

// Read which month to cover
$tmin = $getargs->readTime('year', 'month', null, null, null, null, $const->yearMin, $const->yearMax);

// Clip requested month to span over which we have data
$newest = $obstory_info['newest_obs_utc'];
if ((!is_null($newest)) && (
        ($tmin['year'] > intval(date('Y', $newest))) ||
        (($tmin['year'] == intval(date('Y', $newest))) && ($tmin['mc'] > intval(date('m', $newest))))
    )
) {
    $utc = mktime(0, 0, 1, date('m', $obstory_info['newest_obs_utc']), 1, date('Y', $obstory_info['newest_obs_utc']));
    $tmin = $getargs->readTimeFromUTC($utc);
}

$oldest = $obstory_info['oldest_obs_utc'];
if ((!is_null($oldest)) && (
        ($tmin['year'] < intval(date('Y', $oldest))) ||
        (($tmin['year'] == intval(date('Y', $oldest))) && ($tmin['mc'] < intval(date('m', $oldest))))
    )
) {
    $utc = mktime(0, 0, 1, date('m', $obstory_info['oldest_obs_utc']), 1, date('Y', $obstory_info['oldest_obs_utc']));
    $tmin = $getargs->readTimeFromUTC($utc);
}

// Look up calendar date of start date
$month_name = date('F Y', $tmin['utc'] + 1);
$month = date('n', $tmin['utc'] + 1);
$year = date('Y', $tmin['utc'] + 1);

// Look up which months to put on the "prev" and "next" buttons
$prev_month = date('n', $tmin['utc'] - 10 * 24 * 3600);
$prev_month_year = date('Y', $tmin['utc'] - 10 * 24 * 3600);
$next_month = date('n', $tmin['utc'] + 40 * 24 * 3600);
$next_month_year = date('Y', $tmin['utc'] + 40 * 24 * 3600);

$days_in_month = date('t', $tmin['utc'] + 1);
$day_offset = date('w', $tmin['utc'] + 1);
$period = 24 * 3600;

$byday = [];

// Fetch observatory activity history
function get_activity_history($metaKey, $suffix, $url)
{
    global $byday, $const, $tmin, $period, $obstory, $days_in_month, $year, $month;
    $count = 0;
    while ($count < $days_in_month) {
        $a = floor($tmin['utc'] / 86400) * 86400 + 43200 + $period * $count;
        $b = $a + $period;
        $count++;
        $stmt = $const->db->prepare("
SELECT COUNT(*) FROM archive_observations o
INNER JOIN archive_observatories l ON o.observatory = l.uid
INNER JOIN archive_semanticTypes s ON o.obsType = s.uid
WHERE l.publicId=:o AND s.name=:k AND o.obsTime>=:x AND o.obsTime<:y LIMIT 1");
        $stmt->bindParam(':o', $o, PDO::PARAM_STR, strlen($obstory));
        $stmt->bindParam(':k', $k, PDO::PARAM_STR, strlen($metaKey));
        $stmt->bindParam(':x', $x, PDO::PARAM_INT);
        $stmt->bindParam(':y', $y, PDO::PARAM_INT);
        $stmt->execute(['o' => $obstory, 'k' => $metaKey, 'x' => $a, 'y' => $b]);
        $items = $stmt->fetchAll()[0]['COUNT(*)'];
        if ($items > 0) {
            $tomorrow = $count + 1;
            $text = "<a href='{$url}?obstory={$obstory}&year1={$year}&month1={$month}&day1={$count}&hour1=12&minute1=0" .
                "&year2={$year}&month2={$month}&day2={$tomorrow}&hour2=12&minute2=0" .
                "&flag_lenscorr=1'>" .
                "<span class='cal_number'>{$items}</span><span class='cal_type'>{$suffix}</span></a>";
        } else {
            $text = "";
        }
        $byday[$count][] = $text;
    }
}

get_activity_history("pigazing:timelapse/", " still images", "search_still.php");
get_activity_history("pigazing:movingObject/", " moving objects", "search_moving.php");

$pageInfo = [
    "pageTitle" => "Activity history for {$obstory_name}",
    "pageDescription" => "Pi Gazing",
    "activeTab" => "cameras",
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => [],
    "breadcrumb" => [["observatory_activity_all.php", "Activity log"], ["observatory.php?id=" . $obstory, $obstory_name]]
];


$pageTemplate->header($pageInfo);

?>
    <div class="row">
        <div class="col-md-10">

            <div style="text-align: center; font-size:26px; padding-top:20px;">
                <a href="observatory_activity.php?id=<?php echo $obstory; ?>&month=<?php echo $prev_month; ?>&year=<?php echo $prev_month_year; ?>">
                    <span class="mp-img mp-img-leftB"></span>
                </a>
                <?php echo $month_name; ?>
                <a href="observatory_activity.php?id=<?php echo $obstory; ?>&month=<?php echo $next_month; ?>&year=<?php echo $next_month_year; ?>">
                    <span class="mp-img mp-img-rightB"></span>
                </a>
            </div>

            <div style="text-align:center;">
                Camera active between <?php echo $obstory_info['oldest_obs_date_short']; ?> and
                <?php echo $obstory_info['newest_obs_date_short']; ?>.
            </div>

            <div style="padding:4px;overflow-x:scroll;">
                <table class="dcf_calendar">
                    <thead>
                    <tr>
                        <td>
                            <?php
                            print implode("</td><td>", ['Sun', 'Mon', 'Tue', 'Wed', 'Thur', 'Fri', 'Sat']);
                            ?>
                        </td>
                    </tr>
                    </thead>
                    <tbody>
                    <tr>

                        <?php
                        for ($i = 0; $i < $day_offset; $i++) {
                            print "<td class='even'></td>";
                        }

                        $nowutc = time();
                        $nowyear = intval(date("Y", $nowutc));
                        $nowmc = intval(date("n", $nowutc));
                        $nowday = intval(date("j", $nowutc));
                        for ($day = 1; $day <= $days_in_month; $day++) {
                            print "<td class='odd'>";
                            print "<div class=\"cal_day\">${day}</div><div class=\"cal_body\">";
                            $all_blank = true;
                            $output = "";
                            foreach ($byday[$day] as $s) {
                                if (strlen($s) > 0) $all_blank = false;
                                $output .= "<div style='height:55px;'>{$s}</div>";
                            }
                            if ($all_blank) $output = "<div style='height:55px;'><span class='cal_type'>No data</span></div>";
                            print "{$output}</div></td>";
                            $day_offset++;
                            if ($day_offset == 7) {
                                $day_offset = 0;
                                print "</tr>";
                                if ($day < $days_in_month) print"<tr>";
                            }
                        }

                        if ($day_offset > 0) {
                            for ($day = $day_offset; $day < 7; $day++) {
                                print "<td class='even'></td>";
                            }
                            print "</tr>";
                        }

                        ?>
                    </tbody>
                </table>
            </div>

        </div>

        <div class="col-md-2">

            <div style="cursor:pointer;">
                <form action="observatory_activity_year.php">
                    <input type="hidden" name="id" value="<?php echo $obstory; ?>"/>
                    <input type="hidden" name="year" value="<?php echo $year; ?>"/>
                    <button type="submit" class="btn btn-secondary btn-sm">
                        <i class="fa fa-calendar" aria-hidden="true"></i>
                        Whole year view
                    </button>
                </form>
            </div>


            <h4>Select month</h4>
            <form method="get" action="observatory_activity.php">
                <input type="hidden" name="id" value="<?php echo $obstory; ?>">
                <?php
                html_getargs::makeFormSelect("month", $tmin['mc'], $getargs->months, 0);
                html_getargs::makeFormSelect("year", $tmin['year'], range($const->yearMin, $const->yearMax), 0);
                ?>
                <br/>
                <input class="btn btn-primary btn-sm" style="margin:12px;" type="submit" name="Update" value="Update">
            </form>

            <div style="padding-top:25px;">
                <?php
                $pageTemplate->listObstories($obstories,
                    "observatory_activity.php?year={$tmin['year']}&month={$tmin['mc']}&id=");
                ?>
            </div>

        </div>
    </div>

<?php
$pageTemplate->footer($pageInfo);


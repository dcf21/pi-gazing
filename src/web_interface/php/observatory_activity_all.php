<?php

// observatory_activity_year.php
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

require_once "php/imports.php";
require_once "php/html_getargs.php";
require_once "php/observatory_info.php";

$getargs = new html_getargs(false);

// Fetch list of observatories
$obstories = $getargs->obstory_objlist;

$obstory_info = observatory_info::obstory_info($obstory);

// Read which year to cover
$tmin = $getargs->readTime('year', null, null, null, null, null, $const->yearMin, $const->yearMax);

// Look up calendar date of start date
$year = date('Y', $tmin['utc'] + 1);

// Look up which months to put on the "prev" and "next" buttons
$prev_year = $year - 1;
$next_year = $year + 1;

$by_month = [];

// Fetch observatory activity history
function get_activity_history($metaKey, $url)
{
    global $by_month, $const, $obstory, $year;
    for ($mc = 1; $mc <= 12; $mc++) {
        $a = mktime(0, 0, 1, $mc, 1, $year);
        if ($mc == 12) $b = $a + 31 * 86400;
        else $b = mktime(0, 0, 1, $mc + 1, 1, $year);
        $stmt = $const->db->prepare("
SELECT 1 FROM archive_observations o
INNER JOIN archive_observatories l ON o.observatory = l.uid
INNER JOIN archive_semanticTypes s ON o.obsType = s.uid
WHERE l.publicId=:o AND s.name=:k AND o.obsTime>=:x AND o.obsTime<:y LIMIT 1");
        $stmt->bindParam(':o', $o, PDO::PARAM_STR, strlen($obstory));
        $stmt->bindParam(':k', $k, PDO::PARAM_STR, strlen($metaKey));
        $stmt->bindParam(':x', $x, PDO::PARAM_INT);
        $stmt->bindParam(':y', $y, PDO::PARAM_INT);
        $stmt->execute(['o' => $obstory, 'k' => $metaKey, 'x' => $a, 'y' => $b]);
        $items = $stmt->fetchAll();
        if (count($items) > 0) {
            $text = "<span style='font-weight:bold;'><a href='{$url}?id={$obstory}&year={$year}&month={$mc}'>Active</a></span>";
        } else {
            $text = "<span style='color:#ccc;'>Inactive</span>";
        }
        $by_month[$mc][] = $text;
    }
}

foreach ($obstories as $obstory_info) {
    $obstory = $obstory_info['publicId'];
    get_activity_history("timelapse", "observatory_activity.php");
}

$pageInfo = [
    "pageTitle" => "pigazing activity history",
    "pageDescription" => "Pi Gazing",
    "activeTab" => "cameras",
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => [],
];


$pageTemplate->header($pageInfo);

?>
    <div class="row">
        <div class="col-md-10">

            <div style="text-align: center; font-size:26px; padding-top:20px;">
                <a href="observatory_activity_all.php?year=<?php echo $prev_year; ?>">
                    <span class="mp-img mp-img-leftB"></span>
                </a>
                <?php echo $year; ?>
                <a href="observatory_activity_all.php?year=<?php echo $next_year; ?>">
                    <span class="mp-img mp-img-rightB"></span>
                </a>
            </div>

            <div style="padding:12px;overflow-x:scroll;" class="centred_table">
                <table class="bordered stripy centred">
                    <thead>
                    <tr>
                        <td>Month</td>
                        <?php foreach ($obstories as $obstory): ?>
                            <td><div class='div-rotated'><div class='content'><?php echo $obstory['name']; ?></div></div></td>
                        <?php endforeach; ?>
                    </tr>
                    </thead>
                    <tbody>
                    <?php
                    $month_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
                    for ($mc = 1; $mc <= 12; $mc++) {
                        print "<tr><td>{$month_names[$mc-1]}</td>";
                        foreach ($by_month[$mc] as $column) {
                            print "<td>{$column}</td>";
                        }
                    }
                    ?>
                    </tbody>
                </table>
            </div>

        </div>

        <div class="col-md-2">
            <h4>Select year</h4>
            <form method="get" action="observatory_activity_all.php">
                <?php
                html_getargs::makeFormSelect("year", $year, range($const->yearMin, $const->yearMax), 0);
                ?>
                <br/>
                <input class="btn btn-primary btn-sm" style="margin:12px;" type="submit" name="Update" value="Update">
            </form>
        </div>
    </div>

<?php
$pageTemplate->footer($pageInfo);


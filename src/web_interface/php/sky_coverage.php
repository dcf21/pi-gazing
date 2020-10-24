<?php

// sky_coverage.php
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

require "php/imports.php";
require_once "php/html_getargs.php";

$getargs = new html_getargs(true);

$pageInfo = [
    "pageTitle" => "Sky coverage charts",
    "pageDescription" => "Pi Gazing",
    "fluid" => true,
    "activeTab" => "search",
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => []
];

$sky_chart_metadata = [];

// Look up duration of graph
$durationList = [
    [0, "1 day", 1, 1],
    [1, "2 days", 2, 1],
    [2, "1 week", 7, 1],
    [3, "2 weeks", 14, 1],
    [4, "1 month", 30, 1],
    [5, "2 months", 60, 1],
    [6, "3 months", 90, 1],
    [7, "6 months", 180, 2],
    [8, "1 year", 365, 4]
];

if (array_key_exists('duration', $_GET) && is_string($_GET['duration'])) $durationCode = $_GET['duration'];
else                                     $durationCode = 6;
if (!array_key_exists($durationCode, $durationList)) {
    $durationCode = 6;
}
if (!array_key_exists($durationCode, $durationList)) {
    die ("Could not find a suitable duration.");
}
$durationInfo = $durationList[$durationCode];

// Read which time range to cover
$t1 = time() - 90 * 3600 * 24;
$tmin = $getargs->readTime('year1', 'month1', 'day1', 'hour1', 'min1', null, $const->yearMin, $const->yearMax, $t1);
$utc_max = $tmin['utc'] + $durationList[$durationInfo[0]][2] * 3600 * 24;

// Which observatory are we searching for images from?
$obstory = $getargs->readObservatory("obstory");

// Read image options
$flag_highlights = 1;

$pageTemplate->header($pageInfo);

?>

    <p>
        Use this form to generate charts of sky areas covered by Pi Gazing cameras.
    </p>
    <form class="form-horizontal search-form" method="get" action="sky_coverage.php#results">
        <div class="form-item-holder">
            <div class="form-item" style="margin: 0 16px 16px 0;">
                <p class="formlabel">Time of observation</p>
                <b>From</b>
                <?php
                $getargs->makeFormSelect("day1", $tmin['day'], range(1, 31), 0);
                $getargs->makeFormSelect("month1", $tmin['mc'], $getargs->months, 0);
                ?>
                <input name="year1" class="year" style="max-width:80px;"
                       type="number" step="1"
                       min="<?php echo $const->yearMin; ?>" max="<?php echo $const->yearMax; ?>"
                       value="<?php echo $tmin['year']; ?>"/>
                <?php
                print "</span><span>";
                $getargs->makeFormSelect("hour1", $tmin['hour'], $getargs->hours, 0);
                print "&nbsp;<b>:</b>&nbsp;";
                $getargs->makeFormSelect("min1", $tmin['min'], $getargs->mins, 0);
                ?>
            </div>
            <div class="form-item" style="margin: 0 16px 16px 0;">
                <p class="formlabel">Time span</p>
                <b>Spanning</b>
                <?php
                html_getargs::makeFormSelect("duration", $durationInfo[0], $durationList, 0);
                ?>
            </div>
            <div class="form-item" style="margin: 0 16px 16px 0;">
                <p class="formlabel">Observed by camera</p>
                <?php
                $getargs->makeFormSelect("obstory", $obstory, $getargs->obstories, 1);
                ?>
            </div>
            <div class="form-item-notitle">
                <input class="btn btn-primary" type="submit" value="Update chart"/>
            </div>
        </div>
    </form>

    <hr/>

    <div id="results"></div>

<?php

// Display results if and only if we are searching
$searching = true;
if ($searching) {

    // Work out which semantic type to search for
    $semantic_type = "pigazing:timelapse";

    // Search for results
    $where = ["o.obsTime BETWEEN {$tmin['utc']} AND {$utc_max}"];

    if ($flag_highlights)
        $where[] = "o.featured";

    if ($obstory != "Any") $where[] = 'l.publicId="' . $obstory . '"';

    $search = ("
archive_observations o
INNER JOIN archive_files f ON f.observationId = o.uid
           AND f.semanticType=(SELECT uid FROM archive_semanticTypes WHERE name=\"{$semantic_type}\")
INNER JOIN archive_observatories l ON o.observatory = l.uid
WHERE o.obsType = (SELECT uid FROM archive_semanticTypes WHERE name=\"pigazing:timelapse/\")
      AND o.positionAngle IS NOT NULL
      AND " . implode(' AND ', $where));

    $stmt = $const->db->prepare("
SELECT o.obsTime, f.repositoryFname, ST_AsText(o.skyArea) AS skyPolygon,
       l.publicId AS observatory, l.name AS observatory_name
FROM ${search}
ORDER BY o.obsTime LIMIT 5000;");
    $stmt->execute([]);
    $result_list = $stmt->fetchAll();
    $result_count = count($result_list);

    // List of colours to apply to observatories
    $colour_list = ["#FF0000", "#00FF00", "#0000FF", "#FF00FF", "#00FFFF", "#FFFF00"];

    // Compile list of unique observatories
    $observatory_colours = [];
    $observatory_names = [];
    $observatory_list = [];

    foreach ($result_list as $result) {
        if (in_array($result['observatory'], $observatory_list)) continue;

        $colour_index = count($observatory_list) % count($colour_list);
        $observatory_colours[$result['observatory']] = $colour_list[$colour_index];
        $observatory_names[$result['observatory']] = $result['observatory_name'];
        array_push($observatory_list, $result['observatory']);
    }

    // Display result counter
    if ($result_count == 0):
        ?>
        <div class="alert alert-success">
            <p><b>No results found</b></p>

            <p>
                The query completed, but no observations were found matching the constraints you specified.
                Try altering values in the form above and re-running the query.
            </p>
        </div>
    <?php
    else:
        $sky_polygons = [];
        foreach ($result_list as $result) {
            // Make string describing the time of observation
            $date_string = date("d M Y - H:i", $result['obsTime']);

            // Assemble HTML code for the text which appears when hovering over an item
            $html_hover_text = "
            <p>{$date_string}</p>
            ";

            // Look up which colour to use for this observatory
            $colour = $observatory_colours[$result['observatory']];

            // Convert the MULTIPOLYGON string output by MySQL into a list of coordinates
            preg_match('/MULTIPOLYGON\(\(\((.*?)\)\)\)/', $result['skyPolygon'], $match);
            $multipolygon_string = $match[1];
            $multipolygon_points = explode(',', $multipolygon_string);
            $point_list = [[
                $html_hover_text,
                "{$const->server}image.php?id={$result['repositoryFname']}",
                $colour
            ]];
            foreach ($multipolygon_points as $multipolygon_point) {
                $multipolygon_coordinates = explode(' ', $multipolygon_point);
                array_push($point_list, [floatval($multipolygon_coordinates[0]),
                    floatval($multipolygon_coordinates[1])]);
            }
            array_push($sky_polygons, $point_list);
        }
        ?>

        <div class="sky_coverage_chart" style="text-align: center;"
             data-meta='<?php echo json_encode($sky_chart_metadata); ?>'
             data-polygons='<?php echo json_encode($sky_polygons); ?>'>
            <div style="display: inline-block; position: relative;">
                <div class="annotation-hover PLhover"
                     style="position:absolute;top:0;left:0;display:none;text-align:left;z-index:195;"></div>
                <canvas class="sky_chart_canvas" width="1" height="1"></canvas>
            </div>
        </div>

        <div>
            <?php foreach ($observatory_list as $observatory_id): ?>
                <div>
                <span style="font-size: 18px; font-weight: bold; color:<?php echo $observatory_colours[$observatory_id] ?>">
                    &mdash;&nbsp;
                </span>
                    <?php echo $observatory_names[$observatory_id]; ?>
                </div>
            <?php endforeach; ?>
        </div>

        <!--
        <table class="stripy bordered bordered_slim">
            <thead>
            <tr>
                <td>Date</td>
                <td>Sky area</td>
            </tr>
            </thead>
            <tbody>
            <?php
        for ($index = 0; $index < count($result_list); $index++):
            $result = $result_list[$index];
            ?>
                <tr>
                    <td><?php echo date("d M Y - H:i", $result['obsTime']); ?></td>
                    <td><?php echo json_encode($sky_polygons[$index]); ?></td>
                </tr>
            <?php endfor; ?>
            </tbody>
        </table>
        -->
    <?php
    endif;

}

$pageTemplate->footer($pageInfo);

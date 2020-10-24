<?php

// sky_clarity.php
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
    "pageTitle" => "Sky clarity charts",
    "pageDescription" => "Pi Gazing",
    "activeTab" => "search",
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => []
];

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
else                                     $durationCode = 2;
if (!array_key_exists($durationCode, $durationList)) {
    $durationCode = 2;
}
if (!array_key_exists($durationCode, $durationList)) {
    die ("Could not find a suitable duration.");
}
$durationInfo = $durationList[$durationCode];

// Read which time range to cover
$t1 = time() - 7 * 3600 * 24;
$tmin = $getargs->readTime('year1', 'month1', 'day1', 'hour1', 'min1', null, $const->yearMin, $const->yearMax, $t1);
$utc_max = $tmin['utc'] + $durationList[$durationInfo[0]][2] * 3600 * 24;

// Which observatory are we searching for images from?
$obstory = $getargs->readObservatory("obstory");

// Read image options
$flag_bgsub = 0;
$flag_highlights = 0;

if (array_key_exists("flag_bgsub", $_GET)) $flag_bgsub = 1;

$pageTemplate->header($pageInfo);

?>

    <p>
        Use this form to generate charts of sky clarity estimates based on still images recorded by Pi Gazing cameras.
    </p>
    <form class="form-horizontal search-form" method="get" action="sky_clarity.php#results">
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
            <div class="form-item" style="margin: 0 16px 16px 0;">
                <p class="formlabel">Image options</p>
                <label>
                    <input type="checkbox" name="flag_bgsub"
                        <?php if ($flag_bgsub) echo 'checked="checked"'; ?> >
                    Use images with light pollution removed
                </label>
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
    if ($flag_bgsub) $semantic_type = "pigazing:timelapse/backgroundSubtracted";
    else $semantic_type = "pigazing:timelapse";

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
INNER JOIN archive_metadata d2 ON f.uid = d2.fileId
           AND d2.fieldId = (SELECT uid FROM archive_metadataFields WHERE metaKey=\"pigazing:skyClarity\")
WHERE o.obsType = (SELECT uid FROM archive_semanticTypes WHERE name=\"pigazing:timelapse/\")
      AND " . implode(' AND ', $where));

    $stmt = $const->db->prepare("
SELECT o.obsTime, d2.floatValue AS skyClarity, l.publicId AS obstoryId, l.name AS obstoryName
FROM ${search}
ORDER BY o.obsTime LIMIT 5000;");
    $stmt->execute([]);
    $result_list = $stmt->fetchAll();
    $result_count = count($result_list);

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
        $obstory_ids = [];
        $obstory_names = [];
        $graph_data = [];

        foreach ($result_list as $result) {
            $obstory_index = array_search($result['obstoryId'], $obstory_ids);
            if ($obstory_index === false) {
                $obstory_ids[] = $result['obstoryId'];
                $obstory_names[] = $result['obstoryName'];
                $graph_data[] = [];
                $obstory_index = array_search($result['obstoryId'], $obstory_ids);
            }
            $graph_data[$obstory_index][] = [$result['obsTime'], $result['skyClarity']];
        };

        $graph_metadata = [
            'y-axis' => 'Sky clarity',
            'data' => $graph_data,
            'data_set_titles' => $obstory_names
        ];

        ?>

        <div class="chart_holder" data-meta='<?php echo json_encode($graph_metadata); ?>'>
            <div class="chart_div"></div>
        </div>

        <table class="stripy bordered bordered_slim">
            <thead>
            <tr>
                <td>Date</td>
                <td>Observatory</td>
                <td>Sky clarity</td>
            </tr>
            </thead>
            <tbody>
            <?php foreach ($result_list as $result): ?>
                <tr>
                    <td><?php echo date("d M Y - H:i", $result['obsTime']); ?></td>
                    <td><?php echo $result['obstoryName']; ?></td>
                    <td style="text-align:right;"><?php printf("%.1f", $result['skyClarity']); ?></td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
    <?php
    endif;

}

$pageTemplate->footer($pageInfo);

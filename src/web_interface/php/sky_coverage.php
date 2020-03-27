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
    "activeTab" => "search",
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => []
];

// Read which time range to cover
$t2 = time();
$t1 = $t2 - 2 * 3600 * 24;
$tmin = $getargs->readTime('year1', 'month1', 'day1', 'hour1', 'min1', null, $const->yearMin, $const->yearMax, $t1);
$tmax = $getargs->readTime('year2', 'month2', 'day2', 'hour2', 'min2', null, $const->yearMin, $const->yearMax, $t2);

// Which observatory are we searching for images from?
$obstory = $getargs->readObservatory("obstory");

// Swap times if they are the wrong way round
if ($tmax['utc'] < $tmin['utc']) {
    $tmp = $tmax;
    $tmax = $tmin;
    $tmin = $tmp;
}

// Read image options
$flag_highlights = 1;

$pageTemplate->header($pageInfo);

?>

    <p>
        Use this form to generate charts of sky areas covered by Pi Gazing cameras.
    </p>
    <form class="form-horizontal search-form" method="get" action="sky_coverage.php#results">

        <div style="cursor:pointer;text-align:right;">
            <button type="button" class="btn btn-secondary btn-sm help-toggle">
                <i class="fa fa-info-circle" aria-hidden="true"></i>
                Show tips
            </button>
        </div>
        <div class="row">
            <div class="search-form-column col-lg-12">

                <div><span class="formlabel">Time of observation</span></div>
                <div class="tooltip-holder">
                    <span class="formlabel2">Between</span>

                    <div class="form-group-dcf"
                         data-toggle="tooltip" data-pos="tooltip-above"
                         title="Search for objects seen after this date and time."
                    >
                        <span style="display:inline-block; padding-right:20px;">
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
                        </span>
                    </div>
                </div>

                <div class="tooltip-holder">
                    <span class="formlabel2">and</span>

                    <div class="form-group-dcf"
                         data-toggle="tooltip" data-pos="tooltip-below"
                         title="Search for objects seen before this date and time."
                    >
                        <span style="display:inline-block; padding-right:20px;">
                        <?php
                        $getargs->makeFormSelect("day2", $tmax['day'], range(1, 31), 0);
                        $getargs->makeFormSelect("month2", $tmax['mc'], $getargs->months, 0);
                        ?>
                        <input name="year2" class="year" style="max-width:80px;"
                               type="number" step="1"
                               min="<?php echo $const->yearMin; ?>" max="<?php echo $const->yearMax; ?>"
                               value="<?php echo $tmax['year']; ?>"/>
                        <?php
                        print "</span><span>";
                        $getargs->makeFormSelect("hour2", $tmax['hour'], $getargs->hours, 0);
                        print "&nbsp;<b>:</b>&nbsp;";
                        $getargs->makeFormSelect("min2", $tmax['min'], $getargs->mins, 0);
                        ?>
                        </span>
                    </div>
                </div>

                <div style="margin-top:25px;"><span class="formlabel">Observed by camera</span></div>
                <div class="tooltip-holder">
                    <span class="formlabel2"></span>

                    <div class="form-group-dcf"
                         data-toggle="tooltip" data-pos="tooltip-below"
                         title="Use this to display images from only one camera in the Pi Gazing network. Set to 'Any' to display images from all Pi Gazing cameras."
                    >
                        <?php
                        $getargs->makeFormSelect("obstory", $obstory, $getargs->obstories, 1);
                        ?>
                    </div>
                </div>

                <div style="padding:40px 0 40px 0;">
                    <span class="formlabel2"></span>
                    <button type="submit" class="btn btn-primary" data-bind="click: performSearch">Search</button>
                </div>

            </div>
        </div>

    </form>

    <div id="results"></div>

<?php

// Display results if and only if we are searching
$searching = true;
if ($searching) {

    // Work out which semantic type to search for
    $semantic_type = "pigazing:timelapse";

    // Search for results
    $where = ["o.obsTime BETWEEN {$tmin['utc']} AND {$tmax['utc']}"];

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
SELECT o.obsTime, ST_AsText(o.skyArea) AS skyPolygon
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
        ?>
        <table class="stripy bordered bordered_slim">
            <thead>
            <tr>
                <td>Date</td>
                <td>Sky area</td>
            </tr>
            </thead>
            <tbody>
            <?php foreach ($result_list as $result): ?>
                <tr>
                    <td><?php echo date("d M Y - H:i", $result['obsTime']); ?></td>
                    <td><?php echo $result['skyPolygon'] ?></td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
    <?php
    endif;

}

$pageTemplate->footer($pageInfo);

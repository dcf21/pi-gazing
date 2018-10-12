<?php

// search_moving.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

// -------------------------------------------------
// Copyright 2016 Cambridge Science Centre.

// This file is part of Meteor Pi.

// Meteor Pi is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Meteor Pi is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Meteor Pi.  If not, see <http://www.gnu.org/licenses/>.
// -------------------------------------------------

require "php/imports.php";
require_once "php/html_getargs.php";

$getargs = new html_getargs(true);

$pageInfo = [
    "pageTitle" => "Search for moving objects",
    "pageDescription" => "Meteor Pi",
    "activeTab" => "search",
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => []
];

// Paging options
$pageSize = 24;
$pageNum = 1;
if (array_key_exists("page", $_GET) && is_numeric($_GET["page"])) $pageNum = $_GET["page"];

// Read which time range to cover
$t2 = time();
$t1 = $t2 - 3600 * 24 * 5;
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

// Read duration options
$duration_min = 0;
$duration_max = 100;
$duration_min_str = $duration_max_str = "";

if (array_key_exists("duration_min", $_GET) && is_numeric($_GET["duration_min"])) {
    $duration_min = $_GET["duration_min"];
    if ($duration_min < 0) $duration_min = 0;
    if ($duration_min > 60) $duration_min = 60;
    $duration_min_str = sprintf("%.2f", $duration_min);
}

if (array_key_exists("duration_max", $_GET) && is_numeric($_GET["duration_max"])) {
    $duration_max = $_GET["duration_max"];
    if ($duration_max < 0) $duration_max = 0;
    if ($duration_max > 60) $duration_max = 60;
    $duration_max_str = sprintf("%.2f", $duration_max);
}

$pageTemplate->header($pageInfo);

?>

    <p>
        Use this form to search for bright moving objects spotted by our cameras. Most of the objects you'll see here
        are aircraft, satellites, shooting stars, and other airborne lights.
    </p>
    <form class="form-horizontal search-form" method="get" action="/search_moving.php#results">

        <div style="cursor:pointer;text-align:right;">
            <button type="button" class="btn btn-secondary btn-sm help-toggle">
                <i class="fa fa-info-circle" aria-hidden="true"></i>
                Show tips
            </button>
        </div>
        <div class="row">
            <div class="search-form-column col-lg-6">

                <div><span class="formlabel">Time of observation</span></div>
                <div class="tooltip-holder">
                    <span class="formlabel2">Between</span>

                    <div class="form-group-dcf"
                         data-toggle="tooltip" data-pos="tooltip-above"
                         title="Search for images recorded after this date and time."
                    >
                        <span style="display:inline-block; padding-right:20px;">
                        <?php
                        $getargs->makeFormSelect("day1", $tmin['day'], range(1, 31), 0);
                        $getargs->makeFormSelect("month1", $tmin['mc'], $getargs->months, 0);
                        $getargs->makeFormSelect("year1", $tmin['year'], range($const->yearMin, $const->yearMax), 0);
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
                         title="Search for images recorded before this date and time."
                    >
                        <span style="display:inline-block; padding-right:20px;">
                        <?php
                        $getargs->makeFormSelect("day2", $tmax['day'], range(1, 31), 0);
                        $getargs->makeFormSelect("month2", $tmax['mc'], $getargs->months, 0);
                        $getargs->makeFormSelect("year2", $tmax['year'], range($const->yearMin, $const->yearMax), 0);
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
                         title="Use this to display images from only one camera in the Meteor Pi network. Set to 'Any' to display images from all Meteor Pi cameras."
                    >
                        <?php
                        $getargs->makeFormSelect("obstory", $obstory, $getargs->obstories, 1);
                        ?>
                    </div>
                </div>

            </div>
            <div class="search-form-column col-lg-6">

                <div style="margin-top:25px;"><span class="formlabel">Duration of appearance</span></div>
                <div class="tooltip-holder"><span
                        data-toggle="tooltip" data-pos="tooltip-above"
                        title="Search for objects visible for longer than this period. Set to around 5 sec to see only planes and satellites."
                    >
                        <span class="formlabel2">Minimum</span>
                    <input class="form-control-dcf form-inline-number"
                           name="duration_min"
                           style="width:70px;"
                           type="text"
                           value="<?php echo $duration_min_str; ?>"
                    />&nbsp;seconds
                </span></div>

                <div class="tooltip-holder"><span
                        data-toggle="tooltip" data-pos="tooltip-below"
                        title="Search for objects visible for less than this period. Set to around 5 sec to filter out planes and satellites, which are visible for long periods."
                    >
                        <span class="formlabel2">Maximum</span>
                    <input class="form-control-dcf form-inline-number"
                           name="duration_max"
                           style="width:70px;"
                           type="text"
                           value="<?php echo $duration_max_str; ?>"
                    />&nbsp;seconds
                </span></div>


            </div>
        </div>

        <div style="padding:30px 0 40px 0;">
            <span class="formlabel2"></span>
            <button type="submit" class="btn btn-primary" data-bind="click: performSearch">Search</button>
        </div>

    </form>

    <div id="results"></div>

<?php

// Display results if and only if we are searching
if (array_key_exists('obstory', $_GET)) {

    // Search for results
    $semantic_type = "meteorpi:triggers/event/maxBrightness/lensCorr";

    $where = ["o.obsTime BETWEEN {$tmin['utc']} AND {$tmax['utc']}"];

    if ($obstory != "Any") $where[] = 'l.publicId="' . $obstory . '"';

    $search = ("
archive_observations o
INNER JOIN archive_files f ON f.observationId = o.uid AND
    f.semanticType=(SELECT uid FROM archive_semanticTypes WHERE name=\"{$semantic_type}\")
INNER JOIN archive_observatories l ON o.observatory = l.uid
INNER JOIN archive_metadata d ON o.uid = d.observationId AND
    d.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey=\"meteorpi:duration\") AND
    d.floatValue>={$duration_min} AND d.floatValue<={$duration_max}
LEFT OUTER JOIN archive_metadata d2 ON o.uid = d2.observationId AND
    d2.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey=\"meteorpi:pathBezier\")
WHERE o.obsType = (SELECT uid FROM archive_semanticTypes WHERE name=\"movingObject\")
    AND " . implode(' AND ', $where));

    $stmt = $const->db->prepare("SELECT COUNT(*) FROM ${search};");
    $stmt->execute([]);
    $result_count = $stmt->fetchAll()[0]['COUNT(*)'];
    $result_list = [];

    $lastPage = ceil($result_count / $pageSize);
    if ($pageNum < 1) $pageNum = 1;
    if ($pageNum > $lastPage) $pageNum = $lastPage;
    $pageSkip = ($pageNum - 1) * $pageSize;

    if ($result_count > 0) {
        $stmt = $const->db->prepare("
SELECT f.repositoryFname, f.fileName, o.publicId AS observationId,
o.obsTime, l.publicId AS obstoryId, l.name AS obstoryName, f.mimeType AS mimeType,
d2.stringValue AS path
FROM ${search} ORDER BY o.obsTime DESC LIMIT {$pageSize} OFFSET {$pageSkip};");
        $stmt->execute([]);
        $result_list = $stmt->fetchAll();
    }

    $gallery_items = [];
    foreach ($result_list as $item) {
        $gallery_items[] = ["fileId" => $item['repositoryFname'],
            "filename" => $item["fileName"],
            "caption" => $item['obstoryName'] . "<br/>" . date("d M Y \\a\\t H:i", $item['obsTime']),
            "hover" => null,
            "path" => $item["path"],
            "linkId" => $item['observationId'],
            "mimeType" => $item['mimeType']];
    }

    // Display result counter
    if ($result_count == 0):
        ?>
        <div class="alert alert-success">
            <p><b>No results found</b></p>

            <p>
                The query completed, but no files were found matching the constraints you specified. Try altering values
                in the form above and re-running the query.
            </p>
        </div>
        <?php
    elseif ($result_count == count($result_list)):
        ?>
        <div class="alert alert-success">
            <p>Showing all <?php echo $result_count; ?> results.</p>
        </div>
        <?php
    else:
        ?>
        <div class="alert alert-success">
            <p>
                Showing results <?php echo $pageSkip + 1; ?> to <?php echo $pageSkip + 1 + count($result_list); ?>
                of <?php echo $result_count; ?>.
            </p>
        </div>
        <?php
    endif;

    // Display results
    $pageTemplate->imageGallery($gallery_items, "/moving_obj.php?id=", true);

    // Display pager
    if (count($result_list) < $result_count) {
        $self_url = "search_moving.php?obstory={$obstory}&year1={$tmin['year']}&month1={$tmin['mc']}&day1={$tmin['day']}&" .
            "hour1={$tmin['hour']}&min1={$tmin['min']}&" .
            "year2={$tmax['year']}&month2={$tmax['mc']}&day2={$tmax['day']}&" .
            "hour2={$tmax['hour']}&min2={$tmax['min']}&" .
            "duration_min={$duration_min_str}&duration_max={$duration_max_str}";
        $pageTemplate->showPager($result_count, $pageNum, $pageSize, $self_url);
    }

}

// Page footer
$pageTemplate->footer($pageInfo);

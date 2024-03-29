<?php

// search_multi.php
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

require "php/imports.php";
require_once "php/html_getargs.php";

$getargs = new html_getargs(true);

$pageInfo = [
    "pageTitle" => "Search for multi-camera detections",
    "pageDescription" => "Pi Gazing",
    "fluid" => true,
    "activeTab" => "search",
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => []
];

// Paging options
$pageSize = 50;
$pageNum = 1;
if (array_key_exists("page", $_GET) && is_numeric($_GET["page"])) $pageNum = $_GET["page"];

// Read which time range to cover
$day = 86400;
$t2 = (floor(time() / $day) + 0.5) * $day;
$t1 = $t2 - 90 * $day; // Default span of 90 days
$tmin = $getargs->readTime('year1', 'month1', 'day1', 'hour1', 'min1', null, $const->yearMin, $const->yearMax, $t1);
$tmax = $getargs->readTime('year2', 'month2', 'day2', 'hour2', 'min2', null, $const->yearMin, $const->yearMax, $t2);

// Which observatory are we searching for images from?
$obstory = $getargs->readObservatory("obstory");

// Which category of objects are we to show
$item_category = $getargs->readCategory("category");

// Swap times if they are the wrong way round
if ($tmax['utc'] < $tmin['utc']) {
    $tmp = $tmax;
    $tmax = $tmin;
    $tmin = $tmp;
}


$pageTemplate->header($pageInfo);

?>

<div class="non-fluid-block">
    <p>
        Use this form to search for simultaneous detections of moving objects by multiple cameras at the same time. In
        some cases, the same object may have been seen by more than one camera, allowing its altitude and speed to be
        triangulated. In other cases, two different objects may coincidentally have been seen at the same time.
    </p>
    <form class="form-horizontal search-form" method="get" action="/search_multi.php#results">

        <div style="cursor:pointer;text-align:right;">
            <button type="button" class="btn btn-secondary help-toggle">
                <i class="fas fa-info-circle" aria-hidden="true"></i>
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
                         title="Search for images recorded before this date and time."
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

            </div>
            <div class="search-form-column col-lg-6">

                <div style="margin-top:25px;"><span class="formlabel">Categorised as</span></div>
                <div class="tooltip-holder">
                    <span class="formlabel2"></span>

                    <div class="form-group-dcf"
                         data-toggle="tooltip" data-pos="tooltip-below"
                         title="Use this to display only events which have already been categorised as being of particular types of object."
                    >
                        <?php
                        $getargs->makeFormSelect("category", $item_category, $getargs->category_list, 1);
                        ?>
                    </div>
                </div>

            </div>
        </div>

        <div style="padding:30px 0 40px 0;">
            <span class="formlabel2"></span>
            <button type="submit" class="btn btn-primary" data-bind="click: performSearch">Search</button>
        </div>

    </form>
</div>

    <div id="results"></div>

<?php

// Display results if and only if we are searching
$searching = true;
if ($searching) {

    // Search for results
    $where = ['s.name="pigazing:simultaneous"', "g.time BETWEEN {$tmin['utc']} AND {$tmax['utc']}"];

    if ($obstory != "Any") {
        $where[] = 'EXISTS (SELECT 1 FROM archive_obs_group_members x1
INNER JOIN archive_observations x2 ON x2.uid=x1.observationId
INNER JOIN archive_observatories x3 ON x3.uid=x2.observatory
WHERE x1.groupId=g.uid AND x3.publicId=%s)' % $obstory;
    }

    if ($item_category != "Any") {
        if ($item_category == "Not set") {
            $where[] = 'd5.stringValue IS NULL';
        } else if ($item_category == "Exclude binned observations") {
            $where[] = 'd5.stringValue != "Bin"';
        } else {
            $where[] = 'd5.stringValue="' . $item_category . '"';
        }
    }

    $search = ('
archive_obs_groups g
INNER JOIN archive_semanticTypes s ON g.semanticType=s.uid
LEFT OUTER JOIN archive_metadata d5 ON g.uid = d5.groupId AND
    d5.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="web:category")
WHERE ' . implode(' AND ', $where));

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
SELECT g.uid, g.time, g.setAtTime, g.setByUser, g.publicId, g.title
FROM ${search} ORDER BY g.time DESC LIMIT {$pageSize} OFFSET {$pageSkip};");
        $stmt->execute([]);
        $result_list = $stmt->fetchAll();
    }

    // Display result counter
    if ($result_count == 0):
        ?>
        <div class="alert alert-success">
            <p><b>No results found</b></p>

            <p>
                The query completed, but no events were found matching the constraints you specified. Try altering
                values in the form above and re-running the query.
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
                Showing results <?php echo $pageSkip + 1; ?> to <?php echo $pageSkip + count($result_list); ?>
                of <?php echo $result_count; ?>.
            </p>
        </div>
    <?php
    endif;

    // Display results
    foreach ($result_list as $grp) {
        $where = ["gm.groupId = {$grp['uid']}"];

        $search = ("
archive_obs_group_members gm
INNER JOIN archive_observations o ON gm.childObservation = o.uid
INNER JOIN archive_files f ON f.observationId = o.uid
INNER JOIN archive_observatories l ON o.observatory = l.uid
LEFT OUTER JOIN archive_metadata d2 ON o.uid = d2.observationId AND
    d2.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey=\"pigazing:pathBezier\")
LEFT OUTER JOIN archive_metadata d3 ON o.uid = d3.observationId AND
    d3.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey=\"pigazing:width\")
LEFT OUTER JOIN archive_metadata d4 ON o.uid = d4.observationId AND
    d4.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey=\"pigazing:height\")
LEFT OUTER JOIN archive_metadata d5 ON o.uid = d5.observationId AND
    d5.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey=\"web:category\")
WHERE f.semanticType=(SELECT uid FROM archive_semanticTypes WHERE name=\"pigazing:movingObject/maximumBrightness\")
   AND o.obsType = (SELECT uid FROM archive_semanticTypes WHERE name=\"pigazing:movingObject/\")
   AND gm.groupId = {$grp['uid']}");

        $stmt = $const->db->prepare("
SELECT f.repositoryFname, f.fileName, o.publicId AS observationId,
o.obsTime, l.publicId AS obstoryId, l.name AS obstoryName, f.mimeType AS mimeType,
d2.stringValue AS path, d3.floatValue AS width, d4.floatValue AS height, d5.stringValue AS classification
FROM ${search} ORDER BY obstoryId;");
        $stmt->execute([]);
        $obs_list = $stmt->fetchAll();

        print "<h3>Object observed at " . date("d M Y \\a\\t H:i", $grp['time']) . "</h3>";

        $gallery_items = [];
        foreach ($obs_list as $obs) {
            $gallery_items[] = ["fileId" => $obs['repositoryFname'],
                "filename" => $obs["fileName"],
                "caption" => $obs['obstoryName'],
                "hover" => null,
                "path" => $obs['path'],
                "image_width" => $obs['width'],
                "image_height" => $obs['height'],
                "classification" => $obs['classification'],
                "linkId" => $obs['observationId'],
                "mimeType" => $obs['mimeType']];
        }

        $pageTemplate->imageGallery($gallery_items, "/moving_obj.php?id=", true, false);
    }

    // Display pager
    if (count($result_list) < $result_count) {
        $self_url = "search_multi.php?obstory={$obstory}&category={$item_category}&" .
            "year1={$tmin['year']}&month1={$tmin['mc']}&day1={$tmin['day']}&" .
            "hour1={$tmin['hour']}&min1={$tmin['min']}&" .
            "year2={$tmax['year']}&month2={$tmax['mc']}&day2={$tmax['day']}&" .
            "hour2={$tmax['hour']}&min2={$tmax['min']}";
        $pageTemplate->showPager($result_count, $pageNum, $pageSize, $self_url);
    }

}

// Page footer
$pageTemplate->footer($pageInfo);

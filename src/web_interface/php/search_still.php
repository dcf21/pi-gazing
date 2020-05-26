<?php

// search_still.php
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
    "pageTitle" => "Search for still images",
    "pageDescription" => "Pi Gazing",
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
$t1 = $t2 - 3600 * 24 * 365;
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
$flag_bgsub = 0;
$flag_highlights = 0;

if (array_key_exists("flag_bgsub", $_GET)) $flag_bgsub = 1;
if (array_key_exists("flag_highlights", $_GET)) $flag_highlights = 1;
if (array_key_exists("defaults", $_GET)) $flag_highlights = 1;

// Read sky clarity options
$sky_clarity_min = 0;

if (array_key_exists("clarity", $_GET) && is_numeric($_GET["clarity"])) {
    $sky_clarity_min = intval($_GET["clarity"]);
    if ($sky_clarity_min < 0) $sky_clarity_min = 0;
    if ($sky_clarity_min > 3000) $sky_clarity_min = 3000;
}

// Set default options for if we are not searching
if (!array_key_exists('obstory', $_GET)) {
    $flag_highlights = 1;
}

$pageTemplate->header($pageInfo);

?>

    <p>
        Our cameras take long 30-second exposures of the sky every 30 seconds, and you can use this form to browse
        through these still images and discover what the sky looked like at any time in the past.
    </p>
    <form class="form-horizontal search-form" method="get" action="search_still.php#results">

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
            <div class="search-form-column col-lg-6">

                <div style="margin-top:25px;"><span class="formlabel">Image options</span></div>

                <div class="tooltip-holder" style="display:inline-block;">
                    <div class="checkbox" data-toggle="tooltip" data-pos="tooltip-top"
                         title="Automatically remove light pollution. In clear conditions this makes more stars visible, but it can lead to strange artifacts when cloudy."
                    >
                        <label>
                            <input type="checkbox" name="flag_bgsub"
                                <?php if ($flag_bgsub) echo 'checked="checked"'; ?> >
                            Remove light pollution
                        </label>
                    </div>
                </div>
                <br/>
                <div class="tooltip-holder" style="display:inline-block; padding:0;">
                    <div class="checkbox" data-toggle="tooltip" data-pos="tooltip-right"
                         title="Show only one image per ten-minute interval. Without this, you will see large numbers of similar images."
                    >
                        <label>
                            <input type="checkbox" name="flag_highlights"
                                <?php if ($flag_highlights) echo 'checked="checked"'; ?> >
                            Show fewer results
                        </label>
                    </div>
                </div>

                <div style="margin-bottom:30px;">
                    <div style="margin-top:25px;"><span class="formlabel">Sky clarity</span></div>
                    <div class="tooltip-holder"><span
                            data-toggle="tooltip" data-pos="tooltip-right"
                            title="Search for images with a sky clarity rating better than a certain value."
                        >
                        <span class="formlabel2">Minimum</span>
                    <input class="form-control-dcf form-inline-number"
                           name="clarity"
                           style="width:70px;"
                           type="number" min="0" max="3000" step="10"
                           value="<?php echo $sky_clarity_min; ?>"
                    />&nbsp;(scale 0&ndash;3000)
                </span></div>
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
    if ($flag_bgsub) $semantic_type = "pigazing:timelapse/backgroundSubtracted";
    else $semantic_type = "pigazing:timelapse";

    // Search for results
    $where = ["o.obsTime BETWEEN {$tmin['utc']} AND {$tmax['utc']}"];

    if ($flag_highlights)
        $where[] = "o.featured";

    if ($sky_clarity_min > 0)
        $where[] = "d2.floatValue>{$sky_clarity_min}";

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
SELECT f.repositoryFname, f.fileName, o.obsTime, l.publicId AS obstoryId, l.name AS obstoryName, f.mimeType AS mimeType
FROM ${search}
ORDER BY o.obsTime DESC LIMIT {$pageSize} OFFSET {$pageSkip};");
        $stmt->execute([]);
        $result_list = $stmt->fetchAll();
    }

    $gallery_items = [];
    foreach ($result_list as $item) {
        $gallery_items[] = ["fileId" => $item['repositoryFname'],
            "filename" => $item["fileName"],
            "caption" => $item['obstoryName'] . "<br/>" . date("d M Y \\a\\t H:i", $item['obsTime']),
            "hover" => null,
            "linkId" => $item['repositoryFname'],
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
                Showing results <?php echo $pageSkip + 1; ?> to <?php echo $pageSkip + count($result_list); ?>
                of <?php echo $result_count; ?>.
            </p>
        </div>
        <?php
    endif;

    // Display results
    $pageTemplate->imageGallery($gallery_items,"/image.php?highlights={$flag_highlights}&id=",false);

    // Display pager
    if (count($result_list) < $result_count) {
        $self_url = "search_still.php?obstory={$obstory}&year1={$tmin['year']}&month1={$tmin['mc']}&day1={$tmin['day']}&" .
            "hour1={$tmin['hour']}&min1={$tmin['min']}&" .
            "year2={$tmax['year']}&month2={$tmax['mc']}&day2={$tmax['day']}&" .
            "hour2={$tmax['hour']}&min2={$tmax['min']}";
        if ($flag_bgsub) $self_url .= "&flag_bgsub=1";
        if ($flag_highlights) $self_url .= "&flag_highlights=1";
        if ($sky_clarity_min) $self_url .= "&clarity={$sky_clarity_min}";
        $pageTemplate->showPager($result_count, $pageNum, $pageSize, $self_url);
    }

}

$pageTemplate->footer($pageInfo);

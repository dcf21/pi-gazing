<?php

// search_moving.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

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

// Read which time range to cover
$t2 = time();
$t1 = $t2 - 3600 * 24 * 5;
$tmin = $getargs->readTime('year1', 'month1', 'day1', 'hour1', 'minute1', null, $const->yearMin, $const->yearMax, $t1);
$tmax = $getargs->readTime('year2', 'month2', 'day2', 'hour2', 'minute2', null, $const->yearMin, $const->yearMax, $t2);

// Which observatory are we searching for images from?
$obstory = $getargs->readObservatory("id");

// Swap times if they are the wrong way round
if ($tmax['utc'] > $tmin['utc']) {
    $tmp = $tmax;
    $tmax = $tmin;
    $tmin = $tmp;
}

// Read duration options
$duration_min = 0;
$duration_max = 100;
$duration_min_str = $duration_max_str = "";

if (in_array("duration_min", $_GET) && is_numeric($_GET["duration_min"])) {
    $duration_min = $_GET["duration_min"];
    if ($duration_min < 0) $duration_min = 0;
    if ($duration_min > 60) $duration_min = 60;
    $duration_min_str = sprintf("%.2f", $duration_min);
}

if (in_array("duration_max", $_GET) && is_numeric($_GET["duration_max"])) {
    $duration_miax = $_GET["duration_max"];
    if ($duration_max < 0) $duration_max = 0;
    if ($duration_max > 60) $duration_max = 60;
    $duration_max_str = sprintf("%.2f", $duration_max);
}

$pageTemplate->header($pageInfo);

?>

    <form class="form-horizontal search-form" method="get" action="/search_moving.php">

        <div style="cursor:pointer;text-align:right;">
            <button type="button" class="btn btn-default btn-md help-toggle">
                <span class="glyphicon glyphicon-info-sign" aria-hidden="true"></span>
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
                        $getargs->makeFormSelect("hour1", $tmin['hour'], range(0, 23), 0);
                        print "&nbsp;<b>:</b>&nbsp;";
                        $getargs->makeFormSelect("min1", $tmin['min'], range(0, 59), 0);
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
                        $getargs->makeFormSelect("hour2", $tmax['hour'], range(0, 23), 0);
                        print "&nbsp;<b>:</b>&nbsp;";
                        $getargs->makeFormSelect("min2", $tmax['min'], range(0, 59), 0);
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
                        data-toggle="tooltip" data-pos="tooltip-right"
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
                        data-toggle="tooltip" data-pos="tooltip-right"
                        title="Search for objects visible for less than this period. Set to around 5 sec to filter out planes and satellites, which are visible for long periods."
                    >
                        <span class="formlabel2">Maximum</span>
                    <input id="maxduration"
                           class="form-control-dcf form-inline-number"
                           name="duration_max"
                           style="width:70px;"
                           type="text"
                           value="<?php echo $duration_max_str; ?>"
                    />&nbsp;seconds
                </span></div>


            </div>
        </div>

        <div style="padding:16px 0;">
            <span class="formlabel2"></span>
            <button type="submit" class="btn btn-primary" data-bind="click: performSearch">Search</button>
        </div>

    </form>

<?php
$pageTemplate->footer($pageInfo);

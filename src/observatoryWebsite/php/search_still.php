<?php

// search_still.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

require "php/imports.php";
require_once "php/html_getargs.php";

$getargs = new html_getargs(true);

$pageInfo = [
    "pageTitle" => "Search for still images",
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

// Read image options
$flag_bgsub = false;
$flag_lenscorr = false;
$flag_highlights = false;

if (in_array("flag_bgsub", $_GET)) $flag_bgsub = true;
if (in_array("flag_lenscorr", $_GET)) $flag_lenscorr = true;
if (in_array("flag_highlights", $_GET)) $flag_highlights = true;
if (in_array("defaults", $_GET)) $flag_lenscorr = $flag_highlights = true;

$pageTemplate->header($pageInfo);

?>

    <form class="form-horizontal search-form" method="get" action="/search_still.php">

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
                         title="Search for objects seen after this date and time."
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
                         title="Search for objects seen before this date and time."
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

                <div style="margin-top:25px;"><span class="formlabel">Image options</span></div>

                <div class="tooltip-holder" style="display:inline-block;">
                    <div class="checkbox" data-toggle="tooltip" data-pos="tooltip-right"
                         title="Automatically remove light pollution from images. In clear conditions, this make more stars visible. In cloudy conditions, it can lead to strange artifacts."
                    >
                        <label>
                            <input type="checkbox" name="flag_bgsub"
                                <?php if ($flag_bgsub) echo 'checked="checked"'; ?> >
                            Remove light pollution
                        </label>
                    </div>
                </div>
                <br/>
                <div class="tooltip-holder" style="padding-top:36px; display:inline-block;">
                    <div class="checkbox" data-toggle="tooltip" data-pos="tooltip-right"
                         title="Reduce the number of similar results to show a range of different images seen through the
                        night. If unticked, you will see large numbers of similar images."
                    >
                        <label>
                            <input type="checkbox" name="flag_highlights"
                                <?php if ($flag_highlights) echo 'checked="checked"'; ?> >
                            Show fewer results
                        </label>
                    </div>
                </div>
                <br/>
                <div class="tooltip-holder" style="padding-top:36px; display:inline-block;">
                    <div class="checkbox" data-toggle="tooltip" data-pos="tooltip-right"
                         title="Correct lens distortions in the images (recommended)."
                    >
                        <label>
                            <input type="checkbox" <?php if ($flag_lenscorr) echo 'checked="checked"'; ?> >
                            Correct lens distortions
                        </label>
                    </div>
                </div>

            </div>
        </div>

        <div style="padding:16px 0;">
            <span class="formlabel2"></span>
            <button type="submit" class="btn btn-primary" data-bind="click: performSearch">Search</button>
        </div>

    </form>

<?php
$pageTemplate->footer($pageInfo);

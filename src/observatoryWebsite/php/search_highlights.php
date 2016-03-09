<?php

// search_highlights.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

require "php/imports.php";
require_once "php/html_getargs.php";

$getargs = new html_getargs(true);

$pageInfo = [
    "pageTitle" => "Search for featured observations",
    "pageDescription" => "Meteor Pi",
    "activeTab" => "search",
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => []
];

// Paging options
$pageSize = 10;
$pageNum = 1;
if (array_key_exists("page", $_GET) && is_numeric($_GET["page"])) $pageNum = $_GET["page"];

// Read which time range to cover
$t2 = time();
$t1 = $t2 - 3600 * 24 * 365;
$tmin = $getargs->readTime('year1', 'month1', 'day1', 'hour1', 'minute1', null, $const->yearMin, $const->yearMax, $t1);
$tmax = $getargs->readTime('year2', 'month2', 'day2', 'hour2', 'minute2', null, $const->yearMin, $const->yearMax, $t2);

// Which observatory are we searching for images from?
$obstory = $getargs->readObservatory("obstory");

// Swap times if they are the wrong way round
if ($tmax['utc'] < $tmin['utc']) {
    $tmp = $tmax;
    $tmax = $tmin;
    $tmin = $tmp;
}


// Search for featured images
$where = "";
if ($obstory != "Any") $where = 'AND l.publicId="' . $obstory . '"';

$search = "FROM archive_files f
INNER JOIN archive_observations o ON f.observationId = o.uid
INNER JOIN archive_observatories l ON o.observatory = l.uid
INNER JOIN archive_semanticTypes so ON o.obsType = so.uid
INNER JOIN archive_metadata d ON f.uid = d.fileId
    AND d.fieldId = (SELECT uid FROM archive_metadataFields WHERE metaKey=\"web:featured\")
INNER JOIN archive_metadata d2 ON f.uid = d2.fileId
    AND d2.fieldId = (SELECT uid FROM archive_metadataFields WHERE metaKey=\"web:caption\")
WHERE (o.obsTime>{$tmin['utc']}) AND (o.obsTime<={$tmax['utc']}) {$where}";

// Count results
$stmt = $const->db->prepare("SELECT COUNT(*) {$search};");
$stmt->execute([]);
$result_count = $stmt->fetchAll()[0]['COUNT(*)'];
$result_list = [];

$lastPage = ceil($result_count / $pageSize);
if ($pageNum < 1) $pageNum = 1;
if ($pageNum > $lastPage) $pageNum = $lastPage;
$pageSkip = ($pageNum - 1) * $pageSize;

if ($result_count > 0) {

    // Fetch results
    $stmt = $const->db->prepare("
SELECT f.repositoryFname, f.fileName, l.name AS obsName, l.publicId AS locId,
o.publicId AS obsId, o.obsTime,
d2.stringValue AS caption, so.name AS obsType
{$search}
ORDER BY o.obsTime DESC LIMIT {$pageSize} OFFSET {$pageSkip};");
    $stmt->execute([]);
    $result_list = $stmt->fetchAll();
}

$paneList = [];
foreach ($result_list as $item) {
    if ($item["obsType"] == "timelapse") $link = "/image.php?id=" . $item['repositoryFname'];
    else $link = "/moving_obj.php?id=" . $item['obsId'];
    $paneList[] = ["link" => $link,
        "caption" => "<div class='smallcaps'>" .
            "<a href='observatory.php?id={$item['locId']}'>{$item['obsName']}</a>" .
            "<br />" .
            date("d M Y - H:i", $item['obsTime']) . "</div>{$item['caption']}",
        "teaser" => "api/thumbnail/" . $item['repositoryFname'] . "/" . $item['fileName']
    ];
}

$pageTemplate->header($pageInfo);

?>

    <p>
        Use this form to search for highlights from the Meteor Pi archive, as picked by our expert observers.
    </p>
    <form class="form-horizontal search-form" method="get" action="/search_highlights.php#results">

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
            </div>
        </div>

        <div style="padding:30px 0 40px 0;">
            <span class="formlabel2"></span>
            <button type="submit" class="btn btn-primary" data-bind="click: performSearch">Search</button>
        </div>

    </form>

<div id="results"></div>

<?php
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
foreach ($paneList as $item) {
    ?>
    <div class="grey_box" style="margin:16px 4px;padding:16px;">
        <div class="row">
            <div class="col-md-4" style="text-align:center;">
                <div class="gallery_image">
                    <a href="<?php echo $item['link']; ?>">
                        <img src="/<?php echo $item['teaser']; ?>" alt=""/>
                    </a>
                </div>
            </div>
            <div class="col-md-8" style="font-size:17px;">
                <?php echo $item['caption']; ?>
            </div>
        </div>
    </div>
    <?php
}

// Display pager
if (count($result_list) < $result_count) {
    $self_url = "search_highlights.php?obstory={$obstory}&" .
        "year1={$tmin['year']}&month1={$tmin['mc']}&day1={$tmin['day']}&" .
        "hour1={$tmin['hour']}&minute1={$tmin['min']}&" .
        "year2={$tmax['year']}&month2={$tmax['mc']}&day2={$tmax['day']}&" .
        "hour2={$tmax['hour']}&minute2={$tmax['min']}";
    $pageTemplate->showPager($result_count, $pageNum, $pageSize, $self_url);
}

$pageTemplate->footer($pageInfo);

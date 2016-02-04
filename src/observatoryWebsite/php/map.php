<?php

// map.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

require "php/imports.php";
require_once "php/html_getargs.php";

$getargs = new html_getargs();

// Fetch list of observatories
$obstories = $getargs->obstory_objlist;

$pageInfo = [
    "pageTitle" => "The Meteor Pi network",
    "pageDescription" => "Meteor Pi",
    "activeTab" => "cameras",
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => []
];

$pageTemplate->header($pageInfo);

?>

<div class="row camera_map" data-meta='<?php echo json_encode($obstories); ?>'>
    <div class="col-md-10">
        <div class="map_holder"
             style="width:100%; height:550px; background-color:#eee; display:inline-block; margin: 12px auto;">
            <div class="map_canvas" style="width:100%; height:100%;"></div>
        </div>
    </div>
    <div class="col-md-2">
        <?php $pageTemplate->listObstories($obstories, "/observatory.php?id="); ?>
    </div>
    </div>

<?php
$pageTemplate->footer($pageInfo);


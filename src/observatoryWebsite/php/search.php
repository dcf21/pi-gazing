<?php

// search.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

require "php/imports.php";
require_once "php/html_getargs.php";

$getargs = new html_getargs(true);

$pageInfo = [
    "pageTitle" => "Search for Meteor Pi images",
    "pageDescription" => "Meteor Pi",
    "activeTab" => "search",
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => []
];

$pageTemplate->header($pageInfo);

?>

    <p>
        Our cameras record long-exposure photographs throughout the night, as well as making videos of any moving
        objects they spot. Select what kind of observations you would like to search for.
    </p>

<?php

$pageTemplate->pageGallery([
    ["link" => "/search_moving.php",
        "title" => "Moving objects",
        "teaser" => "img/moving.png",
        "caption" => "Search for videos of moving objects detected by Meteor Pi."],
    ["link" => "/search_still.php",
        "title" => "Still images",
        "teaser" => "img/still.png",
        "caption" => "Search for images of what the sky looked like at any time in the past."],
    ["link" => "/search_multi.php",
        "title" => "Multi-camera detections",
        "teaser" => "img/multistation.png",
        "caption" => "Search for moving objects which may have been simultaneously seen by multiple cameras."],
    ["link" => "/search_highlights.php",
        "title" => "Featured observations",
        "teaser" => "img/featured.png",
        "caption" => "Search for the best images, picked by our expert observers."]
]);


$pageTemplate->footer($pageInfo);

<?php

// search.php
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
    "pageTitle" => "Search for Pi Gazing images",
    "pageDescription" => "Pi Gazing",
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
        "teaser" => "img/moving_objects.png",
        "caption" => "Search for videos of moving objects detected by Pi Gazing."],
    ["link" => "/search_still.php",
        "title" => "Still images",
        "teaser" => "img/still_images.png",
        "caption" => "Search for images of what the sky looked like at any time in the past."],
    ["link" => "/search_multi.php",
        "title" => "Multi-camera detections",
        "teaser" => "img/simultaneous.png",
        "caption" => "Search for moving objects which may have been simultaneously seen by multiple cameras."],
    ["link" => "/search_highlights.php",
        "title" => "Featured observations",
        "teaser" => "img/highlights.png",
        "caption" => "Search for the best images, picked by our expert observers."]
]);


$pageTemplate->footer($pageInfo);

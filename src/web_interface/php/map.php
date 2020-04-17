<?php

// map.php
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

$getargs = new html_getargs(false);

// Fetch list of observatories
$obstories = $getargs->obstory_objlist;

$pageInfo = [
    "pageTitle" => "The Pi Gazing network",
    "pageDescription" => "Pi Gazing",
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


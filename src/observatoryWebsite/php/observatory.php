<?php

// observatory.php
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
require_once "php/observatory_info.php";

$getargs = new html_getargs(false);

// Fetch list of observatories
$obstories = $getargs->obstory_objlist;
$obstory = $getargs->readObservatory("id");
$obstory_name = $getargs->obstory_objs[$obstory]['name'];

$obstory_info = observatory_info::obstory_info($obstory);

$pageInfo = [
    "pageTitle" => "The Meteor Pi network: {$obstory_name}",
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

<div class="row camera_map" data-meta='<?php echo json_encode([$getargs->obstory_objs[$obstory]]); ?>'>
    <div class="col-md-10">
        <div class="map_holder"
             style="width:100%; height:550px; background-color:#eee; display:inline-block; margin: 12px auto;">
            <div class="map_canvas" style="width:100%; height:100%;"></div>
        </div>
    </div>
    <div class="col-md-2">
        <h5>Latest images</h5>
        <p class="purple-text"><?php echo $obstory_info['newest_obs_date']; ?></p>
        <h5>First active</h5>
        <p class="purple-text"><?php echo $obstory_info['oldest_obs_date']; ?></p>
        <h5>Total images</h5>
        <p class="purple-text"><?php echo $obstory_info['image_count']; ?></p>
        <h5>Total moving objects</h5>
        <p class="purple-text"><?php echo $obstory_info['moving_count']; ?></p>
        <h5>More information</h5>
        <p><a href="/observatory_activity.php?id=<?php echo $obstory; ?>">Calendar of observations</a></p>
        <p><a href="/observatory_metadata.php?id=<?php echo $obstory; ?>">Status messages</a></p>
    </div>
    </div>

<?php
$pageTemplate->footer($pageInfo);


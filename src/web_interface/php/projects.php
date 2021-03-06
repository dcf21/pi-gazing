<?php

// projects.php
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

$pageInfo = [
    "pageTitle" => "Projects",
    "pageDescription" => "Pi Gazing",
    "activeTab" => "projects",
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => []
];

$pageTemplate->header($pageInfo);

?>

    <p class="text">
        Once you've tried searching for <a href="whattodo.php">planes, satellites and meteors</a> in the Pi Gazing
        <a href="search.php">data archive</a>, you'll want to know what else you can see.
        </p>
    <p class="text">
        Soon, we'll be releasing activity sheets on this page with graded difficulty levels. These will include:
    </p>

    <ul>
        <li>How many constellations can you spot?</li>
        <li>Can you find the planets?</li>
        <li>Can you spot the International Space Station?</li>
        <li>See how the stars move through the night!</li>
        <li>Spot a plane using FlightRadar24!</li>
        <li>What's the faintest object you can see?</li>
        <li>Can you spot the Moon?</li>
        <li>Why do the constellations change with season?</li>
        <li>See the planets moving!</li>
        <li>Accessing Pi Gazing data using Python</li>
    </ul>

<?php
$pageTemplate->footer($pageInfo);


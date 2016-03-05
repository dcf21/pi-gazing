<?php

// projects.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

require "php/imports.php";

$pageInfo = [
    "pageTitle" => "Projects",
    "pageDescription" => "Meteor Pi",
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
        Once you've tried searching for <a href="whattodo.php">planes, satellites and meteors</a> in the Meteor Pi
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
        <li>Accessing Meteor Pi data using Python</li>
    </ul>

<?php
$pageTemplate->footer($pageInfo);


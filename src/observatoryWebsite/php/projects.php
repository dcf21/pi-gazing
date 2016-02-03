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
        Once you've found a few <a href="/what-to-do">planes, satellites and meteors</a> spotted by Meteor Pi cameras, you'll
        want to know what else you can see. The activity sheets below guide you through some more advanced activities.
    </p>

    <ul>
        <li>Can you spot a meteor?</li>
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


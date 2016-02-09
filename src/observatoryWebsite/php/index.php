<?php

// index.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

require "php/imports.php";

$pageInfo = [
    "pageTitle" => "Meteor Pi",
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
    <div class="row">
        <div class="col-md-6" style="padding:8px;">
            <p class="text" style="font-size:18px;">Meteor Pi is a network of cameras set up by Cambridge Science Centre
                to observe the night sky.</p>

            <p class="text">They record videos of moving objects, including shooting stars, planes and satellites. They
                also take time lapse photographs through the night showing the movement of the stars.</p>

            <p class="text">All of the images are freely available on this website, and enabling children, amateur
                astronomers and coders to browse the night sky.</p>

            <p class="text">The images on this page show some of the objects we have picked up in recent weeks. Click on
                "Search the Skies" to access all the data recorded by Meteor Pi.</p>

        </div>
    </div>

<?php
$pageTemplate->footer($pageInfo);

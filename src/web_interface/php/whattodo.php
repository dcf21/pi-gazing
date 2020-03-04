<?php

// whattodo.php
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

$pageInfo = [
    "pageTitle" => "Getting started with Pi Gazing",
    "pageDescription" => "Pi Gazing",
    "activeTab" => "whattodo",
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => []
];

$pageTemplate->header($pageInfo);

?>

    <div class="pane-sequence" data-final-next='["/search.php","Search the skies"]'>
        <div class="row">
            <div class="col-md-9">
                <div style="padding:3px;">
                    <div class="grey_box" style="padding:16px;">
                        <div class="pane-item" data-title="Searching the sky">
                            <div class="rightimg">
                                <img style="width:400px;" src="img/highlights.png"/>
                            </div>

                            <p class="text">
                                On this website, you can browse the complete archive of images recorded by Pi Gazing
                                cameras.
                            </p>
                            <p class="text">
                                You can look up what the sky looked like at any of our observing locations
                                on any night. Or, you can browse all of the moving objects we've spotted.
                            </p>
                            <p class="text">
                                You can use our images to track all sorts of celestial phenomena. You can watch the
                                constellations change with the seasons, track the changing phases of the Moon, or
                                see the planets move across the sky.
                            </p>
                            <p class="text">
                                Our <a href="projects.php">projects page</a> has instructions to guide you through
                                these, and many more activities.
                            </p>
                            <p class="text">
                                To begin with, though, let's look at some of the moving objects seen by Pi Gazing.
                                We'll show you how to spot planes, shooting stars, and spacecraft like the
                                International Space Station!
                            </p>
                            <div class="pane-controls"></div>
                        </div>

                        <div class="pane-item" data-title="What can I see?">
                            <h3 style="padding-top:0;">Is it a bird... is it a plane?</h3>

                            <div class="rightimg">
                                <img style="width:400px;" src="img/example_plane_2.png"/>
                                <p class="caption">
                                    An example image of a plane, as it might appear when you search Pi Gazing images.
                                </p>
                            </div>

                            <p class="text">
                                When you <a href="search_moving.php" target="_blank">search for moving objects</a>,
                                you'll see a gallery of long-exposure photos of each object seen. Clicking on these
                                will bring up a video clip of each object.
                            </p>
                            <p class="text">
                                The moving object usually appears as a bright streak across the image, because it
                                will have moved across the image as the long exposure was being taken.
                            </p>
                            <div class="pane-controls"></div>
                        </div>

                        <div class="pane-item" data-title="Spotting aircraft">
                            <h3 style="padding-top:0;">Is it a plane?</h3>
                            <img style="width:60px;margin:5px 200px 16px 0;" src="img/mini_plane.png"/>

                            <div class="rightimg">
                                <div class="gallery_with_markers">
                                    <div data-path="[[378,360,1454532446.745],[460,351,1454532458.140],[531,343,1454532469.341]]">
                                        <img class="gallery_path_marker" alt="" title="" src="img/crosshair.gif"/>
                                        <img class="gallery_img" style="width:400px;" src="img/example_plane.png"/>
                                        <p class="caption">
                                            An example image of a plane, as it might appear when you search Pi Gazing
                                            images.
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <p class="text">
                                A blue cursor will help you to spot the moving object. The cursor will gradually move
                                back and forth along the object's path.
                            </p>
                            <p class="text">
                                Not all the videos contain real moving objects. Sometimes the cameras trigger because of
                                stars twinkling, or video glitches.
                            </p>
                            <p class="text">
                                By far the most common objects you'll see are aircraft. They're usually obvious because
                                their lights flash on and off. Because the lights flash as the aircraft moves across
                                the picture, the long exposure photograph often shows a dotted streak.
                            </p>
                            <div class="pane-controls"></div>
                        </div>

                        <div class="pane-item" data-title="Spotting meteors">
                            <h3 style="padding-top:0;">Is it a meteor?</h3>

                            <div class="rightimg">
                                <img style="width:400px;" src="img/example_meteor.png"/>
                                <p class="caption">
                                    An example image of a meteor, as it might appear when you search Pi Gazing
                                    images.
                                </p>
                            </div>

                            <p class="text">
                                Shooting stars are distinctive, because they move much quicker than planes and
                                satellites. They usually come and go within a fraction of a second, as they burn up in
                                the Earth's atmosphere.
                            </p>
                            <p class="text">
                                Within the search interface for finding moving objects, you can set limits on how long
                                the object was visible was for. Try reducing the maximum duration to one second &ndash;
                                you'll only see objects that were gone within a second of first appearing.
                            </p>
                            <div style="text-align:center;padding:20px;">
                                <div class="gallery_image">
                                    <img src="img/duration_satellite.png" style="width:200px;"/>
                                </div>
                            </div>
                            <p class="text">
                                Look for objects that moved a significant distance within that short space of time, and
                                you're very likely to find a few shooting stars.
                            </p>
                            <p class="text">
                                Shooting stars are only visible in clear weather, as they burn up high in the
                                atmosphere, far above the clouds. On clear starry nights, we often see two or three each
                                night.
                            </p>
                            <div class="pane-controls"></div>
                        </div>

                        <div class="pane-item" data-title="Spotting satellites (1)">
                            <h3 style="padding-top:0;">Is it satellite?</h3>
                            <img style="width:60px;margin:5px 200px 16px 0;" src="img/mini_satellite.png"/>

                            <div class="rightimg position_relative">
                                <img style="width:400px;" src="img/example_satellite.png"/>
                                <p class="caption">
                                    An example image of a satellite, as it might appear when you search Pi Gazing
                                    images.
                                </p>
                            </div>

                            <p class="text">
                                Satellites are often visible soon after sunset, and shortly before sunrise. A few of the
                                brightest,
                                such as the International Space Station and Chinese Tiangong space station can appear
                                even brighter
                                than the brightest star.
                            </p>
                            <p class="text">
                                Like planes, they are visible for much longer than meteors. They usually take a minute
                                or more to cross the sky.
                                They move at a steady speed, and unlike planes, don't have flashing lights.
                            </p>
                            <p class="text">
                                The flight paths of satellites are extremely predictable, and websites like
                                <a href="https://in-the-sky.org/satpasses.php">In-The-Sky.org</a> list the times when
                                bright satellites are due to fly over.
                            </p>
                            <p class="text">
                                Not all of these will be seen by Pi Gazing, since
                                our cameras can only see half the sky, and satellites are only visible in clear
                                conditions.
                            </p>

                            <div class="pane-controls"></div>
                        </div>

                        <div class="pane-item" data-title="Spotting satellites (2)">
                            <h3 style="padding-top:0;">Is it satellite?</h3>

                            <p class="text">
                                To search for videos of satellites, try restricting your search to objects that were
                                visible for ten seconds or more. You can do this using the same duration control that
                                you used to search for short-lasting shooting stars.
                            </p>
                            <div style="text-align:center;padding:20px;">
                                <div class="gallery_image">
                                    <img src="img/duration_plane.png" style="width:200px;"/>
                                </div>
                            </div>
                            <p class="text">
                                Most of the objects you'll see are planes, with flashing lights, but a few may appear
                                with a steady brightness. These are likely to be satellites.
                            </p>
                            <p class="text">
                                To be sure, try checking against the predictions on
                                <a href="https://in-the-sky.org/satpasses.php">In-The-Sky.org</a>.
                            </p>
                            <p class="text">
                                Some satellites, however, aren't listed on the web. These include spy satellites that
                                don't officially exist!
                            </p>

                            <div class="pane-controls"></div>
                        </div>

                        <div class="pane-item" data-title="Next steps">
                            <h3 style="padding-top:0;">What next?</h3>
                            <p class="text">
                                To start searching for images taken by Pi Gazing, our <a href="search.php">online
                                    search interface</a> is the easiest place to start.
                            </p>
                            <p class="text">
                                Once you've started looking through our images,
                                <a href="projects.php">our projects page</a> will give you some ideas for other
                                things to look our for in the night sky.
                            </p>
                            <div class="pane-controls-final"></div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div style="padding:3px;">
                    <div class="grey_box" style="padding:16px;">
                        <h4 style="padding-top:0;">Contents</h4>
                        <div class="pane-list"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

<?php
$pageTemplate->footer($pageInfo);

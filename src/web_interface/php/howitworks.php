<?php

// howitworks.php
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
    "pageTitle" => "How Pi Gazing Works",
    "pageDescription" => "Pi Gazing",
    "activeTab" => "howitworks",
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
                        <div class="pane-item" data-title="What our cameras look like">
                            <div class="rightimg">
                                <img src="img/IMG_20150316_160453.jpg"/>
                                <p class="caption">
                                    Pi Gazing cameras are similar to CCTV cameras, but they point upwards at the sky!
                                </p>
                            </div>

                            <p class="text">
                                Each of our Pi Gazing observatories looks very much like a CCTV camera you might see
                                in the street. The most obvious difference, though, is that ours point upwards at the
                                sky.
                            </p>
                            <p class="text">
                                Inside the box, some of the electronics is also similar to what you might see in a
                                CCTV camera. At the front of the box, we have a Watec 902H2 Ultimate &ndash; a Japanese
                                model of CCTV camera, which is designed to work in incredibly dark places.
                            </p>
                            <p class="text">
                                These cameras are normally used to look at dark alleyways, but they're useful to us
                                because they only need only look at the sky for a few seconds to detect stars hundreds
                                of times fainter than the human eye can see.
                            </p>
                            <div class="pane-controls"></div>
                        </div>

                        <div class="pane-item" data-title="Inside the box">
                            <h3 style="padding-top:0;">Inside the box</h3>


                            <div class="rightimg">
                                <img src="img/IMG_20150805_142114.jpg"/>
                                <p class="caption">
                                    The electronics in a Pi Gazing observatory. A Raspberry Pi Mk 2 analyses the pictures
                                    to look for moving objects.
                                </p>
                            </div>
                            <p class="text">
                                What makes our observatories very different from CCTV cameras is the electronics that
                                analyses the video signal.
                            </p>
                            <p class="text">
                                We have a Raspberry Pi 2 Model B computer, which receives the pictures from the video
                                camera and analyses them. It takes long-exposure still photographs every 30 seconds
                                through the night, and also monitors the video feed to look for moving objects.
                            </p>
                            <p class="text">
                                The system is designed to be entirely autonomous. Once a camera has been set up, we can
                                leave it for long periods without doing any maintenance. Each set up uses a
                                GPS receiver record its exact location, and also to know exactly what the time is. It
                                can calculate the time of local sunrise and sunset to know when it should begin
                                observing each night.
                            </p>
                            <div class="pane-controls"></div>
                        </div>

                        <div class="pane-item" data-title="A network of cameras">
                            <h3 style="padding-top:0;">The Pi Gazing network</h3>

                            <div class="rightimg">
                                <img src="img/simultaneous.png"/>
                                <p class="caption">
                                    By observing from many different locations, we hope eventually to be able to
                                    triangulate the 3D positions of objects.
                                </p>
                            </div>
                            <p class="text">
                                Our cameras are spread across a number of locations in the east of England, and we
                                hope to spread them over a wider area soon.
                            </p>
                            <p class="text">
                                Having many cameras in different locations helps us for several reasons. On average,
                                the weather in any particular location in the UK is only clear on one night in three.
                                However, by having cameras in different places we have a higher chance of finding
                                somewhere where it is clear.
                            </p>
                            <p class="text">
                                Different locations are affected by light pollution to differing degrees. The view of
                                the night sky from a city can be very different from the view in the countryside,
                                where many fainter stars will be visible.
                            </p>
                            <p class="text">
                                Eventually, we hope to use simultaneous detections of moving objects from different
                                locations to triangulate their altitudes and speeds.
                            </p>
                            <div class="pane-controls"></div>
                        </div>

                        <div class="pane-item" data-title="The Pi Gazing website">
                            <h3 style="padding-top:0;">The Pi Gazing website</h3>

                            <p class="text">
                                All of our cameras are programmed to automatically transmit all their observations
                                to a central archive each day.
                            </p>
                            <p class="text">
                                This usually happens around lunchtime, and the observations become accessible via this
                                website shortly afterwards.
                            </p>
                            <p class="text">
                                If you search our website very early in the morning, you may find that the previous
                                night's images haven't appeared yet, but they should arrive soon!
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


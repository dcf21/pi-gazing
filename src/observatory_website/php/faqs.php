<?php

// faqs.php
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

$pageInfo = [
    "pageTitle" => "Frequently asked questions",
    "pageDescription" => "Meteor Pi",
    "activeTab" => "faqs",
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => []
];

$pageTemplate->header($pageInfo);

?>
    <div class="faqs">
        <div class="faq_item">
            <div class="faq_question">
                <a data-toggle="collapse" href="#collapse1">
                    What are shooting stars?
                </a>
            </div>
            <div class="faq_answer panel-collapse collapse" id="collapse1">

                <div class="rightimg">
                    <img src="img/Meteor_trail_over_Chelyabinsk.jpg" style="max-width:450px;"/>
                    <p class="caption">
                        The meteor which burnt up over Chelyabinsk, Russia, on 15 February 2013 was so large that it
                        left a long-lasting trail of smoke in its wake. Most meteors completely vanish within a
                        fraction of a second.
                    </p>
                </div>

                <p class="text">
                    Shooting stars appear when pebble-sized lumps of space rock crash into the Earth. Because they are
                    travelling so fast, they burn up when they hit our planet’s atmosphere, leaving a fiery trail
                    across the sky.
                </p>
                <p class="text">
                    Millions of shooting stars appear around the world every day. The Solar System is teeming with rocky
                    fragments of material which never stuck together to form planets, and astronomers estimate that
                    over 100 tonnes of this material collides with the Earth every day.
                </p>
                <p class="text">
                    Thankfully, the vast majority of it burns up at an altitude of over 50 miles, posing no hazard to
                    anyone on the ground.
                </p>
                <p class="text">
                    By recording videos of these rocks burning up, we can count how many of them there are. By comparing
                    videos seen from multiple locations in East Anglia, we can triangulate the exact altitude and
                    trajectory of each shooting star, telling us where each one came from.
                </p>
                <p class="text">
                    Eventually, Meteor Pi will allow us to trace out how space rocks are distributed through the Solar
                    System.
                </p>
            </div>
        </div>

        <div class="faq_item">
            <div class="faq_question">
                <a data-toggle="collapse" href="#collapse2">
                    Why are many Meteor Pi images blank?
                </a>
            </div>
            <div class="faq_answer panel-collapse collapse" id="collapse2">

                <div class="rightimg">
                    <img src="img/cloudyskies.png"/>
                    <p class="caption">
                        Meteor Pi cameras observe on cloudy skies as well as starry ones. Sometimes the Moon or
                        twilight can dazzle them!
                    </p>
                </div>

                <p class="text">
                    Our cameras observe from nightfall until dawn every day, even when the weather is bad.
                </p>
                <p class="text">
                    In the UK, most places have clear skies on one night in three, so roughly two thirds of Meteor Pi
                    images show cloudy skies.
                </p>
                <p class="text">
                    Around twilight, the images often appear completely white. This is because we use very sensitive
                    cameras that are designed to see faint stars on dark nights. When the sun comes up, they're often
                    completely overwhelmed by the amount of light they see!
                </p>
            </div>
        </div>

        <div class="faq_item">
            <div class="faq_question">
                <a data-toggle="collapse" href="#collapse3">
                    Can I build my own Meteor Pi camera?
                </a>
            </div>
            <div class="faq_answer panel-collapse collapse" id="collapse3">

                <div class="rightimg">
                    <img src="img/system_diagram.png" style="max-width:450px;"/>
                    <p class="caption">
                        The collection of hardware found inside a Meteor Pi camera.
                    </p>
                </div>

                <p class="text">
                    Yes! We are very keen for amateur astronomers and others to get involved.
                </p>

                <p class="text">
                    All the hardware designs and software used by the Meteor Pi cameras are open source, and can be
                    found on our
                    <a href="https://github.com/camsci/meteor-pi">GitHub pages</a>.
                    Not only are they free to download, but you're also welcome to change them and see if you can make
                    them work better!
                </p>

                <p class="text">
                    The cost of building a camera is around &pound;300&ndash;&pound;400, depending on optional extras.
                    You can find a complete guide to how to build your own camera on our
                    <a href="https://github.com/camsci/meteor-pi">GitHub pages</a>.
                </p>

                <p class="text">
                    If you'd like to get involved, why not get in touch with us via
                    <a href="https://www.facebook.com/meteorpicamera/">Facebook</a>
                    or <a href="https://twitter.com/meteorpi">Twitter</a>?
                </p>
            </div>
        </div>


        <div class="faq_item">
            <div class="faq_question">
                <a data-toggle="collapse" href="#collapse4">
                    Why are the pictures black and white?
                </a>
            </div>
            <div class="faq_answer panel-collapse collapse" id="collapse4">

                <div class="rightimg">
                    <img src="img/IMG_20150624_172144.jpg"/>
                    <p class="caption">
                        We use the most sensitive security cameras we could find, with large lenses on the front to catch
                        as much light as possible.
                    </p>
                </div>

                <p class="text">
                    When we designed the Meteor Pi cameras, our priority was make them as sensitive as possible to very
                    faint objects in the night sky.
                </p>
                <p class="text">
                    Colour cameras are much less sensitive than black-and-white ones. They have an array of
                    light-sensitive elements inside them, each of which sits behind filter which makes it sensitive to
                    only one colour. Any green light which falls on a red pixel, for example, isn't detected.
                </p>
                <p class="text">
                    Black-and-white cameras have at least twice the sensitivity of color cameras, because they don't
                    have any filters inside.
                </p>
                <p class="text">
                    So, although this makes the pictures slightly less pretty, it means we can see stars that would be
                    invisible to a colour camera.
                </p>
            </div>
        </div>
    </div>

<?php
$pageTemplate->footer($pageInfo);


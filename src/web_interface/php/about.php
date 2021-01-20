<?php

// about.php
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
    "pageTitle" => "About Pi Gazing",
    "pageDescription" => "Pi Gazing",
    "activeTab" => "about",
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => []
];

$pageTemplate->header($pageInfo);

?>

<div class="rightimg">
    <img src="/img/IMG_20200204_130609.jpg" /><br />
    <b>A Pi Gazing camera.</b>
</div>


<p class="text">
    Pi Gazing is a project to build meteor cameras using Raspberry Pi computers
    connected to CCTV cameras which are directed upwards to record the night sky.
</p>

<p class="text">
    The Raspberry Pi computer analyses the video feed in real time to search for
    moving objects, recording the tracks of shooting stars, as well as satellites
    and aircraft. We also see rarer phenomena: lightning strikes, fireworks, and
    Iridian flares, caused by glints of light from solar panels on spacecraft.
</p>

<p class="text">
    Whenever a moving object is detected, the Raspberry Pi stores a video of the
    object's path across the sky. Using a software package called <i>astrometry.net</i>,
    the camera is able to automatically detect patterns of stars and calculate the
    direction in which the camera is pointing, allowing the object's celestial
    coordinates to be determined.
</p>

<p class="text">
    Each time the camera identifies a moving object, it compares the observation
    with the records of other nearby cameras in the Pi Gazing network, to see if
    the same object was seen from multiple locations. If so, the software compares
    the position of the object in the sky as observed from the two locations, in
    order to triangulate its altitude and speed. For shooting stars and satellites,
    it is then possible to estimate the object's orbital elements.
</p>

<p class="text">
    The cameras also take a series of long-exposure still photos each night. These
    are used by the software to determine the direction the camera is pointing in,
    as well as to calibrate any distortions which may be present in the lens used
    (for example, barrel distortion).
</p>

<p class="text">
    These still images also allow you to watch how the constellations circle
    overhead as the night progresses, or how they change with the seasons. You can
    see the changing phases of the Moon, or watch the planets move across the sky.
</p>

<p class="text">
    On this website, you can browse the entire archive of observations recorded by
    our cameras.
</p>

<h3>Developers</h3>

<p class="text">
	 Pi Gazing is being developed by astronomer
    <a href="https://dcford.org.uk/">Dominic Ford</a>.
    The hardware design for our meteor cameras was developed by Dave Ansell at
    <a href="https://www.sciansell.co.uk">SciAnsell</a>, while the software was
    developed by Dominic himself.
</p>
<p class="text">
    All of the software and hardware designs are open source and can be downloaded
    from our <a href="https://github.com/dcf21/pi-gazing">GitHub pages</a> under a
    <a href="http://www.gnu.org/licenses/gpl-3.0.en.html">Gnu General Public License V3</a>.
</p>

<h3>Acknowledgments</h3>

<p class="text">

We are very grateful for advice from many amateur astronomers who helped us
with the design of Pi Gazing. These include the <a
href="http://www.nemetode.org/">NEMETODE</a> and <a
href="https://www.ukmeteornetwork.co.uk/">UKMON</a> networks of amateur meteor
observers.

</p>
<p class="text">

Pi Gazing is based on code which was developed for Cambridge Science Centre's
MeteorPi project, which was created by Dominic Ford with generous support from
the Raspberry Pi Foundation and Mathworks.

</p>

<?php
$pageTemplate->footer($pageInfo);

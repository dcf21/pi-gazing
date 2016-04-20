<?php

// about.php
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
    "pageTitle" => "About Meteor Pi",
    "pageDescription" => "Meteor Pi",
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
    <img src="/img/IMG_20150910_193401.jpg" /><br />
    <b>Three Meteor Pi cameras being tested side-by-side.</b>
</div>

<p class="text">
    Meteor Pi was developed by astronomer <a href="https://in-the-sky.org/about.php">Dominic Ford</a> for
    Cambridge Science Centre.
    </p>
<p class="text">
    All of the software and hardware designs are open source, and can be downloaded from
    our <a href="https://github.com/camsci/meteor-pi">GitHub pages</a> under a
    <a href="http://www.gnu.org/licenses/gpl-3.0.en.html">Gnu General Public License V3</a>.
</p>
<p class="text">
    You are very welcome to try building your own Meteor Pi camera. You can either use our software as is, or you can
    play around with it, figure out how it works, and try to make it work better!
</p>
<p class="text">
    If you do build your own camera, please do get in touch with us via Facebook or Twitter. We'd love to keep track
    of where Meteor Pi cameras are being installed.
</p>

<h3>Acknowledgments</h3>

<p class="text">
We are very grateful for advice from many amateur astronomers who helped us with the design of Meteor Pi. These include
the <a href="http://www.nemetode.org/">NEMETODE</a> and <a href="https://www.ukmeteornetwork.co.uk/">UKMON</a>
networks of amateur meteor observers.
</p>
<p class="text">
    The hardware used in our MeteorPi cameras was designed by Dave Ansell at Cambridge Science Centre. Our database
    and communications systems were design by Tom Oinn.
</p>

<h3>Supporters</h3>

<p>The development of Meteor Pi was made possible thanks to generous funding from:</p>

<div class="row supporters">
    <div class="col-sm-6">
        <img src="img/rpi_logo.png" alt="The Raspberry Pi Foundation"
             title="The Raspberry Pi Foundation"/>
        <br />
        The Raspberry Pi Foundation
    </div>
    <div class="col-sm-6">
        <img src="img/Mathworks.jpg" alt="MathWorks" title="MathWorks"/>
        <br />
        MathWorks
    </div>
</div>

<?php
$pageTemplate->footer($pageInfo);

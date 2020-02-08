<?php

// about.php
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2019 Dominic Ford.

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
    Pi Gazing is run by astronomer <a href="https://dcford.org.uk/">Dominic Ford</a>. The hardware design for our
    meteor cameras was developed by Dave Ansell at <a href="https://www.sciansell.co.uk">SciAnsell</a>, while the
    software was developed by Dominic himself.
    </p>
<p class="text">
    All of the software and hardware designs are open source and can be downloaded from
    our <a href="https://github.com/dcf21/pi-gazing">GitHub pages</a> under a
    <a href="http://www.gnu.org/licenses/gpl-3.0.en.html">Gnu General Public License V3</a>.
</p>
<p class="text">
    You are very welcome to try building your own Pi Gazing camera. You can either use our software as is, or you can
    play around with it, figure out how it works, and try to make it work better!
</p>

<h3>Acknowledgments</h3>

<p class="text">
We are very grateful for advice from many amateur astronomers who helped us with the design of Pi Gazing. These include
the <a href="http://www.nemetode.org/">NEMETODE</a> and <a href="https://www.ukmeteornetwork.co.uk/">UKMON</a>
networks of amateur meteor observers.
</p>

<p class="text">

    Pi Gazing is based on code which was developed for Cambridge Science Centre's MeteorPi project, which was
    created by Dominic Ford with generous support from the Raspberry Pi Foundation and Mathworks.

</p>

<?php
$pageTemplate->footer($pageInfo);

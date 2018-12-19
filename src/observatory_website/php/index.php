<?php

// index.php
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

// Search for featured images
$stmt = $const->db->prepare("
SELECT f.repositoryFname, f.fileName, l.name AS obsName, l.publicId AS locId,
o.publicId AS obsId, o.obsTime,
d2.stringValue AS caption, so.name AS obsType
FROM archive_files f
INNER JOIN archive_observations o ON f.observationId = o.uid
INNER JOIN archive_observatories l ON o.observatory = l.uid
INNER JOIN archive_semanticTypes so ON o.obsType = so.uid
INNER JOIN archive_metadata d ON f.uid = d.fileId AND d.fieldId = (SELECT uid FROM archive_metadataFields WHERE metaKey=\"web:featured\")
INNER JOIN archive_metadata d2 ON f.uid = d2.fileId AND d2.fieldId = (SELECT uid FROM archive_metadataFields WHERE metaKey=\"web:caption\")
ORDER BY o.obsTime DESC LIMIT 6;");
$stmt->execute([]);
$result_list = $stmt->fetchAll();

$paneList = [];
foreach ($result_list as $item) {
    if ($item["obsType"] == "timelapse") $link = "/image.php?id=" . $item['repositoryFname'];
    else $link = "/moving_obj.php?id=" . $item['obsId'];
    $paneList[] = ["link" => $link,
        "caption" => "<div class='smallcaps'>" .
            "<a href='observatory.php?id={$item['locId']}'>{$item['obsName']}</a>" .
            "<br />" .
            date("d M Y - H:i", $item['obsTime']) . "</div>{$item['caption']}",
        "teaser" => "api/files/content/" . $item['repositoryFname'] . "/" . $item['fileName']
    ];
}

$pageInfo = [
    "pageTitle" => "Pi Gazing",
    "pageDescription" => "Pi Gazing",
    "noTitle" => true,
    "activeTab" => "home",
    "breadcrumb" => null,
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => []
];

$pageTemplate->header($pageInfo);

?>
    <div class="row">
        <div class="col-md-4" style="padding:16px;">
            <p class="text" style="font-size:18px;">
                Pi Gazing lets you browse the night sky without having to step outside or wait until nightfall.
            </p>

            <p class="text">
                We've set up a network of cameras which take pictures of the night sky from dusk till dawn every day.
            </p>

            <p class="text">
                As the night progresses they record the constellations circling overhead.
            </p>

            <p class="text">
                They're also motion sensitive. Whenever anything flies past, they record a video. They capture footage
                of planes, satellites, and shooting stars. We also see rarer phenomena: lightning strikes,
                fireworks, and glints of light from solar panels on spacecraft.
            </p>

            <p class="text">
                Nothing beats the experience of looking at the night sky for yourself with a pair of binoculars, but
                Pi Gazing will help you learn what to look out for. And because our motion-sensitive cameras are keeping
                constant watch, you may see rare events that you would have to wait a long time to see for yourself.
            </p>

            <div style="padding:10px 20px;text-align:right;">
                <button type="button" class="btn btn-primary btn-sm" onclick="window.location='/whattodo.php';">
                    What to do &#187;
                </button>
            </div>

        </div>
        <div class="col-md-8" style="padding:8px;">
            <div class="grey_box" style="padding: 8px;">
                <p class="purple-heading">Recent observations</p>
                <?php $pageTemplate->slidingPanes($paneList); ?>
                <div style="text-align: right; padding:12px">
                    <a href="/search_highlights.php">
                        See more highlights&nbsp;&#187;
                    </a>
                </div>
            </div>
        </div>
    </div>

<?php
$pageTemplate->footer($pageInfo);

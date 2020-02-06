<?php

// observatory_metadata.php
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

require_once "php/imports.php";
require_once "php/html_getargs.php";

$getargs = new html_getargs(false);

$obstories = $getargs->obstory_objlist;
$obstory = $getargs->readObservatory("id");
$obstory_name = $getargs->obstory_objs[$obstory]['name'];

// Fetch observatory metadata
$stmt = $const->db->prepare("
SELECT m.time, mf.metaKey, m.floatValue, m.stringValue FROM archive_metadata m
INNER JOIN archive_metadataFields mf ON m.fieldId = mf.uid
WHERE m.observatory=(SELECT uid FROM archive_observatories WHERE publicId=:o)
ORDER BY m.time DESC;");
$stmt->bindParam(':o', $o, PDO::PARAM_STR, strlen($obstory));
$stmt->execute(['o' => $obstory]);
$metadata = $stmt->fetchAll();

$pageInfo = [
    "pageTitle" => "Observatory {$obstory_name}: Status information",
    "pageDescription" => "Pi Gazing",
    "activeTab" => "cameras",
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => [],
    "breadcrumb" => [["observatory.php?id=" . $obstory, $obstory_name]]
];


$pageTemplate->header($pageInfo);

?>
<div class="row">
    <div class="col-md-10">

        <p class="centred">
            The table below lists various status information reported by the observatory in the course of its
            observations.
        </p>
        <p class="centred">
            Most nights, each observatory returns a new estimate of its location, based on GPS. Other information,
            such as the model of camera and lens installed are reported less frequently.
        </p>
        <p class="centred">
            Items shown in green are still current. Items shown in red have been superseded by newer updates.
        </p>

        <table class="metadata" style="margin:8px auto;">
            <thead>
            <tr>
                <td>Date</td>
                <td>Setting</td>
                <td>Value</td>
            </tr>
            </thead>
            <?php
            $seenKeys = [];
            foreach ($metadata as $item):
                $key = $item['metaKey'];
                if (array_key_exists($key, $const->metadataFields)) $key = $const->metadataFields[$key];
                $value = $item['stringValue'] ? $item['stringValue'] : sprintf("%.2f", $item['floatValue']);
                $superseded = in_array($key, $seenKeys);
                if (!$superseded) $seenKeys[] = $key;

                if ($item['metaKey'] == "refresh"):
                ?>
                <tr>
                    <td colspan="3" style="text-align:center; font-style: italic;">
                        &ndash;
                        Observatory serviced <?php echo date("d M Y - H:i", $item['time']); ?>
                        &ndash;
                    </td>
                </tr>
                <?php else: ?>
                <tr class="<?php echo $superseded ? 'superseded' : 'active'; ?>">
                    <td>
                        <?php
                        if ($item['time'] > 0)
                            echo date("d M Y - H:i", $item['time']);
                        else
                            echo "&ndash;";
                        ?>
                    </td>
                    <td style="vertical-align:top;white-space:nowrap;" title="<?php echo $item['metaKey']; ?>">
                        <?php echo $key; ?>
                    </td>
                    <td><?php echo $value; ?></td>
                </tr>
                <?php endif; ?>
            <?php endforeach; ?>
        </table>
    </div>

    <div class="col-md-2">
        <?php $pageTemplate->listObstories($obstories, "/observatory_metadata.php?id="); ?>
    </div>
</div>

<?php
$pageTemplate->footer($pageInfo);


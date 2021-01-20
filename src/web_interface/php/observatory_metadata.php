<?php

// observatory_metadata.php
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

require_once "php/imports.php";
require_once "php/html_getargs.php";

$getargs = new html_getargs(false);

// Which observatory are we searching for metadata from?
$obstories = $getargs->obstory_objlist;
$obstory = $getargs->readObservatory("id");
$obstory_name = $getargs->obstory_objs[$obstory]['name'];

// Which metadata field are we displaying?
$field_options = [["0", "Show all"]];
foreach($const->metadataFields as $field_key => $field_name) {
    $field_options[] = [$field_key, $field_name];
}
$metadata_field = $getargs->readMetadataField("field");

// Make SQL search constraint
if ($metadata_field == "0") {
    $search = "AND (mf.metaKey=:k OR 1)";
} else {
    $search = "AND mf.metaKey=:k";
}

// Fetch observatory metadata
$stmt = $const->db->prepare("
SELECT m.time, mf.metaKey, m.floatValue, m.stringValue FROM archive_metadata m
INNER JOIN archive_metadataFields mf ON m.fieldId = mf.uid
WHERE m.observatory=(SELECT uid FROM archive_observatories WHERE publicId=:o)
      ${search}
ORDER BY m.time DESC;");
$stmt->bindParam(':o', $o, PDO::PARAM_STR, strlen($obstory));
$stmt->bindParam(':k', $k, PDO::PARAM_STR, strlen($metadata_field));
$stmt->execute(['o' => $obstory, 'k' => $metadata_field]);
$metadata = $stmt->fetchAll();

// Limit the width of drop-down menus
$cssextra = <<<__HTML__
<style media="screen" type="text/css">
select { max-width: 250px; }
</style>
__HTML__;

$pageInfo = [
    "pageTitle" => "Observatory {$obstory_name}: Status information",
    "pageDescription" => "Pi Gazing",
    "activeTab" => "cameras",
    "teaserImg" => null,
    "cssextra" => $cssextra,
    "includes" => [],
    "linkRSS" => null,
    "options" => [],
    "breadcrumb" => [["observatory.php?id=" . $obstory, $obstory_name]]
];


$pageTemplate->header($pageInfo);

?>

    <form class="form-horizontal search-form" method="get" action="observatory_metadata.php">

        <div style="cursor:pointer;text-align:right;">
            <button type="button" class="btn btn-secondary help-toggle">
                <i class="fa fa-info-circle" aria-hidden="true"></i>
                Show tips
            </button>
        </div>
        <div class="row">
            <div class="search-form-column col-lg-5">
                <div style="margin-top:25px;"><span class="formlabel">Observatory</span></div>
                <div class="tooltip-holder">
                    <div class="form-group-dcf"
                         data-toggle="tooltip" data-pos="tooltip-below"
                         title="Use this to display metadata from only one camera in the Pi Gazing network. Set to 'Any' to display images from all Pi Gazing cameras."
                    >
                        <?php
                        $getargs->makeFormSelect("id", $obstory, $getargs->obstories, 1);
                        ?>
                    </div>
                </div>
            </div>
            <div class="search-form-column col-lg-5">
                <div style="margin-top:25px;"><span class="formlabel">Metadata field</span></div>
                <div class="tooltip-holder">
                    <div class="form-group-dcf"
                         data-toggle="tooltip" data-pos="tooltip-below"
                         title="Use this to display only one particular metadata field. Set to 'Show all' to show all metadata fields."
                    >
                        <?php
                        $getargs->makeFormSelect("field", $metadata_field, $field_options, 1);
                        ?>
                    </div>
                </div>

            </div>
            <div class="search-form-column col-lg-2">
                <div style="padding:40px 0 0 0;">
                    <button type="submit" class="btn btn-primary" data-bind="click: performSearch">Search</button>
                </div>
            </div>
        </div>

    </form>

    <hr style="margin: 20px 0;"/>

<?php

if (($metadata_field !== "0") && (count($metadata) > 1) && (!$metadata[0]['stringValue'])):
            $key = $metadata[0]['metaKey'];
            if (array_key_exists($key, $const->metadataFields)) {
                $key = $const->metadataFields[$key];
            }
        $graph_data = [];

        foreach ($metadata as $result) {
            $graph_data[] = [$result['time'], floor($result['floatValue'] * 100) / 100];
        };

        $graph_metadata = [
            'y-axis' => $key,
            'data' => [$graph_data],
            'data_set_titles' => [$obstory_name]
        ];

        ?>

        <div class="chart_holder" data-meta='<?php echo json_encode($graph_metadata); ?>'>
            <div class="chart_div"></div>
        </div>

<?php endif; ?>

    <p class="centred">
        The table below lists status information reported by each observatory.
    </p>
    <p class="centred">
        Some information, such as the direction the camera is pointing in, is often updated on a nightly
        basis. Other information, such as the model of camera and lens installed are generally only
        updated whenever a camera is serviced.
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
                    <td style="vertical-align:top;white-space:nowrap;">
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
                    <td style="max-width: 350px;">
                        <?php echo $value; ?>
                    </td>
                </tr>
            <?php endif; ?>
        <?php endforeach; ?>
    </table>

<?php
$pageTemplate->footer($pageInfo);


<?php

// moving_obj.php
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
require_once "php/html_getargs.php";
require_once "php/set_metadata.php";

$getargs = new html_getargs(true);

// Get ID for event to display
$id = "";
if (array_key_exists("id", $_GET)) $id = $_GET["id"];

// Get the observation
$stmt = $const->db->prepare("
SELECT o.uid, o.observatory, o.obsTime, s.name AS semanticType
FROM archive_observations o
INNER JOIN archive_semanticTypes s ON o.obsType = s.uid
WHERE publicId=:i;");
$stmt->bindParam(':i', $i, PDO::PARAM_INT);
$stmt->execute(['i' => $id]);
$observations = $stmt->fetchAll();

// Check observation exists
if (count($observations) != 1) die ("Requested file does not have associated observation.");
$observation = $observations[0];
$uid = $observation['uid'];

// Get observatory information
$stmt = $const->db->prepare("SELECT * FROM archive_observatories WHERE uid=:i;");
$stmt->bindParam(':i', $i, PDO::PARAM_INT);
$stmt->execute(['i' => $observation['observatory']]);
$obstory = $stmt->fetch();

// Does user have permission to set metadata on this item?
$allow_item_to_be_featured = in_array("voter", $user->roles);

// Find previous and next images of the same type, from the same observatory
$related = [];

foreach ([["prev", "<", "DESC"], ["next", ">", "ASC"]] as $sort) {
    $stmt = $const->db->prepare("
SELECT o.publicId AS uid
FROM archive_observations o
INNER JOIN archive_semanticTypes s ON o.obsType = s.uid
WHERE s.name=:s AND o.observatory=:o AND o.obsTime {$sort[1]} :t
ORDER BY o.obsTime {$sort[2]} LIMIT 1;");
    $stmt->bindParam(':s', $s, PDO::PARAM_STR, strlen($observation['semanticType']));
    $stmt->bindParam(':t', $t, PDO::PARAM_STR, 32);
    $stmt->bindParam(':o', $o, PDO::PARAM_INT);
    $stmt->execute([
            'o' => $observation['observatory'],
        't' => $observation['obsTime'],
        's' => $observation['semanticType']
    ]);
    $related[$sort[0]] = $stmt->fetchAll();
}

// Set categorisation of image based on get data
if ($allow_item_to_be_featured && array_key_exists("update", $_GET)) {
    if (array_key_exists("category", $_GET)) {
        $new_category = $_GET["category"];
        if ($new_category == "Not set") $new_category = null;
        set_metadata("web:category", $new_category, $observation['obsTime'], $uid, "observationId");
    }
}

// Get list of metadata
$stmt = $const->db->prepare("
SELECT m.time, mf.metaKey, m.floatValue, m.stringValue
FROM archive_metadata m
INNER JOIN archive_metadataFields mf ON m.fieldId = mf.uid
WHERE observationId=:i;");
$stmt->bindParam(':i', $i, PDO::PARAM_INT);
$stmt->execute(['i' => $uid]);
$metadata = $stmt->fetchAll();

// Make metadata dictionary
$metadata_by_key = [];
foreach ($metadata as $item) {
    $metadata_by_key[$item['metaKey']] = $item['stringValue'] ? $item['stringValue'] : $item['floatValue'];
}

// Get list of associated files
$stmt = $const->db->prepare("
SELECT f.repositoryFname, f.fileName, o.obsTime, l.publicId AS obstoryId, sf.name AS obstoryName,
f.mimeType AS mimeType,sf.name AS semanticType
FROM archive_files f
INNER JOIN archive_observations o ON f.observationId = o.uid
INNER JOIN archive_observatories l ON o.observatory = l.uid
INNER JOIN archive_semanticTypes sf ON f.semanticType = sf.uid
WHERE observationId=:i;");
$stmt->bindParam(':i', $i, PDO::PARAM_INT);
$stmt->execute(['i' => $uid]);
$file_list = $stmt->fetchAll();

// Build dictionary of files by semantic type
$files_by_type = [];
foreach ($file_list as $item) {
    $item_type = $item['semanticType'];
    $files_by_type[$item_type] = $item;
}

// Get list of simultaneous detections
$stmt = $const->db->prepare("
SELECT m.childObservation, l.name AS obstory, f.repositoryFname, f.mimeType, f.fileName,
d2.stringValue AS path
FROM archive_obs_group_members m
INNER JOIN archive_observations o ON m.childObservation = o.uid
INNER JOIN archive_files f ON f.observationId=m.childObservation
    AND f.semanticType = (SELECT uid FROM archive_semanticTypes WHERE name=\"pigazing:movingObject/maximumBrightness\")
INNER JOIN archive_observatories l ON o.observatory = l.uid
LEFT OUTER JOIN archive_metadata d2 ON o.uid = d2.observationId AND
    d2.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey=\"pigazing:pathBezier\")
LEFT OUTER JOIN archive_metadata d3 ON o.uid = d3.observationId AND
    d2.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey=\"pigazing:width\")
LEFT OUTER JOIN archive_metadata d4 ON o.uid = d4.observationId AND
    d2.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey=\"pigazing:height\")
WHERE m.groupId IN
    (SELECT groupId FROM archive_obs_groups g
     INNER JOIN archive_obs_group_members m2 ON m2.groupId=g.uid AND m2.childObservation=:i);
");
$stmt->bindParam(':i', $i, PDO::PARAM_INT);
$stmt->execute(['i' => $uid]);
$simultaneous_events = $stmt->fetchAll();

// Information about this event
$pageInfo = [
    "pageTitle" => "Moving object detected at " . date("d M Y - H:i", $observation['obsTime']),
    "pageDescription" => "Pi Gazing",
    "activeTab" => "search",
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => [],
    "breadcrumb" => [["observatory.php?id=" . $obstory['publicId'], $obstory['name']]]
];

$pageTemplate->header($pageInfo);

?>

<table style="width:100%; margin:4px 0;">
    <tr>
        <?php if ($related['prev']): ?>
            <td style="text-align:left;">
                <form method="get" action="<?php echo $const->server; ?>moving_obj.php">
                    <input type="hidden" name="id" value="<?php echo $related['prev'][0]['uid']; ?>"/>
                    <input class="btn btn-sm btn-success" type="submit" value="Previous"/>
                </form>
            </td>
        <?php endif; ?>
        <?php if ($related['next']): ?>
            <td style="text-align:right;">
                <form method="get" action="<?php echo $const->server; ?>moving_obj.php">
                    <input type="hidden" name="id" value="<?php echo $related['next'][0]['uid']; ?>"/>
                    <input class="btn btn-sm btn-success" type="submit" value="Next"/>
                </form>
            </td>
        <?php endif; ?>
    </tr>
</table>

<?php

if (array_key_exists("pigazing:movingObject/video", $files_by_type)):
    $video = $files_by_type["pigazing:movingObject/video"];
    $file_url = "/api/files/content/{$video['repositoryFname']}/{$video['fileName']}";
    ?>

    <div class="row">
        <div class="col-xl-8">
            <div class="gallery_still">
                <video class="gallery_still_img" controls>
                    <source src="<?php echo $file_url; ?>" type="video/mp4"/>
                    Your browser does not support the video tag.
                </video>
            </div>
        </div>
        <div class="col-xl-4">
            <h5>Observation type</h5>
            <p><?php echo $const->semanticTypes[$observation['semanticType']][1]; ?></p>
            <h5>Observatory</h5>
            <p><a href="observatory.php?id=<?php echo $obstory['publicId']; ?>"><?php echo $obstory['name']; ?></a></p>
            <h5>Time</h5>
            <p><?php echo date("d M Y - H:i", $observation['obsTime']); ?></p>
        </div>
    </div>

<?php endif; ?>

<?php if ($allow_item_to_be_featured): ?>
    <h3>Administration panel: categorise this detection</h3>

    <?php

    // Look up pre-existing categorisation of this image
    $item_category = "Not set";

    if (array_key_exists("web:category", $metadata_by_key)) $item_category = $metadata_by_key["web:category"];
    ?>

    <form class="form-horizontal search-form" method="get" action="/moving_obj.php">
        <div class="grey_box">
            <div class="row">
                <div class="col-sm-8">
                    <input type="hidden" name="id" value="<?php echo $id; ?>"/>
                    <input type="hidden" name="update" value="1"/>
                    <div class="form-section">
                        <span class="formlabel2">Categorise</span>
                        <?php $getargs->makeFormSelect("category", $item_category, $const->item_categories, 0); ?>
                    </div>
                </div>
                <div class="col-sm-4">
                    <div style="padding:40px 0 40px 0;">
                        <button type="submit" class="btn btn-primary btn-sm">Update</button>
                    </div>
                </div>
            </div>
        </div>
    </form>
<?php endif; ?>

<?php
if (count($simultaneous_events) > 0) {
    ?>
    <h3>Other possible detections of the same object</h3>
    <?php

    $gallery_items = [];
    foreach ($simultaneous_events as $item) {
        $gallery_items[] = [
            "fileId" => $item['repositoryFname'],
            "filename" => $item["fileName"],
            "caption" => $item["obstory"],
            "hover" => null,
            "path" => $item['path'],
            "image_width" => $item['width'],
            "image_height" => $item['height'],
            "linkId" => $item['repositoryFname'],
            "mimeType" => $item['mimeType']
        ];
    }
    $pageTemplate->imageGallery($gallery_items, "/image.php?id=", true);

}
?>

<?php if (count($file_list) > 0): ?>
    <h3>Other files associated with this event</h3>

    <div class="moving-obj-files">

        <?php

        // Display results
        $gallery_items = [];
        foreach ($file_list as $item) {
            $semantic_type = $item['semanticType'];
            if (array_key_exists($semantic_type, $const->semanticTypes))
                $caption = $const->semanticTypes[$semantic_type];
            else
                $caption = [$semantic_type, ""];
            if ($caption == null) continue;
            $gallery_items[] = [
                    "fileId" => $item['repositoryFname'],
                "filename" => $item["fileName"],
                "caption" => $caption[0],
                "hover" => $caption[1],
                "path" => $metadata_by_key['pigazing:pathBezier'],
                "image_width" => $metadata_by_key['pigazing:width'],
                "image_height" => $metadata_by_key['pigazing:height'],
                "linkId" => $item['repositoryFname'],
                "mimeType" => $item['mimeType']];
        }
        $pageTemplate->imageGallery($gallery_items, "/image.php?id=", true);
        ?>
    </div>
<?php else: ?>
    <p>None</p>
<?php endif; ?>

    <h3>Status information about this detection</h3>
<?php if (count($metadata) > 0): ?>
    <table class="metadata" style="max-width:700px;">
        <thead>
        <tr>
            <td>Property</td>
            <td>Value</td>
        </tr>
        </thead>
        <?php
        foreach ($metadata as $item):
            $key = $item['metaKey'];
            if (array_key_exists($key, $const->metadataFields)) $key = $const->metadataFields[$key];
            $value = $item['stringValue'] ? $item['stringValue'] : sprintf("%.2f", $item['floatValue']);
            ?>
            <tr class="active">
                <td style="vertical-align:top;white-space:nowrap;" title="<?php echo $item['metaKey']; ?>">
                    <?php echo $key; ?>
                </td>
                <td><?php echo $value; ?></td>
            </tr>
        <?php endforeach; ?>
    </table>
<?php else: ?>
    <p>None</p>
<?php endif; ?>

<?php
// Page footer
$pageTemplate->footer($pageInfo);

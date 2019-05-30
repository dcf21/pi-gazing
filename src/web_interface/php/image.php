<?php

// image.php
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

// Look up details of file
$stmt = $const->db->prepare("
SELECT f.uid,f.repositoryFname,f.observationId,f.mimeType,f.fileName,s.name AS semanticType
FROM archive_files f
INNER JOIN archive_semanticTypes s ON f.semanticType = s.uid
WHERE repositoryFname=:i;");
$stmt->bindParam(':i', $i, PDO::PARAM_STR, strlen($id));
$stmt->execute(['i' => $id]);
$results = $stmt->fetchAll();

// Check file exists
if (count($results) != 1) die ("Requested file does not exist.");
$result = $results[0];
$uid = $result['uid'];

// Get the associated observation
$stmt = $const->db->prepare("
SELECT o.observatory, o.obsTime, s.name AS semanticType
FROM archive_observations o
INNER JOIN archive_semanticTypes s ON o.obsType = s.uid
WHERE o.uid=:i;");
$stmt->bindParam(':i', $i, PDO::PARAM_INT);
$stmt->execute(['i' => $result['observationId']]);
$observations = $stmt->fetchAll();

// Check observation exists
if (count($observations) != 1) die ("Requested file does not have associated observation.");
$observation = $observations[0];

// Get observatory information
$stmt = $const->db->prepare("SELECT * FROM archive_observatories WHERE uid=:i;");
$stmt->bindParam(':i', $i, PDO::PARAM_INT);
$stmt->execute(['i' => $observation['observatory']]);
$obstory = $stmt->fetch();

// Check mime type
$mime_type = $result['mimeType'];
$file_url = "/api/files/content/{$result['repositoryFname']}/{$result['fileName']}";

// Does user have permission to set metadata on this item?
$allow_item_to_be_featured = (($mime_type == "image/png") && in_array("voter", $user->roles));

// Find previous and next images of the same type, from the same observatory
$related = [];

$flag_highlights = 0;
$search_highlights = "";

if (array_key_exists("highlights", $_GET) && $_GET["highlights"]) {
    $flag_highlights = 1;
    $search_highlights = "AND o.featured ";
}

foreach ([["prev", "<", "DESC"], ["next", ">", "ASC"]] as $sort) {
    $stmt = $const->db->prepare("
SELECT f.repositoryFname AS uid
FROM archive_files f
INNER JOIN archive_observations o on f.observationId = o.uid
INNER JOIN archive_semanticTypes s ON f.semanticType = s.uid
WHERE s.name=:s AND o.observatory=:o AND o.obsTime {$sort[1]} :t {$search_highlights}
ORDER BY o.obsTime {$sort[2]} LIMIT 1;");
    $stmt->bindParam(':s', $s, PDO::PARAM_STR, strlen($result['semanticType']));
    $stmt->bindParam(':t', $t, PDO::PARAM_STR, 32);
    $stmt->bindParam(':o', $o, PDO::PARAM_INT);
    $stmt->execute(['o' => $observation['observatory'], 't' => $observation['obsTime'], 's' => $result['semanticType']]);
    $related[$sort[0]] = $stmt->fetchAll();
}

// Set categorisation of image based on get data
if ($allow_item_to_be_featured && array_key_exists("update", $_GET)) {
    set_metadata("web:featured",
        array_key_exists("feature", $_GET) ? 1 : null,
        $observation['obsTime'],
        $uid,
        "fileId");
    if (array_key_exists("caption", $_GET))
        set_metadata("web:caption",
            $_GET["caption"],
            $observation['obsTime'],
            $uid,
            "fileId");
}

// Get list of metadata
$stmt = $const->db->prepare("
SELECT m.time, mf.metaKey, m.floatValue, m.stringValue
FROM archive_metadata m
INNER JOIN archive_metadataFields mf ON m.fieldId = mf.uid
WHERE fileId=:i;");
$stmt->bindParam(':i', $i, PDO::PARAM_INT);
$stmt->execute(['i' => $uid]);
$metadata = $stmt->fetchAll();

// Make metadata dictionary
$metadata_by_key = [];
foreach ($metadata as $item) {
    $metadata_by_key[$item['metaKey']] = $item['stringValue'] ? $item['stringValue'] : $item['floatValue'];
}

// Get list of other files
$stmt = $const->db->prepare("
SELECT f.repositoryFname, f.fileName, o.obsTime, l.publicId AS obstoryId, sf.name AS obstoryName,
f.mimeType AS mimeType,sf.name AS semanticType
FROM archive_files f
INNER JOIN archive_observations o ON f.observationId = o.uid
INNER JOIN archive_observatories l ON o.observatory = l.uid
INNER JOIN archive_semanticTypes sf ON f.semanticType = sf.uid
WHERE f.observationId=:i;");
$stmt->bindParam(':i', $i, PDO::PARAM_INT);
$stmt->execute(['i' => $result['observationId']]);
$other_files = $stmt->fetchAll();

// Information about this event
$pageInfo = [
    "pageTitle" => "{$const->mimeTypes[$mime_type]} recorded at " . date("d M Y - H:i", $observation['obsTime']),
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
                <form method="get" action="<?php echo $const->server; ?>image.php">
                    <input type="hidden" name="id" value="<?php echo $related['prev'][0]['uid']; ?>"/>
                    <input type="hidden" name="highlights" value="<?php echo $flag_highlights; ?>"/>
                    <input class="btn btn-sm btn-success" type="submit" value="Previous"/>
                </form>
            </td>
        <?php endif; ?>
        <?php if ($related['next']): ?>
            <td style="text-align:right;">
                <form method="get" action="<?php echo $const->server; ?>image.php">
                    <input type="hidden" name="id" value="<?php echo $related['next'][0]['uid']; ?>"/>
                    <input type="hidden" name="highlights" value="<?php echo $flag_highlights; ?>"/>
                    <input class="btn btn-sm btn-success" type="submit" value="Next"/>
                </form>
            </td>
        <?php endif; ?>
    </tr>
</table>

    <div class="row">
        <div class="col-md-8">
            <div class="gallery_still">
                <?php if ($mime_type == "image/png"): ?>
                    <img class="gallery_still_img" alt="" title="" src="<?php echo $file_url; ?>"/>
                <?php elseif ($mime_type == "video/mp4"): ?>
                    <div style="position:relative" class="video_marker_overlay"
                         data-path='<?php echo $metadata_by_key['pigazing:path']; ?>'
                         data-width='<?php echo $metadata_by_key['pigazing:width']; ?>'
                         data-height='<?php echo $metadata_by_key['pigazing:height']; ?>'
                         data-start='<?php echo $metadata_by_key['pigazing:videoStart']; ?>'
                    >
                        <img class="video_path_marker" alt="" title="" src="/img/crosshair.gif"/>
                        <video class="gallery_still_img" controls>
                            <source src="<?php echo $file_url; ?>" type="video/mp4"/>
                            Your browser does not support the video tag.
                        </video>
                    </div>
                <?php else: ?>
                    <div class="gallery_still_img scrolling_text_container">
                        <?php
                        $file_path = $const->datapath . $result['repositoryFname'];
                        if (file_exists($file_path)) echo htmlentities(file_get_contents($file_path));
                        ?>
                    </div>
                <?php endif; ?>
            </div>
        </div>
        <div class="col-md-4">
            <?php if ($mime_type == "video/mp4"): ?>
            <h5>Video controls</h5>
            <label>
                <input type="checkbox" checked="" class="video_marker" /> Show position marker
            </label>
            <?php endif; ?>
            <h5>Observation type</h5>
            <p><?php echo $const->semanticTypes[$observation['semanticType']][1]; ?></p>
            <h5>Observatory</h5>
            <p><a href="observatory.php?id=<?php echo $obstory['publicId']; ?>"><?php echo $obstory['name']; ?></a></p>
            <h5>Time</h5>
            <p><?php echo date("d M Y - H:i", $observation['obsTime']); ?></p>
            <h5><?php echo $const->mimeTypes[$mime_type]; ?> type</h5>
            <?php
            $semantic_type = $result['semanticType'];
            if (array_key_exists($semantic_type, $const->semanticTypes)) {
                print "<p><b>" . $const->semanticTypes[$semantic_type][0] . "</b>. ";
                print $const->semanticTypes[$semantic_type][1] . "</p>";
            }
            ?>
        </div>
    </div>


<?php if ($allow_item_to_be_featured): ?>
    <h3>Administration panel: promote this image</h3>

    <?php

    // Look up pre-existing categorisation of this image
    $featured = false;
    $item_caption = "";

    if (array_key_exists("web:featured", $metadata_by_key)) $featured = true;
    if (array_key_exists("web:caption", $metadata_by_key)) $item_caption = $metadata_by_key["web:caption"];
    ?>

    <form class="form-horizontal search-form" method="get" action="/image.php">
        <div class="grey_box">
            <div class="row">
                <div class="col-sm-8">
                    <input type="hidden" name="id" value="<?php echo $id; ?>"/>
                    <input type="hidden" name="update" value="1"/>

                    <div class="form-section">
                        <label>
                            <input type="checkbox" name="feature"
                                <?php if ($featured) echo 'checked="checked"'; ?> >
                            Feature this image.
                        </label>
                    </div>
                    <div class="form-section">
                        <span class="formlabel2">Caption</span>
                        <input class="form-control-dcf form-inline-number"
                               name="caption"
                               style="width:350px;"
                               type="text"
                               value="<?php echo $item_caption; ?>"
                        />
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

    <h3>
        <?php if ($observation['semanticType'] == "timelapse"): ?>Other versions of this image
        <?php else: ?>Other files associated with this event
        <?php endif; ?>
    </h3>
<?php if (count($other_files) > 0): ?>
    <div class="moving-obj-files">

        <?php

        // Display results
        $gallery_items = [];
        foreach ($other_files as $item) {
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
                "linkId" => $item['repositoryFname'],
                "mimeType" => $item['mimeType']];
        }
        $pageTemplate->imageGallery($gallery_items, "/image.php?id=", false);
        ?>
    </div>
<?php else: ?>
    <p>None</p>
<?php endif; ?>

    <h3>Status information about this image</h3>
<?php if (count($metadata) > 0): ?>
    <table class="metadata">
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
    <p>None available</p>
<?php endif; ?>

<?php

// Page footer
$pageTemplate->footer($pageInfo);

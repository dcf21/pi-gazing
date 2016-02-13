<?php

// moving_obj.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

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
SELECT m.observationId, l.name AS obstory, f.repositoryFname, f.mimeType, f.fileName
FROM archive_obs_group_members m
INNER JOIN archive_observations o ON m.observationId = o.uid
INNER JOIN archive_files f ON f.observationId=m.observationId
INNER JOIN archive_semanticTypes fs ON f.semanticType = fs.uid AND fs.name=\"meteorpi:triggers/event/maxBrightness\"
INNER JOIN archive_observatories l ON o.observatory = l.uid
INNER JOIN archive_obs_groups g ON g.uid=m.groupId
INNER JOIN archive_obs_group_members m2 ON m2.groupId=g.uid AND m2.observationId=:i;");
$stmt->bindParam(':i', $i, PDO::PARAM_INT);
$stmt->execute(['i' => $uid]);
$simultaneous_events = $stmt->fetchAll();

// Information about this event
$pageInfo = [
    "pageTitle" => "Moving object detected at " . date("d M Y - h:i", $observation['obsTime']),
    "pageDescription" => "Meteor Pi",
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

<?php
if (array_key_exists("meteorpi:triggers/event", $files_by_type)):
    $video = $files_by_type["meteorpi:triggers/event"];
    $file_url = "/api/files/content/{$video['repositoryFname']}/{$video['fileName']}";
    ?>

    <div class="row">
        <div class="col-md-8">
            <div class="gallery_still">
                <video class="gallery_still_img" controls>
                    <source src="<?php echo $file_url; ?>" type="video/mp4"/>
                    Your browser does not support the video tag.
                </video>
            </div>
        </div>
        <div class="col-md-4">
            <h5>Observation type</h5>
            <p><?php echo $const->semanticTypes[$observation['semanticType']][1]; ?></p>
            <h5>Observatory</h5>
            <p><a href="observatory.php?id=<?php echo $obstory['publicId']; ?>"><?php echo $obstory['name']; ?></a></p>
            <h5>Time</h5>
            <p><?php echo date("d M Y - h:i", $observation['obsTime']); ?></p>
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
                        <button type="submit" class="btn btn-primary">Update</button>
                    </div>
                </div>
            </div>
        </div>
    </form>
<?php endif; ?>

<?php
if (count($simultaneous_events)>0)
{
    ?>
    <h3>Other possible detections of the same object</h3>
    <?php

    $gallery_items = [];
    foreach ($simultaneous_events as $item)
    {
        $gallery_items[] = ["fileId" => $item['repositoryFname'],
            "filename" => $item["fileName"],
            "caption" => $item["obstory"],
            "hover" => "",
            "linkId" => $item['repositoryFname'],
            "mimeType" => $item['mimeType']];
    }
    $pageTemplate->imageGallery($gallery_items, "/image.php?id=");

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
                continue;
            if ($caption == null) continue;
            $gallery_items[] = ["fileId" => $item['repositoryFname'],
                "filename" => $item["fileName"],
                "caption" => $caption[0],
                "hover" => $caption[1],
                "linkId" => $item['repositoryFname'],
                "mimeType" => $item['mimeType']];
        }
        $pageTemplate->imageGallery($gallery_items, "/image.php?id=");
        ?>
    </div>
<?php else: ?>
    <p>None</p>
<?php endif; ?>

    <h3>Status information about this detection</h3>
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
                <td><?php echo $key; ?></td>
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

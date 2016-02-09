<?php

// image.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

require "php/imports.php";
require_once "php/html_getargs.php";

$getargs = new html_getargs(true);

// Get ID for event to display
$id = "";
if (array_key_exists("id", $_GET)) $id = $_GET["id"];

// Look up details of file
$stmt = $const->db->prepare("
SELECT f.uid,f.repositoryFname,f.observationId,f.mimeType,f.fileName,s.name AS semanticType
FROM archive_files f
INNER JOIN archive_semanticTypes s ON f.semanticType=s.uid
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

// Get list of metadata
$stmt = $const->db->prepare("
SELECT m.time, mf.metaKey, m.floatValue, m.stringValue
FROM archive_metadata m
INNER JOIN archive_metadataFields mf ON m.fieldId = mf.uid
WHERE fileId=:i;");
$stmt->bindParam(':i', $i, PDO::PARAM_INT);
$stmt->execute(['i' => $uid]);
$metadata = $stmt->fetchAll();

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
    "pageTitle" => "Image recorded at " . date("d M Y - h:i", $observation['obsTime']),
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

    <div class="row">
        <div class="col-md-8">
            <div class="gallery_still">
                <img alt="" title="" src="/api/files/content/<?php
                echo $result['repositoryFname'] . "/" . $result['fileName'];
                ?>"/>
            </div>
        </div>
        <div class="col-md-4">
            <h5>Observation type</h5>
            <p><?php echo $const->semanticTypes[$observation['semanticType']][1]; ?></p>
            <h5>Observatory</h5>
            <p><a href="observatory.php?id=<?php echo $obstory['publicId']; ?>"><?php echo $obstory['name']; ?></a></p>
            <h5>Time</h5>
            <p><?php echo date("d M Y - h:i", $observation['obsTime']); ?></p>
            <h5>Image Type</h5>
            <?php
            $semantic_type = $result['semanticType'];
            if (array_key_exists($semantic_type, $const->semanticTypes))
            {
              print "<p><b>".$const->semanticTypes[$semantic_type][0]."</b>. ";
              print $const->semanticTypes[$semantic_type][1]."</p>";
            }
            ?>
        </div>
    </div>

    <h3>Other versions of this image</h3>
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
                continue;
            if ($caption==null) continue;
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
                <td><?php echo $key; ?></td>
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

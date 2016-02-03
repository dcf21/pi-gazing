<?php

// observatory_metadata.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

require_once "php/imports.php";
require_once "php/html_getargs.php";

$getargs = new html_getargs();

$obstories = $getargs->obstory_objlist;
$obstory = $getargs->readObservatory("id");
$obstory_name = $getargs->obstory_objs[$obstory]['name'];

// Fetch observatory metadata
$stmt = $const->db->prepare("
SELECT m.time, mf.metaKey, m.floatValue, m.stringValue FROM archive_metadata m
INNER JOIN archive_observatories o ON m.observatory = o.uid
INNER JOIN archive_metadataFields mf ON m.fieldId = mf.uid
WHERE o.publicId=:o
ORDER BY m.time DESC;");
$stmt->bindParam(':o', $o, PDO::PARAM_STR, strlen($obstory));
$stmt->execute(['o' => $obstory]);
$metadata = $stmt->fetchAll();

$pageInfo = [
    "pageTitle" => "Observatory {$obstory_name}: Status information",
    "pageDescription" => "Meteor Pi",
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

        <table class="metadata">
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
                $value = $item['stringValue'] ? $item['stringValue'] : $item['floatValue'];
                $superseded = in_array($key, $seenKeys);
                if (!$superseded) $seenKeys[] = $key;
                ?>
                <tr class="<?php echo $superseded ? 'superseded' : 'active'; ?>">
                    <td><?php echo date("d M Y - h:i", $item['time']); ?></td>
                    <td><?php echo $key; ?></td>
                    <td><?php echo $value; ?></td>
                </tr>
            <?php endforeach; ?>
        </table>
    </div

    <div class="col-md-2">
        <?php $pageTemplate->listObstories($obstories, "/observatory_metadata.php?id="); ?>
    </div>
</div>

<?php
$pageTemplate->footer($pageInfo);


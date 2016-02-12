<?php

// index.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

require "php/imports.php";

// Search for featured images
$stmt = $const->db->prepare("
SELECT f.repositoryFname, f.fileName,
o.publicId AS obsId, o.obsTime,
d2.stringValue AS caption, so.name AS obsType
FROM archive_files f
INNER JOIN archive_observations o ON f.observationId = o.uid
INNER JOIN archive_semanticTypes so ON o.obsType = so.uid
INNER JOIN archive_metadata d ON f.uid = d.fileId
INNER JOIN archive_metadataFields df ON d.fieldId = df.uid AND df.metaKey=\"web:featured\"
INNER JOIN archive_metadata d2 ON f.uid = d2.fileId
INNER JOIN archive_metadataFields df2 ON d2.fieldId = df2.uid AND df2.metaKey=\"web:caption\"
ORDER BY o.obsTime DESC LIMIT 6;");
$stmt->execute([]);
$result_list = $stmt->fetchAll();

$paneList = [];
foreach ($result_list as $item) {
    if ($item["obsType"] == "timelapse") $link = "/image.php?id=" . $item['repositoryFname'];
    else $link = "/moving_obj.php?id=" . $item['obsId'];
    $paneList[] = ["link" => $link,
        "caption" => $item['caption'],
        "teaser" => "api/files/content/" . $item['repositoryFname'] . "/" . $item['fileName']
    ];
}

$pageInfo = [
    "pageTitle" => "Meteor Pi",
    "pageDescription" => "Meteor Pi",
    "activeTab" => "projects",
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => []
];

$pageTemplate->header($pageInfo);

?>
    <div class="row">
        <div class="col-md-6" style="padding:8px;">
            <p class="text" style="font-size:18px;">Meteor Pi is a network of cameras set up by Cambridge Science Centre
                to observe the night sky.</p>

            <p class="text">They record videos of moving objects, including shooting stars, planes and satellites. They
                also take time lapse photographs through the night showing the movement of the stars.</p>

            <p class="text">All of the images are freely available on this website, and enabling children, amateur
                astronomers and coders to browse the night sky.</p>

            <p class="text">The images on this page show some of the objects we have picked up in recent weeks. Click on
                "Search the Skies" to access all the data recorded by Meteor Pi.</p>

        </div>
        <div class="col-md-6" style="padding:8px;">
            <?php $pageTemplate->slidingPanes($paneList); ?>
        </div>
    </div>

<?php
$pageTemplate->footer($pageInfo);

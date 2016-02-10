<?php

// observatory.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

require "php/imports.php";
require_once "php/html_getargs.php";

$getargs = new html_getargs(false);

// Fetch list of observatories
$obstories = $getargs->obstory_objlist;
$obstory = $getargs->readObservatory("id");
$obstory_name = $getargs->obstory_objs[$obstory]['name'];

// Get oldest observation
$stmt = $const->db->prepare("
SELECT o.obsTime FROM archive_observations o
INNER JOIN archive_observatories l ON o.observatory = l.uid
WHERE l.publicId=:o
ORDER BY obsTime ASC LIMIT 1;");
$stmt->bindParam(':o', $o, PDO::PARAM_STR, strlen($obstory));
$stmt->execute(["o"=>$obstory]);
$oldest_obs = $stmt->fetch();
if ($oldest_obs) $oldest_obs_date = date("d M Y - h:i", $oldest_obs['obsTime']);
else $oldest_obs_date = "&ndash;";

// Get newest observation
$stmt = $const->db->prepare("
SELECT obsTime FROM archive_observations o
INNER JOIN archive_observatories l ON o.observatory = l.uid
WHERE l.publicId=:o
ORDER BY obsTime DESC LIMIT 1;");
$stmt->bindParam(':o', $o, PDO::PARAM_STR, strlen($obstory));
$stmt->execute(["o"=>$obstory]);
$newest_obs = $stmt->fetch();
if ($newest_obs) $newest_obs_date = date("d M Y - h:i", $newest_obs['obsTime']);
else $newest_obs_date = "&ndash;";

// Total image count
$stmt = $const->db->prepare("
SELECT COUNT(*) FROM archive_observations o
INNER JOIN archive_observatories l ON o.observatory = l.uid
INNER JOIN archive_semanticTypes s ON o.obsType = s.uid
WHERE l.publicId=:o AND s.name=\"timelapse\"
ORDER BY obsTime DESC LIMIT 1;");
$stmt->bindParam(':o', $o, PDO::PARAM_STR, strlen($obstory));
$stmt->execute(["o"=>$obstory]);
$image_count = $stmt->fetch()['COUNT(*)'];

// Moving object count
$stmt = $const->db->prepare("
SELECT COUNT(*) FROM archive_observations o
INNER JOIN archive_observatories l ON o.observatory = l.uid
INNER JOIN archive_semanticTypes s ON o.obsType = s.uid
WHERE l.publicId=:o AND s.name=\"movingObject\"
ORDER BY obsTime DESC LIMIT 1;");
$stmt->bindParam(':o', $o, PDO::PARAM_STR, strlen($obstory));
$stmt->execute(["o"=>$obstory]);
$moving_count = $stmt->fetch()['COUNT(*)'];

$pageInfo = [
    "pageTitle" => "The Meteor Pi network: {$obstory_name}",
    "pageDescription" => "Meteor Pi",
    "activeTab" => "cameras",
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => []
];

$pageTemplate->header($pageInfo);

?>

<div class="row camera_map" data-meta='<?php echo json_encode([$getargs->obstory_objs[$obstory]]); ?>'>
    <div class="col-md-10">
        <div class="map_holder"
             style="width:100%; height:550px; background-color:#eee; display:inline-block; margin: 12px auto;">
            <div class="map_canvas" style="width:100%; height:100%;"></div>
        </div>
    </div>
    <div class="col-md-2">
        <h5>Latest images</h5>
        <?php echo $newest_obs_date; ?>
        <h5>First active</h5>
        <?php echo $oldest_obs_date; ?>
        <h5>Total images</h5>
        <?php echo $image_count; ?>
        <h5>Total moving objects</h5>
        <?php echo $moving_count; ?>
        <h5>More information</h5>
        <p><a href="/observatory_activity.php?id=<?php echo $obstory; ?>">Calendar of observations</a></p>
        <p><a href="/observatory_metadata.php?id=<?php echo $obstory; ?>">Status messages</a></p>
    </div>
    </div>

<?php
$pageTemplate->footer($pageInfo);


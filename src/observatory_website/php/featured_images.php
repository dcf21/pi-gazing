<?php

// featured_images.php
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
o.publicId AS obsId, o.uid AS observation, o.obsTime,
d2.stringValue AS caption, so.name AS obsType
FROM archive_files f
INNER JOIN archive_observations o ON f.observationId = o.uid
INNER JOIN archive_observatories l ON o.observatory = l.uid
INNER JOIN archive_semanticTypes so ON o.obsType = so.uid
INNER JOIN archive_metadata d ON f.uid = d.fileId AND d.fieldId = (SELECT uid FROM archive_metadataFields WHERE metaKey=\"web:featured\")
INNER JOIN archive_metadata d2 ON f.uid = d2.fileId AND d2.fieldId = (SELECT uid FROM archive_metadataFields WHERE metaKey=\"web:caption\")
ORDER BY o.obsTime DESC LIMIT 10;");
$stmt->execute([]);
$result_list = $stmt->fetchAll();

$paneList = [];
foreach ($result_list as $item) {
    if ($item["obsType"] == "timelapse") $link = "/image.php?id=" . $item['repositoryFname'];
    else $link = "/moving_obj.php?id=" . $item['obsId'];
    $paneDescriptor = ["link" => $link,
        "observatoryName" => $item['obsName'],
        "observatoryId" => $item['locId'],
        "time" => $item['obsTime'],
        "timeString" => date("d M Y - H:i", $item['obsTime']),
        "caption" => $item['caption'],
        "weblink" => $link,
        "image" => "api/files/content/" . $item['repositoryFname'] . "/" . $item['fileName']
    ];

    $stmt = $const->db->prepare("
SELECT f.repositoryFname, f.fileName
FROM archive_files f
WHERE f.observationId=:o AND f.semanticType =
(SELECT uid FROM archive_semanticTypes WHERE name=\"pigazing:triggers/event\");");
    $stmt->bindParam(':o', $o, PDO::PARAM_INT);
    $stmt->execute([':o' => $item['observation']]);
    $video_list = $stmt->fetchAll();

    if (count($video_list) > 0)
        $paneDescriptor['video'] = "api/files/content/" . $video_list[0]['repositoryFname'] . "/" .
            $video_list[0]['fileName'];

    $paneList[] = $paneDescriptor;
}

header('Content-Type: text/javascript');
print json_encode($paneList);

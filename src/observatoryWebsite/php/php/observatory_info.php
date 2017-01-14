<?php

// observatory_info.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

// -------------------------------------------------
// Copyright 2016 Cambridge Science Centre.

// This file is part of Meteor Pi.

// Meteor Pi is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Meteor Pi is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Meteor Pi.  If not, see <http://www.gnu.org/licenses/>.
// -------------------------------------------------

// User this to make local modifications, e.g. adding Google Analytics code

class observatory_info
{
    // This function returns the oldest and newest observations from an observatoryId
    public static function observatory_info($obstory)
    {
        global $const;

        // Get oldest observation
        $stmt = $const->db->prepare("
SELECT o.obsTime FROM archive_observations o
INNER JOIN archive_observatories l ON o.observatory = l.uid
WHERE l.publicId=:o
ORDER BY obsTime ASC LIMIT 1;");
        $stmt->bindParam(':o', $o, PDO::PARAM_STR, strlen($obstory));
        $stmt->execute(["o" => $obstory]);
        $oldest_obs = $stmt->fetch();
        $oldest_obs_utc = null;
        $oldest_obs_date = "&ndash;";
        if ($oldest_obs) {
            $oldest_obs_utc = $oldest_obs['obsTime'];
            $oldest_obs_date = date("d M Y - H:i", $oldest_obs_utc);
        }

        // Get newest observation
        $stmt = $const->db->prepare("
SELECT obsTime FROM archive_observations o
INNER JOIN archive_observatories l ON o.observatory = l.uid
WHERE l.publicId=:o
ORDER BY obsTime DESC LIMIT 1;");
        $stmt->bindParam(':o', $o, PDO::PARAM_STR, strlen($obstory));
        $stmt->execute(["o" => $obstory]);
        $newest_obs = $stmt->fetch();
        $newest_obs_utc = null;
        $newest_obs_date = "&ndash;";
        if ($newest_obs) {
            $newest_obs_utc = $newest_obs['obsTime'];
            $newest_obs_date = date("d M Y - H:i", $newest_obs_utc);
        }

        // Total image count
        $stmt = $const->db->prepare("
SELECT COUNT(*) FROM archive_observations o
INNER JOIN archive_observatories l ON o.observatory = l.uid
INNER JOIN archive_semanticTypes s ON o.obsType = s.uid
WHERE l.publicId=:o AND s.name=\"timelapse\"
ORDER BY obsTime DESC LIMIT 1;");
        $stmt->bindParam(':o', $o, PDO::PARAM_STR, strlen($obstory));
        $stmt->execute(["o" => $obstory]);
        $image_count = $stmt->fetch()['COUNT(*)'];

        // Moving object count
        $stmt = $const->db->prepare("
SELECT COUNT(*) FROM archive_observations o
INNER JOIN archive_observatories l ON o.observatory = l.uid
INNER JOIN archive_semanticTypes s ON o.obsType = s.uid
WHERE l.publicId=:o AND s.name=\"movingObject\"
ORDER BY obsTime DESC LIMIT 1;");
        $stmt->bindParam(':o', $o, PDO::PARAM_STR, strlen($obstory));
        $stmt->execute(["o" => $obstory]);
        $moving_count = $stmt->fetch()['COUNT(*)'];

        return [
            "moving_count" => $moving_count,
            "image_count" => $image_count,
            "newest_obs_utc" => $newest_obs_utc,
            "newest_obs_date" => $newest_obs_date,
            "oldest_obs_utc" => $oldest_obs_utc,
            "oldest_obs_date" => $oldest_obs_date
        ];
    }

}

<?php

// observatory_info.php
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

// User this to make local modifications, e.g. adding Google Analytics code

class observatory_info
{
    // This function returns the oldest and newest observations from an observatoryId
    public static function obstory_info($obstory)
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
        $oldest_obs_date = $oldest_obs_date_short = "&ndash;";
        if ($oldest_obs) {
            $oldest_obs_utc = $oldest_obs['obsTime'];
            $oldest_obs_date = date("d M Y - H:i", $oldest_obs_utc);
            $oldest_obs_date_short = date("d M Y", $oldest_obs_utc);
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
        $newest_obs_date = $newest_obs_date_short = "&ndash;";
        if ($newest_obs) {
            $newest_obs_utc = $newest_obs['obsTime'];
            $newest_obs_date = date("d M Y - H:i", $newest_obs_utc);
            $newest_obs_date_short = date("d M Y", $newest_obs_utc);
        }

        // Total image count
        $stmt = $const->db->prepare("
SELECT COUNT(*) FROM archive_observations o
INNER JOIN archive_observatories l ON o.observatory = l.uid
INNER JOIN archive_semanticTypes s ON o.obsType = s.uid
WHERE l.publicId=:o AND s.name=\"pigazing:timelapse/\"
ORDER BY obsTime DESC LIMIT 1;");
        $stmt->bindParam(':o', $o, PDO::PARAM_STR, strlen($obstory));
        $stmt->execute(["o" => $obstory]);
        $image_count = $stmt->fetch()['COUNT(*)'];

        // Moving object count
        $stmt = $const->db->prepare("
SELECT COUNT(*) FROM archive_observations o
INNER JOIN archive_observatories l ON o.observatory = l.uid
INNER JOIN archive_semanticTypes s ON o.obsType = s.uid
WHERE l.publicId=:o AND s.name=\"pigazing:movingObject/\"
ORDER BY obsTime DESC LIMIT 1;");
        $stmt->bindParam(':o', $o, PDO::PARAM_STR, strlen($obstory));
        $stmt->execute(["o" => $obstory]);
        $moving_count = $stmt->fetch()['COUNT(*)'];

        return [
            "moving_count" => $moving_count,
            "image_count" => $image_count,
            "newest_obs_utc" => $newest_obs_utc,
            "newest_obs_date" => $newest_obs_date,
            "newest_obs_date_short" => $newest_obs_date_short,
            "oldest_obs_utc" => $oldest_obs_utc,
            "oldest_obs_date" => $oldest_obs_date,
            "oldest_obs_date_short" => $oldest_obs_date_short
        ];
    }

    // This function returns a list of metadata for an observatory
    public static function obstory_metadata($time, $obstory)
    {
        global $const;
        $output = [];

        # See when this observatory was last serviced. Do not report any metadata set before this time.
        $last_serviced = 0;
        $stmt = $const->db->prepare("
SELECT time FROM archive_metadata
WHERE observatory=(SELECT uid FROM archive_observatories WHERE publicId=:o)
      AND fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey='refresh')
      AND time <= :t
ORDER BY time DESC LIMIT 1");
        $stmt->bindParam(':o', $o, PDO::PARAM_STR, strlen($obstory));
        $stmt->bindParam(':t', $t, PDO::PARAM_STR, 32);
        $stmt->execute(["o" => $obstory, "t" => $time]);
        $results = $stmt->fetchAll();
        if (count($results) > 0) {
            $last_serviced = $results[0]['time'];
        }

        # Loop over each known metadata field in turn, and see when it was most recently set
        $stmt = $const->db->prepare("SELECT uid,metaKey FROM archive_metadataFields;");
        $stmt->execute([]);
        $fields = $stmt->fetchAll();
        foreach ($fields as $field) {
            $stmt = $const->db->prepare("
SELECT floatValue, stringValue FROM archive_metadata
WHERE observatory=(SELECT uid FROM archive_observatories WHERE publicId=:o) AND fieldId=:f
      AND time BETWEEN :s AND :t
ORDER BY time DESC LIMIT 1");
            $stmt->bindParam(':o', $o, PDO::PARAM_STR, strlen($obstory));
            $stmt->bindParam(':f', $f, PDO::PARAM_INT);
            $stmt->bindParam(':s', $s, PDO::PARAM_STR, 32);
            $stmt->bindParam(':t', $t, PDO::PARAM_STR, 32);
            $stmt->execute(["o" => $obstory, "f" => $field['uid'], "s" => $last_serviced, "t" => $time]);
            $results = $stmt->fetchAll();

            # See if this metadata field has ever been set for this observatory
            if (count($results) > 0) {
                $result = $results[0];

                # If so, return it as a floating-point value if possible, otherwise as a string
                if (is_null($result['stringValue'])) {
                    $value = $result['floatValue'];
                } else {
                    $value = $result['stringValue'];
                }
                $output[$field['metaKey']] = $value;
            }
        }

        # Return dictionary of results
        if (array_key_exists('refresh', $output)) {
            unset($output['refresh']);
        }
        return $output;
    }

    // This function returns an array of all the lenses we have models for
    public static function fetch_lenses()
    {
        $xml = file_get_contents("../../../configuration_global/camera_properties/lenses.xml");
        $xml_data = simplexml_load_string($xml) or die("Error: Cannot create object");

        $lens_data = [];
        foreach ($xml_data->lens as $lens_item) {
            $barrel_parameters = json_decode($lens_item->radial_distortion);
            $lens_data[(string)$lens_item->name] = [
                "name" => (string)$lens_item->name,
                "fov" => (float)$lens_item->fov,
                "barrel_parameters" => $barrel_parameters
            ];
        }

        return $lens_data;
    }
}

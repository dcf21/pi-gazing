<?php

// set_metadata.php
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

require_once "constants.php";
require_once "user.php";

function get_metadata_key_id($key)
{
    global $const;
    $stmt = $const->db->prepare("SELECT uid FROM archive_metadataFields WHERE metaKey=:k;");
    $stmt->bindParam(':k', $k, PDO::PARAM_STR, strlen($key));
    $stmt->execute(['k' => $key]);
    $results = $stmt->fetchAll();
    if (count($results) < 1) {
        $stmt = $const->db->prepare("INSERT INTO archive_metadataFields (metaKey) VALUES (:k);");
        $stmt->bindParam(':k', $k, PDO::PARAM_STR, strlen($key));
        $stmt->execute(['k' => $key]);
        $stmt = $const->db->prepare("SELECT uid FROM archive_metadataFields WHERE metaKey=:k;");
        $stmt->bindParam(':k', $k, PDO::PARAM_STR, strlen($key));
        $stmt->execute(['k' => $key]);
        $results = $stmt->fetchAll();
    }
    return $results[0]['uid'];
}

function set_metadata($key, $value, $time, $uid, $column)
{
    global $const, $user;

    $meta_id = get_metadata_key_id($key);
    $stringValue = $floatValue = null;
    if (is_numeric($value)) $floatValue = floatval($value);
    else $stringValue = strval($value);

    $tstr = date("Ymd_His", time());
    $key = sprintf("%s_%s", time(), rand());
    $md5 = md5($key);
    $publicId = substr(sprintf("%s_%s", $tstr, $md5), 0, 32);

    $stmt = $const->db->prepare("
DELETE m FROM archive_metadata m
WHERE m.{$column}=:i AND m.fieldId=:k;");
    $stmt->bindParam(':i', $i, PDO::PARAM_INT);
    $stmt->bindParam(':k', $k, PDO::PARAM_INT);
    $stmt->execute(['i' => $uid, 'k' => $meta_id]);
    if ($value == null) return;
    $stmt = $const->db->prepare("
INSERT INTO archive_metadata ({$column}, fieldId, publicId, time, setAtTime, setByUser, stringValue, floatValue)
VALUES (:i,:k,:p,:t,:st,:u,:sv,:fv);");
    $stmt->bindParam(':i', $i, PDO::PARAM_INT);
    $stmt->bindParam(':k', $k, PDO::PARAM_INT);
    $stmt->bindParam(':p', $p, PDO::PARAM_INT, 64);
    $stmt->bindParam(':t', $t, PDO::PARAM_STR, 256);
    $stmt->bindParam(':st', $st, PDO::PARAM_STR, 256);
    $stmt->bindParam(':u', $u, PDO::PARAM_STR, strlen($user->userId));
    $stmt->bindParam(':sv', $sv, PDO::PARAM_STR, 256);
    $stmt->bindParam(':fv', $fv, PDO::PARAM_STR, 256);
    $stmt->execute(['i' => $uid,
        'k' => $meta_id,
        'p' => $publicId,
        't' => $time,
        'st' => time(),
        'u' => $user->userId,
        'sv' => $stringValue,
        'fv' => $floatValue
    ]);
}

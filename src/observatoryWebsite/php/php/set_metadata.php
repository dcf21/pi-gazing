<?php

// set_metadata.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

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
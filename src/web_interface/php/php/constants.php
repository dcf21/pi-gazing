<?php

// constants.php
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

$php_path = realpath(dirname(__FILE__));

require_once $php_path . "/utils.php";

class constants
{
    public $path, $server, $server_json;
    public $semanticTypes, $metadataFields, $mimeTypes;

    public function __construct()
    {
        $this->server = "/";
        $this->server_json = "/";
        $this->yearMin = 2015;
        $this->yearMax = date("Y");

        // Path to PHP modules directory
        $this->path = realpath(dirname(__FILE__));
        $this->datapath = $this->path."/../../../../datadir/db_filestore/";

        // Time we started execution
        $this->timeStart = microtime(True);

        // Set all calculations to work in UTC
        date_default_timezone_set("UTC");

        // SQL code used to fetch the current unix time
        $this->sql_unixtime = "UNIX_TIMESTAMP()";

        // List of names of the months
        $this->fullMonthNames = explode(" ", "x January February March April May June July August September October November December");
        $this->shortMonthNames = explode(" ", "x Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec");
        unset($this->shortMonthNames[0]);
        unset($this->fullMonthNames[0]);

        // Database connection details
        $this->mysqlLogin = "pigazing";
        $this->mysqlHost = "localhost";
        $this->mysqlUser = "pigazing";
        $this->mysqlPassword = "pigazing";
        $this->mysqlDB = "pigazing";

        // Connect to database
        $this->db = new PDO("mysql:host=" . $this->mysqlHost . ";dbname=" . $this->mysqlDB, $this->mysqlUser,
            $this->mysqlPassword) or die ("Can't connect to SQL database.");
        $this->db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

        // Categories of image
        $this->item_categories = ["Not set","Plane","Satellite","Meteor","Junk","Pretty sky"];

        // Known mime types
        $this->mimeTypes = ["image/png" => "Image",
            "video/mp4" => "Video",
            "application/json" => "Data file",
            "text/plain" => "Text file"
        ];

        // Known semantic types
        $this->semanticTypes = [
            "timelapse" => ["Still photograph", "A long exposure image, taken over a 30-second period"],
            "movingObject" => ["Moving object", "An object moving across the sky"],
            "pigazing:triggers/event/triggerFrame/lensCorr" => ["Initial appearance", "This image shows the first video frame in which the moving object was detected."],
            "pigazing:triggers/event/triggerFrame" => null,
            "pigazing:triggers/event/timeAverage/lensCorr" => ["Long exposure", "This shows a long exposure of the sky, taken over the entire duration that the moving object was visible."],
            "pigazing:triggers/event/timeAverage" => null,
            "pigazing:triggers/event/previousFrame/lensCorr" => ["Previous frame", "This image shows what the sky looked like immediately before the object appeared."],
            "pigazing:triggers/event/previousFrame" => null,
            "pigazing:triggers/event/maxBrightness/lensCorr" => ["Maximum brightness", "This image shows the maximum brightness of each part of the image over the course of the object's appearance. This is usually the image that shows the object most clearly."],
            "pigazing:triggers/event/maxBrightness" => null,
            "pigazing:triggers/event/mapTrigger/lensCorr" => ["Trigger map", "This map indicates why the camera thought this object was interesting. Grey spots indicate areas which had recently brightened by an unusual amount. White spots indicate areas large enough to trigger the camera's motion sensor."],
            "pigazing:triggers/event/mapTrigger" => null,
            "pigazing:triggers/event/mapExcludedPixels/lensCorr" => ["Excluded pixels", "This is a map of pixels within the frame which were being ignored owing to too much past variability. They may be foreground objects which are often illuminated by car headlights, for example. Only white pixels are ignored; different shades of grey indicate how much each pixel has varied in the past."],
            "pigazing:triggers/event/mapExcludedPixels" => null,
            "pigazing:triggers/event/mapDifference/lensCorr" => ["Difference frame", "This frame indicates why the camera thought this object was interesting. It shows the difference between the video frame where the object appeared and the one before. White areas have brightened; dark areas have darkened."],
            "pigazing:triggers/event/mapDifference" => null,
            "pigazing:triggers/event" => ["Video of object", "This is a video of the object which triggered the camera"],
            "pigazing:timelapse/frame/skyBackground/lensCorr" => ["Light pollution map","This is an image of the light pollution that we believe to be present in this image, compiled from observations over the previous 20 minutes. It is subtracted from the observed image to see faint objects."],
            "pigazing:timelapse/frame/skyBackground" => null,
            "pigazing:timelapse/frame/lensCorr" => ["Lens-corrected image","This image has had lens distortions corrected."],
            "pigazing:timelapse/frame/bgrdSub/lensCorr" => ["Image with light pollution removed", "This image has been processed to attempt to remove light pollution."],
            "pigazing:timelapse/frame/bgrdSub" => null,
            "pigazing:timelapse/frame" => ["Original image", "This is the original image recorded by the camera, with no post-processing."],
            "pigazing:path" => ["Path of object across frame", "This file contains a list of positions within the frame where the object was detected, together with the time of sighting at each position"],
            "pigazing:logfile" => ["Internal observatory log file", "This log file contains internal reporting from the observatory to allow us to check its health"],
            "logging" => ["Internal observatory log file", "This log file contains internal reporting from the observatory to allow us to check its health"]
        ];

        // Known metadata fields
        $this->metadataFields = [
            "instName" => "Institution name",
            "instURL" => "Institution web address",
            "latitude" => "Latitude north of equator (deg)",
            "lens" => "Lens model",
            "lens_barrel_a" => "Barrel distortion (A)",
            "lens_barrel_b" => "Barrel distortion (B)",
            "lens_barrel_c" => "Barrel distortion (C)",
            "lens_fov" => "Field of view (deg)",
            "location_source" => "Location determined from",
            "longitude" => "Longitude east of Greenwich (deg)",
            "pigazing:amplitudePeak" => "Peak brightness of object",
            "pigazing:amplitudeTimeIntegrated" => "Time-integrated brightness of object",
            "pigazing:cameraId" => "Observatory ID",
            "pigazing:detectionCount" => "Number of frames",
            "pigazing:duration" => "Duration of object's appearance (sec)",
            "pigazing:highlight" => "Image highlighted",
            "pigazing:inputNoiseLevel" => "Noise level of input frames (0-255)",
            "pigazing:path" => "Path of object",
            "pigazing:pathBezier" => "Path of object",
            "pigazing:skyClarity" => "Sky clarity estimate (0-100)",
            "pigazing:stackedFrames" => "Number of frames averaged",
            "pigazing:stackNoiseLevel" => "Noise level (0-255)",
            "pigazing:sunAlt" => "Altitude of Sun (sec)",
            "pigazing:sunAz" => "Azimuth of Sun (sec)",
            "pigazing:sunDecl" => "Declination of Sun (deg)",
            "pigazing:sunRA" => "Right Ascension of Sun (hr)",
            "camera" => "Camera model",
            "camera_type" => "Camera interface type",
            "camera_fps" => "Camera frame rate per sec",
            "camera_height" => "Camera pixel height",
            "sensor_upside_down" => "Camera mounted upside-down",
            "sensor_width" => "Camera pixel width",
            "softwareVersion" => "Software version"
        ];
    }
}

$const = new constants();
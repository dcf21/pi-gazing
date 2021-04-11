<?php

// constants.php
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
        $this->yearMin = 2019;
        $this->yearMax = date("Y");

        // Path to PHP modules directory
        $this->path = realpath(dirname(__FILE__));
        $this->datapath = $this->path . "/../../../../datadir/db_filestore/";

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
        $this->item_categories = ["Not set", "Bird", "Plane", "Satellite", "Meteor", "Junk", "Pretty sky", "Bin"];

        // Known mime types
        $this->mimeTypes = ["image/png" => "Image",
            "video/mp4" => "Video",
            "application/json" => "Data file",
            "text/plain" => "Text file"
        ];

        // Known semantic types
        $this->semanticTypes = [
            "pigazing:timelapse/" => ["Still photograph", "A long exposure image"],
            "pigazing:movingObject/" => ["Moving object", "An object moving across the sky"],
            "pigazing:movingObject/triggerFrame" => ["Initial appearance", "This image shows the first video frame in which the moving object was detected."],
            "pigazing:movingObject/timeAverage" => ["Long exposure", "This shows a long exposure of the sky, taken over the entire duration that the moving object was visible."],
            "pigazing:movingObject/previousFrame" => ["Previous frame", "This image shows what the sky looked like immediately before the object appeared."],
            "pigazing:movingObject/maximumBrightness" => ["Maximum brightness", "This image shows the maximum brightness of each part of the image over the course of the object's appearance. This is usually the image that shows the object most clearly."],
            "pigazing:movingObject/allTriggers" => ["All trigger pixels", "A map of all the pixels which triggered the camera's motion sensor over the duration of the object's appearance."],
            "pigazing:movingObject/mapTrigger" => ["Trigger map", "This map indicates why the camera thought this object was interesting. Grey spots indicate areas which had recently brightened by an unusual amount. White spots indicate areas large enough to trigger the camera's motion sensor."],
            "pigazing:movingObject/mapExcludedPixels" => ["Excluded pixels", "This is a map of pixels within the frame which were being ignored owing to too much past variability. They may be foreground objects which are often illuminated by car headlights, for example. Only white pixels are ignored; different shades of grey indicate how much each pixel has varied in the past."],
            "pigazing:movingObject/mapDifference" => ["Difference frame", "This frame indicates why the camera thought this object was interesting. It shows the difference between the video frame where the object appeared and the one before. White areas have brightened; dark areas have darkened."],
            "pigazing:movingObject/video" => ["Video of object", "This is a video of the object which triggered the camera"],
            "pigazing:timelapse/backgroundModel" => ["Light pollution map", "This is an image of the light pollution that we believe to be present in this image, compiled from observations over the previous 20 minutes. It is subtracted from the observed image to see faint objects."],
            "pigazing:timelapse/backgroundSubtracted" => ["Image with light pollution removed", "This image has been processed to attempt to remove light pollution."],
            "pigazing:timelapse" => ["Original image", "This is the original image recorded by the camera, with no post-processing."],
            "pigazing:path" => ["Path of object across frame", "This file contains a list of positions within the frame where the object was detected, together with the time of sighting at each position"],
            "pigazing:logfile" => ["Internal observatory log file", "This log file contains internal reporting from the observatory to allow us to check its health"],
            "logging" => ["Internal observatory log file", "This log file contains internal reporting from the observatory to allow us to check its health"]
        ];

        // Known metadata fields
        $this->metadataFields = [
            "altitude_gps" => "Altitude (from GPS; m)",
            "calibration:lens_barrel_parameters" => "Lens calibration: Radial distortion parameters",
            "calibration:chi_squared" => "Lens calibration: Fitting error",
            "calibration:point_count" => "Lens calibration: Histogram of points used in matching",
            "camera" => "Camera model",
            "camera_type" => "Camera interface type",
            "camera_fps" => "Camera frame rate per sec",
            "camera_height" => "Camera pixel height",
            "camera_upside_down" => "Camera mounted upside-down",
            "camera_width" => "Camera pixel width",
            "clipping_region" => "Sky clipping region",
            "frame_drop:list" => "Frame drop incidents",
            "hardware_version" => "Observatory hardware",
            "instName" => "Institution name",
            "instURL" => "Institution web address",
            "latitude" => "Latitude north of equator (deg)",
            "latitude_gps" => "Latitude north of equator (from GPS; deg)",
            "lens" => "Lens model",
            "lens_fov" => "Estimated field of view (deg)",
            "location_source" => "Location determined from",
            "longitude" => "Longitude east of Greenwich (deg)",
            "longitude_gps" => "Longitude east of Greenwich (from GPS; deg)",
            "obstory_name" => "Observatory name",
            "orientation:altitude" => "Orientation: Altitude above horizon (deg)",
            "orientation:azimuth" => "Orientation: Azimuth east of north (deg)",
            "orientation:dec" => "Orientation: Central dec (deg)",
            "orientation:fit_quality" => "Orientation: Fit quality",
            "orientation:fit_quality_to_daily" => "Orientation: Fit quality to daily average",
            "orientation:image_count" => "Orientation: Number of images used",
            "orientation:pa" => "Orientation: Positional angle of field (deg)",
            "orientation:ra" => "Orientation: Central RA (hr)",
            "orientation:tilt" => "Orientation: Tilt of camera, clockwise from vertical (deg)",
            "orientation:width_x_field" => "Orientation: Calculated horizontal FoV (deg)",
            "orientation:width_y_field" => "Orientation: Calculated vertical FoV (deg)",
            "orientation:uncertainty" => "Orientation: Uncertainty (deg)",
            "pigazing:amplitudePeak" => "Peak brightness of object",
            "pigazing:amplitudeTimeIntegrated" => "Time-integrated brightness of object",
            "pigazing:detectionCount" => "Number of motion sensor detections",
            "pigazing:detectionSignificance" => "Detection significance",
            "pigazing:duration" => "Duration of object's appearance (sec)",
            "pigazing:gainFactor" => "Multiplicative gain applied to image",
            "pigazing:height" => "Height of frame",
            "pigazing:inputNoiseLevel" => "Noise level of input frames (0-255)",
            "pigazing:meanLevel" => "Average pixel brightness (0-255)",
            "pigazing:obstoryId" => "Observatory ID",
            "pigazing:path" => "Path of object",
            "pigazing:pathBezier" => "Path of object",
            "pigazing:semanticType" => "Pi-gazing type",
            "pigazing:skyClarity" => "Sky clarity estimate",
            "pigazing:stackedFrames" => "Number of frames spanned",
            "pigazing:stackNoiseLevel" => "Noise level of stacked image (0-255)",
            "pigazing:sunAlt" => "Altitude of Sun (sec)",
            "pigazing:sunAz" => "Azimuth of Sun (sec)",
            "pigazing:sunDecl" => "Declination of Sun (deg)",
            "pigazing:sunRA" => "Right ascension of Sun (hr)",
            "pigazing:utc" => "Unix timestamp",
            "pigazing:width" => "Width of frame",
            "pigazing:videoDuration" => "Video duration",
            "pigazing:videoFPS" => "Video frames/second",
            "pigazing:videoStart" => "Video start time",
            "satellite:angular_offset" => "Satellite: Angular mismatch (deg)",
            "satellite:clock_offset" => "Satellite: Ephemeris clock offset (sec)",
            "satellite:name" => "Satellite: Name",
            "satellite:norad_id" => "Satellite: Number",
            "satellite:path_length" => "Satellite: Track length (deg)",
            "satellite:path_ra_dec" => "Satellite: Path (RA, Dec)",
            "shower:name" => "Meteor: parent shower",
            "shower:path_length" => "Meteor: Track length (deg)",
            "shower:path_ra_dec" => "Meteor: Path (RA, Dec)",
            "shower:radiant_offset" => "Meteor: Angular offset from radiant (deg)",
            "software_version" => "Pi Gazing: Software version",
            "triangulation:max_angular_offset" => "Triangulation: Error (deg)",
            "triangulation:max_baseline" => "Triangulation: Max baseline (m)",
            "triangulation:mean_altitude" => "Triangulation: Altitude (m)",
            "triangulation:path" => "Triangulation: Path",
            "triangulation:radiant_direction" => "Triangulation: Radiant direction (RA, Dec)",
            "triangulation:sight_line_count" => "Triangulation: Sight line count",
            "triangulation:speed" => "Triangulation: Speed (m/s)",
            "web:category" => "Identification: Object type"
        ];
    }
}

$const = new constants();

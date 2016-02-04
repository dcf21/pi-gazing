<?php

// constants.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

$php_path = realpath(dirname(__FILE__));

require_once $php_path . "/utils.php";

class constants
{
    public $path, $server, $server_json;

    public function __construct()
    {
        $this->server = "/";
        $this->server_json = "/";
        $this->yearMin = 2015;
        $this->yearMax = date("Y");

        // Path to PHP modules directory
        $this->path = realpath(dirname(__FILE__));

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
        $this->mysqlLogin = "meteorpi";
        $this->mysqlHost = "localhost";
        $this->mysqlUser = "meteorpi";
        $this->mysqlPassword = "meteorpi";
        $this->mysqlDB = "meteorpi";

        // Connect to database
        $this->db = new PDO("mysql:host=" . $this->mysqlHost . ";dbname=" . $this->mysqlDB, $this->mysqlUser,
            $this->mysqlPassword) or die ("Can't connect to SQL database.");
        $this->db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    }
}

$const = new constants();

<?php

// local_mods.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

// User this to make local modifications, e.g. adding Google Analytics code

class local_mods
{
    // This function returns a dictionary of settings that effect the headers of each page
    // You can disable the import of the Google Maps JS files if you don't have a valid API key
    // or you can insert your own API key here
    public static function get_settings()
    {
        return [
            "googleAPIKey" => "AIzaSyCuMsPQjaWPZK8c9Sskll0y5Utd0Oq5cxA",
            "includeGoogleMaps" => true
        ];
    }

    // Use this function to add arbitrary code to the headers of every page of the Meteor Pi observatory website
    // For example, you might want to add Google Analytics code here
    public static function extra_headers()
    {
        ?>

        <?php
    }
}

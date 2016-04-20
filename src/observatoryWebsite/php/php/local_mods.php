<?php

// local_mods.php
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

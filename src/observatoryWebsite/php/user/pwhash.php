<?php

// pwhash.php
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

$php_path = realpath(dirname(__FILE__)) . "/../php";
require_once $php_path . "/imports.php";
require_once $php_path . "/html_getargs.php";
require_once $php_path . "/user.php";

$pageInfo = [
    "pageTitle" => "Password hash tool",
    "pageDescription" => "Meteor Pi",
    "activeTab" => "resources",
    "breadcrumb" => [["user/login.php", "Your account"]],
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => []
];

$pageTemplate->header($pageInfo);

$pwhash = "&ndash;";
if (isset($_POST['pw'])) $pwhash = password_hash($_POST['pw'],PASSWORD_DEFAULT);

?>

    <p class="widetitle">Password hash tool</p>

    <p class="newsbody">Password hash:<br/><?php echo $pwhash; ?></p>

    <div class="newsbody">
        <form method="post" action="/user/pwhash.php">
            <table style="margin-left:70px;">
                <tr>
                    <td class="gapcalitem" style="padding-bottom:0;"><span class="formlabel">Password</span></td>
                </tr>
                <tr>
                    <td>
                        <input style="width:350px;" class="txt" type="password" name="pw" id="pw" value=""/>
                    </td>
                </tr>
                <tr>
                    <td>
                        <span class="btn"><input class="btn" type="submit" value="Log in"/></span>
                    </td>
                </tr>
            </table>
        </form>

    </div>

<?php
$pageTemplate->footer($pageInfo);

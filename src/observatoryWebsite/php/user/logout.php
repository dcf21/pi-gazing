<?php

// logout.php
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
    "pageTitle" => "Log out from Meteor Pi",
    "pageDescription" => "Meteor Pi",
    "activeTab" => "resources",
    "breadcrumb" => [["user/login.php", "Log in"]],
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => []
];

$user->logOut();

$pageTemplate->header($pageInfo);

?>

<?php if (!is_null($user->username)): ?>

    <p class="widetitle">Goodbye, <?php echo $user->username; ?></p>

    <div class="newsbody">

        You have been successfully logged out. Click here to <a href="/user/login.php">log in</a> again.

    </div>

<?php else: ?>

    <p class="widetitle">Log out</p>

    <div class="newsbody">

        You are already logged out.

    </div>
<?php endif; ?>

<?php
$pageTemplate->footer($pageInfo);

<?php

// userlist.php
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

$cssextra = <<<__HTML__
<style media="screen" type="text/css">
.scrolltable td:nth-child(   1) { min-width:150px; max-width:150px; }
.scrolltable td:nth-child(   2) { min-width:150px; max-width:150px; }
.scrolltable td:nth-child(   3) { min-width:150px; max-width:150px; }
.scrolltable td:nth-child(   4) { min-width:150px; max-width:150px; }
</style>
__HTML__;

$pageInfo = [
    "pageTitle" => "List of user accounts",
    "pageDescription" => "Meteor Pi",
    "activeTab" => "resources",
    "breadcrumb" => [["user/login.php", "Your account"]],
    "teaserImg" => null,
    "cssextra" => $cssextra,
    "includes" => [],
    "linkRSS" => null,
    "options" => []
];

$pageTemplate->header($pageInfo);

?>

<?php if (in_array("obstory_admin",$user->roles)): ?>

    <p>The following users are registered on this server:</p>

    <?php
    $stmt = $const->db->prepare("
SELECT u.userId,
(SELECT lastSeen FROM archive_user_sessions s WHERE s.userId=u.uid ORDER BY lastSeen DESC LIMIT 1) AS lastSeen
FROM archive_users u ORDER BY u.userId LIMIT 500;");
    $stmt->execute();
    $user_list = $stmt->fetchAll(PDO::FETCH_ASSOC);
    if (count($user_list) > 0):
        ?>
        <div class="scrolltable">
        <div class="scrolltable_thead">
            <table class="stripy bordered">
                <?php ob_start(); ?>
                <thead>
                <tr>
                    <td>Username</td>
                    <td>Last Seen</td>
                </tr>
                </thead>
                <?php $scrolltable_thead = ob_get_contents();
                ob_end_clean();
                echo $scrolltable_thead; ?>
            </table>
        </div>
        <div class="scrolltable_tbody">
            <table class="stripy bordered bordered2">
                <?php echo $scrolltable_thead; ?>
                <tbody>
                <?php foreach ($user_list as $item): ?>
                    <tr>
                        <td><?php echo $item['userId']; ?></td>
                        <td><?php echo $item['lastSeen'] ? date("d M Y H:i", $item['lastSeen']) : "Never"; ?></td>
                    </tr>
                <?php endforeach; ?>
                </tbody>
            </table>
        </div>
        </div>
    <?php else: ?>
        <div class="newsbody">
            <i>None</i>
        </div>
    <?php endif; ?>

<?php else: ?>

    <p>Access denied</p>

<?php endif; ?>

<?php
$pageTemplate->footer($pageInfo);

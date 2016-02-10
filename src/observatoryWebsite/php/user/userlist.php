<?php

// userlist.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

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

    <p class="widetitle">List of user accounts</p>

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

<?php

// activity.php
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
    "pageTitle" => "Activity history",
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

    <p class="widetitle">Recent site activity</p>

    <div class="newsbody">
        <p>
            Recent activity:
        </p>
    </div>

    <?php
    $stmt = $const->db->prepare("
SELECT u.userId,s.logIn,s.logOut,s.ip FROM archive_user_sessions s
INNER JOIN archive_users u ON u.uid=s.userId
ORDER BY logIn LIMIT 10;");
    $stmt->execute();
    $activity = $stmt->fetchAll(PDO::FETCH_ASSOC);
    if (count($activity) > 0):
        ?>
        <div class="scrolltable">
        <div class="scrolltable_thead">
            <table class="stripy bordered">
                <?php ob_start(); ?>
                <thead>
                <tr>
                    <td>Username</td>
                    <td>Log in</td>
                    <td>Log off</td>
                    <td>IP address</td>
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
                <?php foreach ($activity as $item): ?>
                    <tr>
                        <td><?php echo $item['userId']; ?></td>
                        <td><?php echo date("d M Y H:i", $item['logIn']); ?></td>
                        <td><?php echo $item['logOut'] ? date("d M Y H:i", $item['logOut']) : "Still logged in"; ?></td>
                        <td><?php printf("%d.%d.%d.%d", ($item['ip'] / 256 / 256 / 256) & 255,
                                ($item['ip'] / 256 / 256) & 255, ($item['ip'] / 256) % 256, ($item['ip']) & 255); ?>
                        </td>
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

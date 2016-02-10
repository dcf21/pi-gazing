<?php

// logout.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

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

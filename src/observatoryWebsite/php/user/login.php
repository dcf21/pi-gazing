<?php

// login.php
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

if (is_null($user->username))
{
    $pageTitle = "Log in to Meteor Pi control panel";
}
else
{
    $pageTitle = "Your Meteor Pi account";
}

$pageInfo = [
    "pageTitle" => $pageTitle,
    "pageDescription" => "Meteor Pi",
    "activeTab" => "resources",
    "breadcrumb" => [["user/login.php", "Log in"]],
    "teaserImg" => null,
    "cssextra" => $cssextra,
    "includes" => [],
    "linkRSS" => null,
    "options" => []
];

$pageTemplate->header($pageInfo);

?>

<?php if (!is_null($user->username)): ?>

    <div class="alert alert-success">
    Welcome, <?php echo $user->username; ?>
    </div>

    <div class="newsbody">
        <p>
            Click here to <a href="/user/logout.php">log out</a>.
        </p>
        <?php if (in_array("obstory_admin", $user->roles)): ?>
            <p>
                Administration links:<br/>
                <a href="activity.php">Recent activity</a><br/>
                <a href="userlist.php">List of users</a><br/>
            </p>
        <?php endif; ?>
        <p>
            Your recent activity:
        </p>
    </div>

    <?php
    $stmt = $const->db->prepare("SELECT * FROM archive_user_sessions WHERE userId=:u ORDER BY logIn LIMIT 10;");
    $stmt->bindParam(':u', $u, PDO::PARAM_INT);
    $stmt->execute(['u' => $user->userId]);
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
                        <td><?php echo $user->username; ?></td>
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

    <?php if ($user->refused): ?>

        <div class="alert alert-danger">
            Incorrect username or password.
        </div>

    <?php endif; ?>

    <div class="newsbody">
        <form method="post" action="/user/login.php">
            <table style="margin-left:70px;">
                <tr>
                    <td class="gapcalitem" style="padding-bottom:0;"><span class="formlabel">Username</span></td>
                </tr>
                <tr>
                    <td>
                        <input style="width:350px;" class="txt" type="text" name="un" id="un" value=""/>
                    </td>
                </tr>
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
<?php endif; ?>

<?php
$pageTemplate->footer($pageInfo);

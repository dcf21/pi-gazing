<?php

// observatory_metadata.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

require_once "php/imports.php";
require_once "php/html_getargs.php";

$getargs = new html_getargs();

// Read which month to cover
$tmin = $getargs->readTime('year', 'month', null, null, null, null, $const->yearMin, $const->yearMax);

$days_in_month = date('t', $tmin['utc']);
$day_offset = date('w', $tmin['utc']);
$period = 24 * 3600;

$obstories = $getargs->obstory_objlist;
$obstory = $getargs->readObservatory("id");
$obstory_name = $getargs->obstory_objs[$obstory]['name'];

$byday = [];

// Fetch observatory activity history
function get_activity_history($metaKey, $suffix)
{
    global $byday, $const, $tmin, $period, $obstory, $days_in_month;
    $count = 0;
    while ($count < $days_in_month) {
        $a = $tmin['utc'] + $period * $count;
        $b = $a + $period;
        $count++;
        $stmt = $const->db->prepare("
SELECT COUNT(*) FROM archive_observations o
INNER JOIN archive_observatories l ON o.observatory = l.uid
INNER JOIN archive_semanticTypes s ON o.obsType = s.uid
WHERE l.publicId=:o AND s.name=:k AND o.obsTime>=:x AND o.obsTime<:y LIMIT 1");
        $stmt->bindParam(':o', $o, PDO::PARAM_STR, strlen($obstory));
        $stmt->bindParam(':k', $k, PDO::PARAM_STR, strlen($metaKey));
        $stmt->bindParam(':x', $x, PDO::PARAM_INT);
        $stmt->bindParam(':y', $y, PDO::PARAM_INT);
        $stmt->execute(['o' => $obstory, 'k' => $metaKey, 'x' => $a, 'y' => $b]);
        $items = $stmt->fetchAll()[0]['COUNT(*)'];
        if ($items > 0)
         {
          $text = "<span class='cal_number'>{$items}</span><span class='cal_type'>{$suffix}</span>";
         }
        else
         {
          $text = "";
         }
        $byday[$count][] = $text;
    }
}

get_activity_history("timelapse", " still images");
get_activity_history("movingObject", " moving objects");

$pageInfo = [
    "pageTitle" => "Observatory {$obstory_name}: Activity history",
    "pageDescription" => "Meteor Pi",
    "activeTab" => "cameras",
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => [],
    "breadcrumb" => [["observatory.php?id=" . $obstory, $obstory_name]]
];


$pageTemplate->header($pageInfo);

?>
    <div class="row">
        <div class="col-md-10">

            <div style="padding:4px;overflow-x:scroll;">
                <table class="dcf_calendar">
                    <thead>
                    <tr>
                        <td>
                            <?php
                            print implode("</td><td>", ['Sun', 'Mon', 'Tue', 'Wed', 'Thur', 'Fri', 'Sat']);
                            ?>
                        </td>
                    </tr>
                    </thead>
                    <tbody>
                    <tr>

                        <?php
                        for ($i = 0; $i < $day_offset; $i++)
                        {
                            print "<td class='even'></td>";
                        }

                        $nowutc = time();
                        $nowyear = intval(date("Y", $nowutc));
                        $nowmc = intval(date("n", $nowutc));
                        $nowday = intval(date("j", $nowutc));
                        for ($day = 1; $day <= $days_in_month; $day++) {
                            print "<td class='odd'>";
                            print "<div class=\"cal_day\">${day}</div><div class=\"cal_body\">";
                            $all_blank = true;
                            $output = "";
                            foreach ($byday[$day] as $s) {
                                if (strlen($s)>0) $all_blank = false;
                                $output.="<div style='height:55px;'>{$s}</div>";
                            }
                            if ($all_blank) $output = "<div style='height:55px;'><span class='cal_type'>No data</span></div>";
                            print "{$output}</div></td>";
                            $day_offset++;
                            if ($day_offset == 7) {
                                $day_offset = 0;
                                print "</tr>";
                                if ($day < $days_in_month) print"<tr>";
                            }
                        }

                        if ($day_offset > 0) {
                            for ($day = $day_offset; $day < 7; $day++)
                            {
                                print "<td class='even'></td>";
                            }
                            print "</tr>";
                        }

                        ?>
                    </tbody>
                </table>
            </div>

        </div>

        <div class="col-md-2">
            <h4>Select month</h4>
            <form method="get" action="/observatory_activity.php">
                <input type="hidden" name="id" value="<?php echo $obstory; ?>">
                <?php
                html_getargs::makeFormSelect("month", $tmin['mc'], $getargs->months, 0);
                html_getargs::makeFormSelect("year", $tmin['year'], range($const->yearMin, $const->yearMax), 0);
                ?>
                <br/>
                <input type="submit" name="Update" value="Update">
            </form>

            <div style="padding-top:25px;">
                <?php
                $pageTemplate->listObstories($obstories,
                    "/observatory_activity.php?year={$tmin['year']}&month={$tmin['mc']}&id=");
                ?>
            </div>

        </div>
    </div>

<?php
$pageTemplate->footer($pageInfo);


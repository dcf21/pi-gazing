<?php

// search_aircraft.php
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2015-2021 Dominic Ford.

// This file is part of Pi Gazing.

// Pi Gazing is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Pi Gazing is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Pi Gazing.  If not, see <http://www.gnu.org/licenses/>.
// -------------------------------------------------

require "php/imports.php";
require_once "php/html_getargs.php";

$getargs = new html_getargs(true);

// Limit the width of drop-down menus
$cssextra = <<<__HTML__
<style media="screen" type="text/css">
td { max-width: 200px; vertical-align: middle; }
</style>
__HTML__;

$pageInfo = [
    "pageTitle" => "Search for aircraft sightings",
    "pageDescription" => "Pi Gazing",
    "fluid" => true,
    "activeTab" => "search",
    "teaserImg" => null,
    "cssextra" => $cssextra,
    "includes" => [],
    "linkRSS" => null,
    "options" => []
];

// Read which time range to cover
$t2 = time();
$t1 = $t2 - 3600 * 24 * 365;
$tmin = $getargs->readTime('year1', 'month1', 'day1', 'hour1', 'min1', null, $const->yearMin, $const->yearMax, $t1);
$tmax = $getargs->readTime('year2', 'month2', 'day2', 'hour2', 'min2', null, $const->yearMin, $const->yearMax, $t2);

// Read switch for showing unidentified objects
$flag_include_unidentified = 0;
if (array_key_exists("show_all", $_GET)) $flag_include_unidentified = 1;

// Which observatory are we searching for images from?
$obstory = $getargs->readObservatory("obstory");

// Swap times if they are the wrong way round
if ($tmax['utc'] < $tmin['utc']) {
    $tmp = $tmax;
    $tmax = $tmin;
    $tmin = $tmp;
}

$pageTemplate->header($pageInfo);

?>

    <div class="non-fluid-block">
        <p>
            Use this form to search for aircraft spotted by our cameras.
        </p>
        <form class="form-horizontal search-form" method="get" action="/search_aircraft.php#results">

            <div style="cursor:pointer;text-align:right;">
                <button type="button" class="btn btn-secondary help-toggle">
                    <i class="fa fa-info-circle" aria-hidden="true"></i>
                    Show tips
                </button>
            </div>
            <div class="row">
                <div class="search-form-column col-lg-6">

                    <div><span class="formlabel">Time of observation</span></div>
                    <div class="tooltip-holder">
                        <span class="formlabel2">Between</span>

                        <div class="form-group-dcf"
                             data-toggle="tooltip" data-pos="tooltip-above"
                             title="Search for images recorded after this date and time."
                        >
                        <span style="display:inline-block; padding-right:20px;">
                        <?php
                        $getargs->makeFormSelect("day1", $tmin['day'], range(1, 31), 0);
                        $getargs->makeFormSelect("month1", $tmin['mc'], $getargs->months, 0);
                        ?>
                        <input name="year1" class="year" style="max-width:80px;"
                               type="number" step="1"
                               min="<?php echo $const->yearMin; ?>" max="<?php echo $const->yearMax; ?>"
                               value="<?php echo $tmin['year']; ?>"/>
                        <?php
                        print "</span><span>";
                        $getargs->makeFormSelect("hour1", $tmin['hour'], $getargs->hours, 0);
                        print "&nbsp;<b>:</b>&nbsp;";
                        $getargs->makeFormSelect("min1", $tmin['min'], $getargs->mins, 0);
                        ?>
                        </span>
                        </div>
                    </div>

                    <div class="tooltip-holder">
                        <span class="formlabel2">and</span>

                        <div class="form-group-dcf"
                             data-toggle="tooltip" data-pos="tooltip-below"
                             title="Search for images recorded before this date and time."
                        >
                        <span style="display:inline-block; padding-right:20px;">
                        <?php
                        $getargs->makeFormSelect("day2", $tmax['day'], range(1, 31), 0);
                        $getargs->makeFormSelect("month2", $tmax['mc'], $getargs->months, 0);
                        ?>
                        <input name="year2" class="year" style="max-width:80px;"
                               type="number" step="1"
                               min="<?php echo $const->yearMin; ?>" max="<?php echo $const->yearMax; ?>"
                               value="<?php echo $tmax['year']; ?>"/>
                        <?php
                        print "</span><span>";
                        $getargs->makeFormSelect("hour2", $tmax['hour'], $getargs->hours, 0);
                        print "&nbsp;<b>:</b>&nbsp;";
                        $getargs->makeFormSelect("min2", $tmax['min'], $getargs->mins, 0);
                        ?>
                        </span>
                        </div>
                    </div>

                    <div style="margin-top:25px;"><span class="formlabel">Observed by camera</span></div>
                    <div class="tooltip-holder">
                        <span class="formlabel2"></span>

                        <div class="form-group-dcf"
                             data-toggle="tooltip" data-pos="tooltip-below"
                             title="Use this to display images from only one camera in the Pi Gazing network. Set to 'Any' to display images from all Pi Gazing cameras."
                        >
                            <?php
                            $getargs->makeFormSelect("obstory", $obstory, $getargs->obstories, 1);
                            ?>
                        </div>
                    </div>

                </div>
                <div class="search-form-column col-lg-6">
                    <div><span class="formlabel">Search options</span></div>

                    <div class="tooltip-holder" style="display:inline-block;">
                        <div class="checkbox" data-toggle="tooltip" data-pos="tooltip-top"
                             title="Include unidentified aircraft.">
                            <label>
                                <input type="checkbox" name="show_all"
                                    <?php if ($flag_include_unidentified) echo 'checked="checked"'; ?> >
                                Include unidentified aircraft
                            </label>
                        </div>
                    </div>
                </div>

            </div>

            <div style="padding:30px 0 40px 0;">
                <span class="formlabel2"></span>
                <button type="submit" class="btn btn-primary" data-bind="click: performSearch">Search</button>
            </div>

        </form>
    </div>

    <div id="results"></div>

<?php

// Display results if and only if we are searching
$searching = true;
if ($searching) {

    // Search for results
    $where = ["o.obsTime BETWEEN {$tmin['utc']} AND {$tmax['utc']}"];

    if ($obstory != "Any") {
        $where[] = 'l.publicId="' . $obstory . '"';
    }

    if (!$flag_include_unidentified) {
        $where[] = 'd4.stringValue IS NOT NULL AND d4.stringValue != "Unidentified"';
    }

    $search = ("
archive_observations o
INNER JOIN archive_observatories l ON o.observatory = l.uid
INNER JOIN archive_metadata d ON o.uid = d.observationId AND
    d.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey=\"pigazing:duration\")
LEFT OUTER JOIN archive_metadata d2 ON o.uid = d2.observationId AND
    d2.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey=\"plane:angular_offset\")
LEFT OUTER JOIN archive_metadata d3 ON o.uid = d3.observationId AND
    d3.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey=\"plane:clock_offset\")
LEFT OUTER JOIN archive_metadata d4 ON o.uid = d4.observationId AND
    d4.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey=\"plane:call_sign\")
LEFT OUTER JOIN archive_metadata d6 ON o.uid = d6.observationId AND
    d6.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey=\"plane:hex_ident\")
LEFT OUTER JOIN archive_metadata d7 ON o.uid = d7.observationId AND
    d7.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey=\"plane:operator\")
LEFT OUTER JOIN archive_metadata d8 ON o.uid = d8.observationId AND
    d8.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey=\"plane:manufacturer\")
LEFT OUTER JOIN archive_metadata d9 ON o.uid = d9.observationId AND
    d9.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey=\"plane:model\")
LEFT OUTER JOIN archive_metadata d5 ON o.uid = d5.observationId AND
    d5.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey=\"web:category\")
WHERE o.obsType = (SELECT uid FROM archive_semanticTypes WHERE name=\"pigazing:movingObject/\")
      AND d5.stringValue='Plane'
      AND " . implode(' AND ', $where));

    $stmt = $const->db->prepare("
SELECT o.publicId AS observationId, o.obsTime, l.publicId AS obstoryId, l.name AS obstoryName,
       d.floatValue AS duration, d2.floatValue AS ang_offset, d3.floatValue AS clock_offset,
       d4.stringValue AS call_sign, d6.stringValue AS hex_ident, d7.stringValue AS operator,
       d8.stringValue AS manufacturer, d9.stringValue AS model
FROM ${search} ORDER BY o.obsTime DESC;");
    $stmt->execute([]);
    $result_list = $stmt->fetchAll();

    // Display result counter
    $result_count = count($result_list);
    if ($result_count == 0):
        ?>
        <div class="alert alert-success">
            <p><b>No results found</b></p>

            <p>
                The query completed, but no events were found matching the constraints you specified. Try altering
                values in the form above and re-running the query.
            </p>
        </div>
    <?php
    else:
        ?>
        <div class="alert alert-success">
            <p>Showing <?php echo $result_count; ?> results.</p>
        </div>
        <?php

        // Display results table
        ?>
        <table class="stripy stripy2 bordered bordered_slim" style="margin:8px auto;">
            <thead>
            <tr>
                <td>Time</td>
                <td>Observatory</td>
                <td>Duration<br/>(sec)</td>
                <td>Call sign</td>
                <td>Hex ident</td>
                <td>Operator</td>
                <td>Manufacturer</td>
                <td>Model</td>
                <td>Angular<br/>mismatch<br/>(deg)</td>
                <td>Time<br/>mismatch<br/>(sec)</td>
            </tr>
            </thead>
            <tbody>
            <?php
            foreach ($result_list as $item) {
                print "<tr>";
                print "<td>";
                print "<a href='/moving_obj.php?id={$item['observationId']}'>";
                print date("d M Y", $item['obsTime']);
                print "&nbsp;&nbsp;&nbsp;";
                print date("H:i:s", $item['obsTime']);
                print "</a>";
                print "</td>";
                print "<td>{$item['obstoryName']}</td>";
                printf("<td style='text-align: right;'>%.1f</td>", $item['duration']);
                if ($item['call_sign'] && ($item['call_sign'] != "Unidentified")) {
                    print "<td>{$item['call_sign']}</td>";
                    print "<td>{$item['hex_ident']}</td>";
                    print "<td>{$item['operator']}</td>";
                    print "<td>{$item['manufacturer']}</td>";
                    print "<td>{$item['model']}</td>";
                    printf("<td style='text-align: right;'>%.1f</td>", $item['ang_offset']);
                    printf("<td style='text-align: right;'>%.1f</td>", $item['clock_offset']);
                } else {
                    print "<td style='text-align: center;'>&ndash;</td>";
                    print "<td style='text-align: center;'>&ndash;</td>";
                    print "<td style='text-align: center;'>&ndash;</td>";
                    print "<td style='text-align: center;'>&ndash;</td>";
                    print "<td style='text-align: center;'>&ndash;</td>";
                    print "<td style='text-align: center;'>&ndash;</td>";
                    print "<td style='text-align: center;'>&ndash;</td>";
                }
                print "</tr>\n";
            }

            ?>
            </tbody>
        </table>
    <?php
    endif;
}

// Page footer
$pageTemplate->footer($pageInfo);

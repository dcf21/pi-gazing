<?php

// whattodo.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

require "php/imports.php";

$pageInfo = [
    "pageTitle" => "What to do",
    "pageDescription" => "Meteor Pi",
    "activeTab" => "whattodo",
    "teaserImg" => null,
    "cssextra" => null,
    "includes" => [],
    "linkRSS" => null,
    "options" => []
];

$pageTemplate->header($pageInfo);

?>
    <h3>Getting started with Meteor Pi</h3>

    <div class="pane-sequence">
        <div class="row">
            <div class="col-md-9">
                <div style="padding:3px;">
                    <div class="grey_box" style="padding:16px;">
                        <div class="pane-item" data-title="Searching the sky">
                            <p class="text">
                                To search for images collected by Meteor Pi cameras, click on the "Search the Sky" tab
                                at the
                                top of this page.
                            </p>
                            <div class="pane-controls"></div>
                        </div>

                        <div class="pane-item" data-title="What can I see?">
                            <h3>Is it a bird... is it a plane?</h3>

                            <p class="text">
                                Not all the videos contain real moving objects. Sometimes the cameras trigger because of
                                twinkling stars or
                                video
                                artifacts.
                                Look through until you find a video that shows a moving object. The next challenge is to
                                work
                                out what it
                                is.
                                Meteor Pi cameras pick up large numbers of satellites and planes, as well as meteors.
                            </p>
                            <div class="pane-controls"></div>
                        </div>

                        <div class="pane-item" data-title="Spotting meteors">
                            <h4>Is it a meteor?</h4>

                            <p class="text">
                                Meteors are distinctive, because they move much more quickly than planes and satellites,
                                at
                                speeds of over
                                10
                                kilometres each second. They are
                                usually only visible for a fraction of a second as they burn up. To find more meteors,
                                you may
                                want change
                                the "Max
                                duration" field to one second and repeat your search.
                            </p>

                            <div class="rightimg">
                                <img style="width:450px;"
                                     src="https://meteorpi.cambridgesciencecentre.org/api/files/content/00eba2af11f5452cba1ee177c1cc4ebe/20151107213909_Bury-Allman_event_maxBrightness_LC1.png"/>
                                <p class="caption">An example image of a meteor, as it might appear when you search our
                                    website.<a
                                        href="https://meteorpi.cambridgesciencecentre.org/#file/%257B%2522camera_ids%2522%253A%2522Bury-St-Edmunds%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2522%252C%2522searchtype%2522%253A%2522Moving%2520objects%2522%252C%2522before%2522%253A1446932350000%252C%2522after%2522%253A1446932348000%257D">
                                        Click here to see a full video of the event.
                                    </a></p>
                            </div>
                            <div class="pane-controls"></div>
                        </div>

                        <div class="pane-item" data-title="Spotting planes">
                            <h4>Is it a plane?</h4>

                            <p class="text">
                                Planes are often easy to spot because they have flashing lights. They are usually
                                visible for
                                10-30 seconds,
                                whereas
                                meteors are gone in a fraction of a second. If you set the "Min duration" field to 10 or
                                20
                                seconds, most of
                                the
                                objects you'll see will be planes.
                            </p>

                            <div class="rightimg">
                                <img style="width:450px;"
                                     src="https://meteorpi.cambridgesciencecentre.org/api/files/content/00bcb31ce40e4b4ca2db1f25e73e22d1/20151109183940_Bury-Allman_event_maxBrightness_LC1.png"/>
                                <p class="caption">An example image of a plane, as it might appear when you search our
                                    website.<a
                                        href="https://meteorpi.cambridgesciencecentre.org/#file/%257B%2522camera_ids%2522%253A%2522Bury-St-Edmunds%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2522%252C%2522searchtype%2522%253A%2522Moving%2520objects%2522%252C%2522before%2522%253A1446932350000%252C%2522after%2522%253A1446932348000%257D">
                                        Click here to see a full video of the event.
                                    </a></p>
                            </div>
                            <div class="pane-controls"></div>
                        </div>

                        <div class="pane-item" data-title="Spotting satellites">
                            <h4>Is it satellite?</h4>

                            <p class="text">
                                Satellites, like planes, are visible for much longer than meteors &ndash; at least 10-30
                                seconds. They move
                                at a
                                steady speed and they don't have flashing lights.
                            </p>

                            <p class="text">
                                The flight paths of satellites are extremely predictable, and so if you think you've
                                found one,
                                you can try
                                looking
                                on a website like <a href="https://in-the-sky.org/satpasses.php">In-The-Sky.org</a> to
                                see if
                                you can track
                                down
                                which satellite it was.
                            </p>

                            <p class="text">
                                Alternatively, why not look up which satellites flew over the UK last night, and see if
                                any
                                Meteor Pi
                                cameras picked
                                them up?
                            </p>

                            <div class="rightimg">
                                <img style="width:450px;"
                                     src="https://meteorpi.cambridgesciencecentre.org/api/files/content/3f5568248f264477a4fec4f45f8dacda/20151010182540_Bury-Allman_event_maxBrightness_LC1.png"/>
                                <p class="caption">An example image of a satellite, as it might appear when you search
                                    our
                                    website.<a
                                        href="https://meteorpi.cambridgesciencecentre.org/#file/%257B%2522camera_ids%2522%253A%2522Bury-St-Edmunds%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2520%2522%252C%2522searchtype%2522%253A%2522Moving%2520objects%2522%252C%2522before%2522%253A1444501541000%252C%2522after%2522%253A1444501539000%257D">
                                        Click here to see a full video of the event.
                                    </a></p>
                            </div>
                            <div class="pane-controls"></div>
                        </div>

                        <div class="pane-item" data-title="Where next?">

                            <h3 style="clear:both;">What next?</h3>

                            <p class="text">
                                Once you've started looking at Meteor Pi images, you'll want to know what else you can
                                see!
                            </p>

                            <p class="text">
                                Why not take a look at <a href="/projects">our projects</a>, to see what else you can
                                see?
                            </p>
                            <div class="pane-controls"></div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div style="padding:3px;">
                    <div class="grey_box" style="padding:16px;">
                        <h4 style="padding-top:0;">Contents</h4>
                        <div class="pane-list"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

<?php
$pageTemplate->footer($pageInfo);

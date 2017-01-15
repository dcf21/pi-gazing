<?php

// html_template.php
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

require_once "constants.php";
require_once "user.php";
require_once "local_mods.php";

class HTMLtemplate
{
    public static function breadcrumb($items, $area, $postbreadcrumb = null)
    {
        global $const;
        $server = $const->server;
        if (is_null($items)) return;
        if ($area == "home") {
            return;
        } else if ($area == "whattodo") {
            array_unshift($items, ["whattodo.php", "Getting started"]);
        } else if ($area == "search") {
            array_unshift($items, ["search.php", "Search the sky"]);
        } else if ($area == "projects") {
            array_unshift($items, ["projects.php", "Projects"]);
        } else if ($area == "howitworks") {
            array_unshift($items, ["howitworks.php", "How it works"]);
        } else if ($area == "cameras") {
            array_unshift($items, ["map.php", "Cameras"]);
        } else if ($area == "faqs") {
            array_unshift($items, ["faqs.php", "FAQs"]);
        } else if ($area == "about") {
            array_unshift($items, ["about.php", "About"]);
        }
        array_unshift($items, ["", "Home"]);
        ?>
        <table style="margin-top:18px;">
            <tr>
                <td class="snugtop" style="white-space:nowrap;">
                    <p class="smtext" style="padding:12px 0 6px 0;">
                        <?php
                        $firstItem = true;
                        foreach ($items as $arg) {
                            print '<span class="chevron_holder">';
                            if (!$firstItem) print '<span class="chevronsep">&nbsp;</span>';
                            print "<a class='chevron' href='{$server}{$arg[0]}'>{$arg[1]}</a></span>";
                            $firstItem = false;
                        }
                        ?>
                    </p></td>
                <?php if ($postbreadcrumb): ?>
                    <td style="padding-left:20px;vertical-align:middle;">
                        <span class="postchevron">
<?php
$first = true;
foreach ($postbreadcrumb as $c) {
    $cname = str_replace(" ", "&nbsp;", htmlentities($c[1], ENT_QUOTES));
    if (!$first) {
        print "&nbsp;| ";
    } else {
        $first = false;
    }
    print "<a href=\"{$server}{$c[0]}\">" . $cname . "</a>";
}
?>
                        </span>
                    </td>
                <?php endif; ?>
            </tr>
        </table>
        <?php
    }

    public static function require_html5()
    {
        ?>
        <!--[if lt IE 9]>
        <p class="smtext" style="background-color:#a00;color:white;border:1px solid #222;margin:16px 4px;padding:8px;">
            <b>
                You appear to be using an old web browser which may not be compatible with the interactive elements of
                this website. This page is compatible with most modern web browsers, including Chrome, Firefox, Safari
                and Internet Explorer 9+, but not with older versions of Internet Explorer.
            </b>
        </p>
        <![endif]-->
        <?php
    }

    public static function header($pageInfo)
    {
        global $const, $user;
        if (!isset($pageInfo["breadcrumb"])) $pageInfo["breadcrumb"] = [];
        if (!isset($pageInfo["postbreadcrumb"])) $pageInfo["postbreadcrumb"] = null;
        $server = $const->server;
        $settings = local_mods::get_settings();
        print<<<__HTML__
<!DOCTYPE html>
<html lang="en">
__HTML__;
        ?>
        <head>
            <meta charset="utf-8">
            <meta name="description" content="<?php echo $pageInfo["pageDescription"]; ?>"/>
            <meta name="keywords"
                  content="shooting stars, meteors, camera, night sky"/>
            <meta name="generator" content="Dominic Ford"/>
            <meta name="author" content="Dominic Ford"/>
            <link rel="icon" type="image/png" href="/favicon-32x32.png" sizes="32x32">
            <link rel="icon" type="image/png" href="/favicon-194x194.png" sizes="194x194">
            <link rel="icon" type="image/png" href="/favicon-96x96.png" sizes="96x96">
            <link rel="icon" type="image/png" href="/favicon-16x16.png" sizes="16x16">
            <meta name="viewport" content="width=device-width, initial-scale=1">

            <title id="title1">
                <?php echo $pageInfo["pageTitle"]; ?>
            </title>

            <!--[if lt IE 9]>
            <script src="<?php echo $server; ?>vendor/html5shiv/dist/html5shiv.min.js" type="text/javascript"></script>
            <script src="<?php echo $server; ?>vendor/ExplorerCanvas/excanvas.js" type="text/javascript"></script>
            <![endif]-->

            <?php if ($settings['includeGoogleMaps']): ?>
                <script type="text/javascript"
                        src="//maps.googleapis.com/maps/api/js?key=<?php echo $settings['googleAPIKey']; ?>&amp;sensor=false">
                </script>
            <?php endif; ?>


            <script src="<?php echo $server; ?>vendor/jquery/dist/jquery.min.js" type="text/javascript"></script>
            <script src="<?php echo $server; ?>vendor/jquery-ui/jquery-ui.min.js" type="text/javascript"></script>
            <link rel="stylesheet" type="text/css"
                  href="<?php echo $server; ?>vendor/jquery-ui/themes/ui-darkness/jquery-ui.min.css"/>
            <style type="text/css">
                .ui-slider-horizontal .ui-state-default {
                    background: url(<?php echo $server; ?>/images/sliderarrow.png) no-repeat;
                    width: 9px;
                    height: 20px;
                    border: 0 none;
                    margin-left: -4px;
                }

                .ui-slider-vertical .ui-state-default {
                    background: url(<?php echo $server; ?>/images/slidervarrow.png) no-repeat;
                    width: 20px;
                    height: 9px;
                    border: 0 none;
                    margin-left: -4px;
                }
            </style>
            <link rel="stylesheet" href="<?php echo $server; ?>vendor/bootstrap/dist/css/bootstrap.min.css">
            <script src="<?php echo $server; ?>vendor/bootstrap/dist/js/bootstrap.min.js"></script>

            <link rel="stylesheet" href="<?php echo $server; ?>vendor/font-awesome/css/font-awesome.min.css">

            <link rel="stylesheet" type="text/css" href="<?php echo $server; ?>css/style.css" media="all"/>

            <script type="text/javascript" src="<?php echo $server; ?>js/meteorpi.min.js"></script>

            <?php if ($pageInfo["teaserImg"]): ?>
                <link rel="image_src" href="<?php echo $server . $pageInfo["teaserImg"]; ?>"
                      title="<?php echo $pageInfo["pageTitle"]; ?>"/>
                <meta property="og:image" content="<?php echo $server . $pageInfo["teaserImg"]; ?>"/>
            <?php endif; ?>

            <?php echo $pageInfo["cssextra"]; ?>
            <?php local_mods::extra_headers(); ?>
        </head>

        <?php echo "<body><div class=\"contentwrapper\">"; ?>

        <div class="bannerback">
            <div class="banner">
                <div class="banner_txt_right" id="top">
                    <p class="toptitleA"><a href="#">Meteor Pi</a></p>
                </div>
                <div id="bannerppl"></div>
                <div id="bannercsc"></div>
            </div>
            <div id="bannerfull"></div>
        </div>

        <nav id="navbar-header" class="navbar navbar-dark bg-inverse navbar-fixed-top">
            <div class="container-fluid">
                <button class="navbar-toggler hidden-md-up" type="button"
                        data-toggle="collapse" data-target="#collapsing-navbar">
                    <i class="fa fa-bars" aria-hidden="true"></i>
                </button>
                <div class="collapse in" id="collapsing-navbar">

                    <a class="navbar-brand" style="padding-right:25px;" href="<?php echo $server; ?>">
                        <i class="fa fa-home" aria-hidden="true"></i>
                    </a>

                    <ul class="nav navbar-nav">
                        <li class="nav-item <?php if ($pageInfo["activeTab"] == "home") echo "active "; ?>">
                            <a class="nav-link" href="/">Home</a>
                        </li>
                        <li class="nav-item <?php if ($pageInfo["activeTab"] == "whattodo") echo "active "; ?>">
                            <a class="nav-link" href="/whattodo.php">What to do</a>
                        </li>
                        <li class="nav-item dropdown <?php if ($pageInfo["activeTab"] == "search") echo "active "; ?>">
                            <a class="nav-link dropdown-toggle" data-toggle="dropdown" href="#">Search the sky<span
                                        class="caret"></span></a>
                            <div class="dropdown-menu">
                                <a class="dropdown-item" href="<?php echo $server; ?>search_moving.php">Moving
                                    objects</a>
                                <a class="dropdown-item" href="<?php echo $server; ?>search_still.php">Still
                                    photography</a>
                                <a class="dropdown-item" href="<?php echo $server; ?>search_multi.php">Multi-camera
                                    detections</a>
                                <a class="dropdown-item" href="<?php echo $server; ?>search_highlights.php">Featured
                                    images</a>
                            </div>
                        </li>
                        <li class="nav-item <?php if ($pageInfo["activeTab"] == "projects") echo "active "; ?>">
                            <a class="nav-link" href="/projects.php">Projects</a>
                        </li>
                        <li class="nav-item <?php if ($pageInfo["activeTab"] == "howitworks") echo "active "; ?>">
                            <a class="nav-link" href="/howitworks.php">How it works</a>
                        </li>
                        <li class="nav-item dropdown <?php if ($pageInfo["activeTab"] == "cameras") echo "active "; ?>">
                            <a class="nav-link dropdown-toggle" data-toggle="dropdown" href="#">Cameras<span
                                        class="caret"></span></a>
                            <div class="dropdown-menu">
                                <a class="dropdown-item" href="<?php echo $server; ?>map.php">Locations</a>
                                <a class="dropdown-item" href="<?php echo $server; ?>observatory_activity_all.php">Activity
                                    tracker</a>
                                <a class="dropdown-item" href="<?php echo $server; ?>observatory_metadata.php">Status
                                    information</a>
                            </div>
                        </li>
                        <li class="nav-item <?php if ($pageInfo["activeTab"] == "faqs") echo "active "; ?>">
                            <a class="nav-link" href="/faqs.php">FAQs</a>
                        </li>
                        <li class="nav-item <?php if ($pageInfo["activeTab"] == "about") echo "active "; ?>">
                            <a class="nav-link" href="/about.php">About</a>
                        </li>
                        <li class="nav-item <?php if ($pageInfo["activeTab"] == "login") echo "active "; ?>">
                            <a class="nav-link" href="/user/login.php">
                                <?php if (is_null($user->username)): ?>
                                    <i class="fa fa-user-plus" aria-hidden="true"></i>&nbsp;Log in
                                <?php else: ?>
                                    <i class="fa fa-user" aria-hidden="true"></i>&nbsp;Your account
                                <?php endif; ?>
                            </a>
                        </li>
                    </ul>
                </div>
            </div>
            </div>
        </nav>
        <script type="application/javascript">
            if ($(window).width() < 768) $("#collapsing-navbar").collapse("hide");

            $(function () {
                setInterval(function () {
                    if ($(window).width() > 768) {
                        if (!window.is_large) $("#collapsing-navbar").collapse("show");
                        window.is_large = true;
                    } else {
                        window.is_large = false;

                    }
                }, 500);
            });
        </script>

        <div class="bannerfade"></div>

        <?php
        print "<div class='container mainpage'>";
        HTMLtemplate::breadcrumb($pageInfo["breadcrumb"], $pageInfo["activeTab"], $pageInfo["postbreadcrumb"]);
        ?>

        <?php if (!array_key_exists("noTitle", $pageInfo)) echo "<h2>" . $pageInfo["pageTitle"] . "</h2>"; ?>

        <?php
    }

    public function footer($pageInfo)
    {
        echo "</div>";  // mainpage

        ?>
        <div class="footer">
            <div class="container">
                <div class="row">
                    <div class="col-sm-2" style="text-align:center;padding:4px;">
                    </div>

                    <div class="col-sm-4" style="padding:4px;">
                        <p class="copyright">
                            <span style="font-size:15px;">
                            &copy; <a href="#about">Cambridge Science Centre 2016.</a>
                            </span>
                        </p>

                        <p class="copyright">
                            For more information about Meteor Pi, <a href="#about">click here</a>.<br/>
                            Website designed by Dominic Ford.<br/>
                        </p>

                        <p class="copyright">
                            Top banner image courtesy of Markus Lubjuhn.
                        </p>
                    </div>
                    <div class="col-sm-6" style="padding:4px;">
                        <p class="copyright">Contact us via</p>

                        <div style="display:inline-block;text-align:center;padding:3px 10px;">
                            <a href="https://www.facebook.com/meteorpicamera/">
                                <div class="mp-img mp-img-fb"></div>
                                <br/>Facebook</a>
                        </div>
                        <div style="display:inline-block;text-align:center;padding:3px 10px;">
                            <a href="https://twitter.com/meteorpi">
                                <div class="mp-img mp-img-tweet"></div>
                                <br/>Twitter</a>
                        </div>

                    </div>
                </div>
            </div>
        </div>

        <?php
        print "</body></html>";
    }

    static public function listObstories($obstories, $urlstub)
    {
        ?>
        <h4 style="padding:20px 0;">Our cameras</h4>

        <?php foreach ($obstories as $obstory): ?>
        <p class="select-list">
            <a href="<?php echo $urlstub . $obstory['publicId']; ?>">
                <?php echo $obstory['name']; ?>
            </a>
        </p>
    <?php endforeach; ?>
        <?php
    }

    public static function slidingPanes($itemList)
    {
        ?>
        <div class="slidingPane">
            <div class="overlay_host">
                <div class="holder" style="min-height: 200px;">
                    <div class="mp-back" style="left: 18px;">
                        <div class="mp-img mp-img-leftB slidingPane_prev"></div>
                    </div>
                    <div class="mp-back" style="right:18px;">
                        <div class="mp-img mp-img-rightB slidingPane_next"></div>
                    </div>
                    <img src="/<?php echo $itemList[0]['teaser']; ?>" alt="" style="width:100%; z-index:-999;"/>
                    <?php
                    foreach ($itemList as $item) {
                        ?>
                        <div class="slidingPane_item" style="visibility:hidden;">
                            <a href="<?php echo $item['link']; ?>"><img
                                        src="/<?php echo $item['teaser']; ?>"
                                        alt="" style="width:100%;"/></a>

                            <div class="img_overcaption"><?php echo $item['caption']; ?></div>
                        </div>
                        <?php
                    }
                    ?>
                </div>
            </div>
        </div>
        <?php
    }


    public static function pageGallery($itemList)
    {
        global $const;
        ?>
        <div class="row">
        <?php
        foreach ($itemList as $item) {
            ?>
            <div class="col-md-4">
                <h3>
                    <a href="<?php echo $item['link']; ?>"><?php echo $item['title']; ?></a>
                </h3>
                <div class="chartsgalleryitem">
                    <div class="overlay_host">
                        <div class="holder">
                            <a href="<?php echo $item['link']; ?>">
                                <img src="<?php echo $const->server . $item['teaser']; ?>" alt="icon"/>
                            </a>
                            <div class="img_overcaption"><?php echo $item['caption']; ?></div>
                        </div>
                    </div>
                </div>
            </div>
            <?php
        }
        ?></div><?php
    }


    static public function imageGallery($result_list, $url_stub, $show_paths)
    {
        global $const;

        $holder_class = "";
        if ($show_paths) $holder_class = "gallery_with_markers";
        ?>

        <div class="<?php echo $holder_class; ?>">

            <?php if ($show_paths): ?>
                <div style="cursor:pointer;text-align:right;margin:16px 0;">
                    <button type="button" class="btn btn-secondary btn-sm paths-toggle">
                        <i class="fa fa-info-circle" aria-hidden="true"></i>
                        Show position markers
                    </button>
                </div>

            <?php endif; ?>
            <div class="row">
                <?php
                foreach ($result_list as $item):
                    $path_attribute = "";
                    if (array_key_exists("path", $item)) $path_attribute = "data-path=\"{$item['path']}\"";
                    ?>
                    <div class="col-md-3 gallery_item">
                        <a href="<?php echo $url_stub . $item['linkId']; ?>">
                            <div class="gallery_image" <?php echo $path_attribute; ?> >
                                <?php if ($item['mimeType'] == 'image/png'): ?>
                                    <img class="gallery_img" alt="" title="" src="/api/thumbnail/<?php
                                    echo $item['fileId'] . "/" . $item['filename'];
                                    ?>"/>
                                    <?php if ($show_paths): ?>
                                        <img class="gallery_path_marker" alt="" title="" src="/img/crosshair.gif"/>
                                    <?php endif; ?>
                                <?php elseif (array_key_exists($item['mimeType'], $const->mimeTypes)): ?>
                                    <div class="image_substitute gallery_img">
                                        <div class="mimetype">
                                            <?php echo $const->mimeTypes[$item['mimeType']]; ?>
                                        </div>
                                    </div>
                                <?php else: ?>
                                    <div class="image_substitute">
                                        <div class="mimetype">FILE</div>
                                    </div>
                                <?php endif; ?>
                            </div>
                            <div class="gallery_text">
                                <?php echo $item['caption'] ?>
                            </div>
                        </a>
                        <div class="gallery_extra">
                            <?php echo $item['hover']; ?>
                        </div>
                    </div>
                <?php endforeach; ?>
            </div>
        </div>
        <?php
    }

    static public function showPager($result_count, $pageNum, $pageSize, $self_url)
    {
        $Npages = floor($result_count / $pageSize);
        $pageMin = max($pageNum - 5, 1);
        $pageMax = min($pageMin + 9, $Npages + 1);

        print "<div class='pager'>Page ";
        for ($p = $pageMin; $p <= $pageMax; $p++) {
            print "<span class='page'>";
            if ($p != $pageNum) print "<a href='{$self_url}&page={$p}'>";
            else print "<b>";
            print $p;
            if ($p != $pageNum) print "</a>";
            else print "</b>";
            print "</span>";
        }
        print "</div>";
    }
}

$pageTemplate = new HTMLtemplate();

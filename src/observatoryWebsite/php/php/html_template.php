<?php

// html_template.php
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

class HTMLtemplate
{
    public static function breadcrumb($items, $area, $postbreadcrumb = null)
    {
        global $const;
        $server = $const->server;
        if (is_null($items)) return;
        if ($area == "news") {
            array_unshift($items, ["newsindex.php", "News"]);
        } else if ($area == "charts") {
            array_unshift($items, ["charts.php", "Charts"]);
        } else if ($area == "spacecraft") {
            array_unshift($items, ["satmap.php", "Spacecraft"]);
        } else if ($area == "objects") {
            array_unshift($items, ["data/data.php", "Objects"]);
        } else if ($area == "ephemerides") {
            array_unshift($items, ["ephemerides.php", "Data"]);
        } else if ($area == "resources") {
            array_unshift($items, ["misc/misc.php", "Resources"]);
        } else if ($area == "links") {
            array_unshift($items, ["links.php", "Links"]);
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

    public static function glossary($display, $key = null)
    {
        global $const;
        if (is_null($key)) $key = $display;
        print "<a href=\"" . $const->server . "article.php?term=" . $key . "\">" . $display . "</a>";
    }

    public static function slidingPanes($itemList)
    {
        global $const;
        ?>
        <div class="slidingPane">
 <div class="overlay_host">
  <div class="holder">
            <div class="its-back" style="left: 10px;">
                <div class="its-img its-img-leftB slidingPane_prev"></div>
            </div>
            <div class="its-back" style="right:10px;">
                <div class="its-img its-img-rightB slidingPane_next"></div>
            </div>
      <img src="<?php echo $const->server . $itemList[0]['teaser']; ?>" alt="" style="width:100%; z-index:-999;"/>
            <?php
            foreach ($itemList as $item) {
                ?>
                <div class="slidingPane_item" style="visibility:hidden;">
                    <a href="<?php echo $item['link']; ?>"><img
                            src="<?php echo $const->server . $item['teaser']; ?>"
                            alt="" style="width:100%;"/></a>

                    <div class="img_overcaption"><?php echo $item['caption']; ?></div>
                </div>
                <?php
            }
            ?>
        </div></div></div>
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
            <div class="col-md-6">
                <p class="mainbar"><span class="mainbar"><a
                            href="<?php echo $item['link']; ?>"><?php echo $item['title']; ?></a></span></p>

                <div class="mainbarb">
                    <div class="mainbarc"></div>
                </div>
                <div class="chartsgalleryitem">
                <div class="overlay_host">
                    <div class="holder">
                        <a href="<?php echo $item['link']; ?>"><img
                                src="<?php echo $const->server . $item['teaser']; ?>"
                                alt="icon"/></a>

                        <div class="img_overcaption"><?php echo $item['caption']; ?></div>
                    </div>
                </div>
            </div></div>
            <?php
        }
        ?></div><?php
    }

    public static function advertFooter()
    {
        ?>
        <div>
            <div class="tallright2">
                <script async src="//pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"></script>
                <!-- DFAN responsive -->
                <ins class="adsbygoogle"
                     style="display:block"
                     data-ad-client="ca-pub-0140009944980327"
                     data-ad-slot="5756012127"
                     data-ad-format="auto"></ins>
                <script>
                    (adsbygoogle = window.adsbygoogle || []).push({});
                </script>
            </div>
        </div>
        <?php
    }

    public static function advertSidebar()
    {
        ?>
        <div>
            <div class="tallright1 centerblock">
                <div class="tallright2">
                    <script async src="//pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"></script>
                    <!-- DFAN responsive -->
                    <ins class="adsbygoogle"
                         style="display:block"
                         data-ad-client="ca-pub-0140009944980327"
                         data-ad-slot="5756012127"
                         data-ad-format="auto"></ins>
                    <script>
                        (adsbygoogle = window.adsbygoogle || []).push({});
                    </script>
                </div>
            </div>
        </div>
        <?php
    }

    public static function sidebar($pageInfo)
    {
        global $const, $loc;
        $server = $const->server;
        ?>
        <div class="tallright">

            <div class="blkprint centerblock">

                <div class="sidebaritem" style="text-align:right;">
                    <form method="get" action="<?php echo $server; ?>search.php">
                        <p class="smtextright" style="margin:4px;">
                            <input class="txt" style="width:100%;" type="text" name="s" value=""/>
                        </p>

                        <p class="smtextright" style="margin:4px;">
                            <span class="btn"><input class="btn" type="submit" value="Search site..."/></span>
                        </p>
                    </form>
                </div>
                <div class="sidebaritem sidebarbox">
                    <p class="centretext" style="font-size: medium; padding: 2px 4px;">
                        <b><?php echo $loc->placename_short; ?></b>
                    </p>
                    <table>
                        <tr>
                            <td class="snugtop">
                                <p class="smtext">
                                    <b>Latitude: </b><br/>
                                    <b>Longitude:</b><br/>
                                    <b>Timezone: </b><br/>
                                </p>
                            </td>
                            <td class="snugtop">
                                <p class="smtext">
                                    <?php echo $loc->latStr; ?><br/>
                                    <?php echo $loc->longStr; ?><br/>
                                    <?php echo $loc->tzString; ?><br/>
                                </p>
                            </td>
                        </tr>
                    </table>
                    <form method="get" action="<?php echo $server; ?>location.php">
                        <p class="centretext noprint">
                            <span class="btn"><input class="btn" type="submit" value="Change location..."/></span>
                        </p>
                    </form>
                </div>
                <?php if ($pageInfo["linkRSS"]): ?>
                    <div class="sidebaritem sidebarbox">
                        <a href="<?php echo $pageInfo["linkRSS"]; ?>">
                            <table>
                                <tr>
                                    <td style="text-align:left;">Subscribe for free to receive news via RSS</td>
                                    <td style="text-align:right;font-weight:bold;">
                                        <div class="its-img its-img-rss" style="vertical-align:middle;"></div>
                                    </td>
                                </tr>
                            </table>
                        </a>
                    </div>
                <?php endif; ?>

                <div class="sidebaritem sidebarbox noprint" style="padding: 6px;text-align:center;">
                    <?php HTMLtemplate::likebar(); ?>
                </div>

                <?php if (in_array("sideTimes", $pageInfo["options"])): ?>
                    <div class="sidebaritem sidebarbox">
                        <?php whatsup::makeWhatsUp($loc->latitude, $loc->longitude,
                            $const->rsday, $const->rsmc, $const->rsyear, 0, 0, 2, 0, 1); ?>
                    </div>
                <?php endif; ?>
            </div>

            <?php if (in_array("sideAdvert", $pageInfo["options"])) HTMLtemplate::advertSidebar(); ?>
        </div>
        <?php
    }

    public static function likebar()
    {
        ?>
        <div class="centerblock">
            <!-- Facebook -->
            <div style="display:inline-block; margin:6px; vertical-align:middle;">
                <div id="fb-root"></div>
                <script>(function (d, s, id) {
                        var js, fjs = d.getElementsByTagName(s)[0];
                        if (d.getElementById(id)) return;
                        js = d.createElement(s);
                        js.id = id;
                        js.src = "//connect.facebook.net/en_GB/sdk.js#xfbml=1&version=v2.4";
                        fjs.parentNode.insertBefore(js, fjs);
                    }(document, 'script', 'facebook-jssdk'));</script>
                <div class="fb-like" data-layout="button" data-action="like" data-show-faces="true"
                     data-share="true"></div>
            </div>

            <!-- Twitter -->
            <div style="display:inline-block; margin:6px; vertical-align:middle;">
                <a href="https://twitter.com/share" class="twitter-share-button">Tweet</a>
                <script>!function (d, s, id) {
                        var js, fjs = d.getElementsByTagName(s)[0], p = /^http:/.test(d.location) ? 'http' : 'https';
                        if (!d.getElementById(id)) {
                            js = d.createElement(s);
                            js.id = id;
                            js.src = p + '://platform.twitter.com/widgets.js';
                            fjs.parentNode.insertBefore(js, fjs);
                        }
                    }(document, 'script', 'twitter-wjs');</script>
            </div>

            <!-- Google Plus -->
            <div style="display:inline-block; margin:6px; vertical-align:middle;">
                <div id="plusA1">
                    <div id="plusA2"></div>
                </div>
            </div>

        </div>
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
        global $const, $loc;
        if (!isset($pageInfo["breadcrumb"])) $pageInfo["breadcrumb"] = [];
        if (!isset($pageInfo["postbreadcrumb"])) $pageInfo["postbreadcrumb"] = null;
        $server = $const->server;
        $server_json = $const->server_json;
        $sitename = $const->sitename;
        print<<<__HTML__
<!DOCTYPE html>
<html lang="en">
__HTML__;
        ?>
        <head>
            <meta charset="utf-8">
            <meta name="description" content="<?php echo $pageInfo["pageDescription"]; ?>"/>
            <meta name="keywords"
                  content="astronomy news, tonight's sky, telescope, binoculars, stars, planet, mercury, venus, mars, jupiter, saturn, uranus, neptune"/>
            <meta name="generator" content="Dominic Ford"/>
            <meta name="author" content="Dominic Ford"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">

            <title id="title1">
                <?php echo $pageInfo["pageTitle"]; ?>
            </title>

            <!--[if lt IE 9]>
            <script src="<?php echo $server; ?>vendor/html5shiv/dist/html5shiv.min.js" type="text/javascript"></script>
            <script src="<?php echo $server; ?>vendor/ExplorerCanvas/excanvas.js" type="text/javascript"></script>
            <![endif]-->

            <script>
                (function (i, s, o, g, r, a, m) {
                    i['GoogleAnalyticsObject'] = r;
                    i[r] = i[r] || function () {
                            (i[r].q = i[r].q || []).push(arguments)
                        }, i[r].l = 1 * new Date();
                    a = s.createElement(o),
                        m = s.getElementsByTagName(o)[0];
                    a.async = 1;
                    a.src = g;
                    m.parentNode.insertBefore(a, m)
                })(window, document, 'script', '//www.google-analytics.com/analytics.js', 'ga');

                ga('create', 'UA-22395429-3', 'in-the-sky.org');
                ga('send', 'pageview');

            </script>

            <script src="<?php echo $server; ?>vendor/jquery/dist/jquery.min.js" type="text/javascript"></script>

            <link rel="stylesheet" href="<?php echo $server; ?>vendor/bootstrap/dist/css/bootstrap.min.css">
            <script src="<?php echo $server; ?>vendor/bootstrap/dist/js/bootstrap.min.js"></script>

            <script src="<?php echo $server; ?>vendor/jquery-ui/jquery-ui.min.js" type="text/javascript"></script>
            <link rel="stylesheet" type="text/css"
                  href="<?php echo $server; ?>vendor/jquery-ui/themes/ui-lightness/jquery-ui.min.css"/>
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


            <link
                href='https://fonts.googleapis.com/css?family=Open+Sans:400,400italic,700,700italic&amp;subset=latin,greek'
                rel='stylesheet' type='text/css'/>

            <script type="text/javascript" id="cookiebanner"
                    src="<?php echo $server; ?>js/vendor/cookiebanner.js"
                    data-moreinfo="<?php echo $server; ?>about.php#privacy"
                    data-message="<?php echo $sitename; ?> uses cookies to personalise content to your geographic location. We also share information with our advertising and analytics partners.">
            </script>

            <link rel="stylesheet" type="text/css" href="<?php echo $server; ?>css/style.css" media="all"/>
            <link rel="stylesheet" type="text/css" href="<?php echo $server; ?>css/style-print.css" media="print"/>

            <?php if (in_array("mathjax", $pageInfo["includes"])): ?>
                <script type="text/javascript"
                        src="https://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML"></script>
                <script type="text/x-mathjax-config"> MathJax.Hub.Config({"HTML-CSS": {scale: 90} });</script>
            <?php endif; ?>

            <script type="text/javascript">
                window.server = "<?php echo $server; ?>";
                window.serverjson = "<?php echo $server_json; ?>";
            </script>

            <?php if (in_array("googlemap", $pageInfo["includes"])): ?>
                <meta name="viewport" content="initial-scale=1.0, user-scalable=no"/>
                <script type="text/javascript"
                        src="https://maps.googleapis.com/maps/api/js?key=AIzaSyDj6zXvhFOM1gZ7J-TxAga8IDMjdFf8X1s&amp;sensor=false"></script>
                <script src="<?php echo $server; ?>vendor/marker-with-label/markerwithlabel.js"
                        type="text/javascript"></script>
            <?php endif; ?>

            <script type="text/javascript" src="<?php echo $server; ?>js/inthesky.min.js"></script>

            <?php if ($pageInfo["teaserImg"]): ?>
                <link rel="image_src" href="<?php echo $server . $pageInfo["teaserImg"]; ?>"
                      title="<?php echo $pageInfo["pageTitle"]; ?>"/>
                <meta property="og:image" content="<?php echo $server . $pageInfo["teaserImg"]; ?>"/>
            <?php endif; ?>

            <?php echo $pageInfo["cssextra"]; ?>
        </head>

        <?php echo "<body><div class=\"contentwrapper\">"; ?>


        <div class="bannerback">
            <div class="banner">
                <div class="banner_txt_left" id="top">
                    <p class="toptitleA"><a class="blkprint"
                                            href="<?php echo $server; ?>index.php"><?php echo $sitename; ?></a></p>

                    <p class="toptitleB"><a class="blkprint" href="<?php echo $server; ?>index.php">Guides&nbsp;to&nbsp;the&nbsp;night&nbsp;sky</a>
                    </p>
                    <?php HTMLtemplate::breadcrumb($pageInfo["breadcrumb"], $pageInfo["activeTab"], $pageInfo["postbreadcrumb"]); ?>
                </div>
                <div class="banner_txt_right">
                    <p class="toptitleC blkprint" id="title2"><?php echo $pageInfo["pageTitle"]; ?></p>
                </div>
                <div class="banner_txt_location blkprint">
                    <a href="<?php echo $server; ?>location.php">Location:
                        <?php
                        print "{$loc->placename} ({$loc->latStr}; {$loc->longStr})";
                        ?></a>
                </div>
                <div id="bannerppl"></div>
            </div>
            <div id="bannerfull"></div>
        </div>

        <nav class="navbar navbar-inverse navbar-fixed-top">
            <div class="container-fluid">
                <div class="navbar-header">
                    <a class="navbar-brand" href="<?php echo $server; ?>"><?php echo $sitename; ?></a>
                </div>
                <div>
                    <ul class="nav navbar-nav">
                        <li class="dropdown <?php if ($pageInfo["activeTab"] == "news") echo "active "; ?>">
                            <a class="dropdown-toggle" data-toggle="dropdown" href="#">News<span
                                    class="caret"></span></a>
                            <ul class="dropdown-menu">
                                <li><a href="<?php echo $server; ?>newsindex.php?feed=dfan">Top stories</a></li>
                                <li><a href="<?php echo $server; ?>data/comets.php">Comets</a></li>
                                <li><a href="<?php echo $server; ?>newsmap.php">News planetarium</a></li>
                                <li><a href="<?php echo $server; ?>newscal.php">Astronomical calendar</a></li>
                                <li><a href="<?php echo $server; ?>eclipses.php">Eclipses</a></li>
                            </ul>
                        </li>
                        <li class="dropdown <?php if ($pageInfo["activeTab"] == "charts") echo "active "; ?>">
                            <a class="dropdown-toggle" data-toggle="dropdown" href="#">Charts<span class="caret"></span></a>
                            <ul class="dropdown-menu">
                                <li><a href="<?php echo $server; ?>charts.php">Interactive charts</a></li>
                                <li><a href="<?php echo $server; ?>skymap.php">Planetarium</a></li>
                                <li><a href="<?php echo $server; ?>skymap2.php">All-sky charts</a></li>
                                <li><a href="<?php echo $server; ?>solarsystem.php">The solar system</a></li>
                                <li><a href="<?php echo $server; ?>findercharts.php">Object-finder charts</a></li>
                                <li><a href="<?php echo $server; ?>risesetcharts.php">Rising &amp; setting times</a>
                                </li>
                                <li><a href="<?php echo $server; ?>twilightmap.php">Live twilight map</a></li>
                                <li><a href="<?php echo $server; ?>earthinspace.php">The Earth in space</a></li>
                            </ul>
                        </li>
                        <li class="dropdown <?php if ($pageInfo["activeTab"] == "spacecraft") echo "active "; ?>">
                            <a class="dropdown-toggle" data-toggle="dropdown" href="#">Spacecraft<span
                                    class="caret"></span></a>
                            <ul class="dropdown-menu">
                                <li><a href="<?php echo $server; ?>satmap.php">Live satellite positions</a></li>
                                <li><a href="<?php echo $server; ?>satmap.php?gps=1">GPS satellite positions</a></li>
                                <li><a href="<?php echo $server; ?>satpasses.php">Find bright satellite passes</a></li>
                            </ul>
                        </li>
                        <li class="dropdown <?php if ($pageInfo["activeTab"] == "objects") echo "active "; ?>">
                            <a class="dropdown-toggle" data-toggle="dropdown" href="#">Objects<span
                                    class="caret"></span></a>
                            <ul class="dropdown-menu">
                                <li><a href="<?php echo $server; ?>data/data.php">Object index</a></li>
                                <li><a href="<?php echo $server; ?>sunrise.php">Sunrise &amp; sunset times</a></li>
                                <li><a href="<?php echo $server; ?>ephemeris.php">Custom ephemerides</a></li>
                                <li><a href="<?php echo $server; ?>jupiter.php">The moons of Jupiter</a></li>
                                <li><a href="<?php echo $server; ?>whatsup.php">What's in the sky?</a></li>
                            </ul>
                        </li>
                        <li class="dropdown <?php if ($pageInfo["activeTab"] == "ephemerides") echo "active "; ?>">
                            <a class="dropdown-toggle" data-toggle="dropdown" href="#">Data Tables<span
                                    class="caret"></span></a>
                            <ul class="dropdown-menu">
                                <li><a href="<?php echo $server; ?>ephemerides.php">Data tables</a></li>
                                <li><a href="<?php echo $server; ?>glossary.php">Glossary</a></li>
                                <li><a href="<?php echo $server; ?>data/constellations_map.php">Map of the
                                        constellations</a></li>
                                <li><a href="<?php echo $server; ?>ngc3d.php">The Universe in 3D</a></li>
                                <li><a href="<?php echo $server; ?>planisphere/index.php">Make a planisphere</a></li>
                                <li><a href="<?php echo $server; ?>astrolabe/index.php">Make a medieval astrolabe</a>
                                </li>
                            </ul>
                        </li>
                        <li class="dropdown <?php if ($pageInfo["activeTab"] == "resources") echo "active "; ?>">
                            <a class="dropdown-toggle" data-toggle="dropdown" href="#">Resources<span
                                    class="caret"></span></a>
                            <ul class="dropdown-menu">
                                <li><a href="<?php echo $server; ?>about.php">About In-The-Sky.org</a></li>
                                <li><a href="<?php echo $server; ?>science/demos.php">Online science demos</a></li>
                                <li><a href="<?php echo $server; ?>software.php">Open-source software</a></li>
                                <li><a href="<?php echo $server; ?>misc/pubs.php">Cambridge pub map</a></li>
                                <li><a href="<?php echo $server; ?>misc/misc.php">More...</a></li>
                            </ul>
                        </li>
                        <li class="dropdown <?php if ($pageInfo["activeTab"] == "links") echo "active "; ?>">
                            <a class="dropdown-toggle" data-toggle="dropdown" href="#">Links<span class="caret"></span></a>
                            <ul class="dropdown-menu">
                                <li><a href="<?php echo $server; ?>links.php">External links</a></li>
                                <li><a href="http://www.pyxplot.org.uk/">Pyxplot</a></li>
                                <li><a href="https://in-the-sky.org/~photos/phish/" rel="nofollow">Photo Gallery</a>
                                </li>
                            </ul>
                        </li>
                    </ul>
                </div>
            </div>
        </nav>

        <div class="bannerfade"></div>

        <?php
        print <<<__HTML__
<div class="container mainpage">
<div class="row">
<div class="col-lg-10">
<div class="mainpane">
__HTML__;

    }

    public function footer($pageInfo)
    {
        global $const;
        $server = $const->server;
        print "</div></div>"; // mainpane and col-lg-10
        ?>
        <div class="col-lg-2 tallright noprint">
            <?php $this->sidebar($pageInfo); ?>
        </div>
        <?php echo "</div>"; ?>
        <div class="row">
            <div class="col-lg-12 wideright">
                <hr/>
                <?php $this->advertFooter(); ?>
            </div>
        </div>
        <?php echo "</div>"; ?>

        <div class="footer">
            <div class="container">
                <div class="row">
                    <div class="col-md-5">
                        <p class="copyright">
                            <span style="font-size:15px;">
                            &copy; <a href="<?php echo $server; ?>about.php" rel="nofollow">Dominic
                                    Ford</a> <?php echo $const->copyright; ?>.
                            </span>
                        </p>

                        <p class="copyright">
                            For more information including contact details, <a
                                href="<?php echo $server; ?>about.php#copyright" rel="nofollow">click here</a>.<br/>
                            Last updated: <?php echo date("d M Y, H:i", $const->lastUpdate); ?> UTC<br/>
                            Website designed by <span class="its-img its-img-email"
                                                      style="height:14px;width:162px;vertical-align:middle;"></span>.<br/>
                        </p>
                    </div>
                    <div class="col-md-7">
                        <div style="display:inline-block;padding:16px;">
                            <b>Site hosted and sponsored&nbsp;by</b><br/>
                            <a href="http://www.mythic-beasts.com/">
                                <div class="its-img its-img-mythic" style="vertical-align:middle;"></div>
                            </a>
                        </div>
                        <div style="display:inline-block;padding:16px;">
                            <?php $thisURI = urlencode($_SERVER["SERVER_NAME"] . $_SERVER["REQUEST_URI"]); ?>
                            <a href="https://validator.w3.org/nu/?doc=<?php echo $thisURI; ?>" rel="nofollow">
                                <div class="its-img its-img-vhtml" style="vertical-align:middle;"></div>
                            </a>
                            <a href="http://jigsaw.w3.org/css-validator/validator?uri=<?php echo $thisURI; ?>"
                               rel="nofollow">
                                <div class="its-img its-img-vcss" style="vertical-align:middle;"></div>
                            </a>
                            <?php if ($pageInfo["linkRSS"]): ?>
                                <a href="http://feed1.w3.org/check.cgi?url=<?php echo $pageInfo["linkRSS"]; ?>"
                                   rel="nofollow">
                                    <div class="its-img its-img-vrss" style="vertical-align:middle;"></div>
                                </a>
                            <?php endif; ?>
                        </div>
                    </div>
                </div>
            </div>

        </div>

        <script type="text/javascript" src="https://apis.google.com/js/plusone.js">
        </script>
        <script type="text/javascript">
            gapi.plusone.render("plusA2", {"size": "tall", "annotation": "none"});
        </script>

        <?php
        print "</body></html>";
    }
}

$pageTemplate = new HTMLtemplate();

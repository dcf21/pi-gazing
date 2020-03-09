// planetarium.js

// Library for producing planetarium / sky view canvases

function Planetarium(settings, context) {
    var self = this;
    this.settings = settings;
    this.context = context;
    this.width = 1;
    this.height = 1;
    this.ready = 0;
    this.refresh = 0;
    this.lock = 0;
    
    // Styling information
    this.styling = {
        "radecol": "rgba(255,255,0,64)",
        "radewid": 1,
        "conlcol": "rgba(255,255,0,64)",
        "conlwid": 1,
        "conbcol": "rgba(255,255,0,64)",
        "conbwid": 1,
        "conncol": "rgba(255,255,0,64)",
        "dso_col": "rgba(255,255,0,64)",
        "starcol": "rgba(255,255,0,64)",
        "starwid": 2
    };

    // Download JSON data
    this.itemsToLoad = 2;
    self.stars = {};
    self.dsos = {};
    self.stars_tiles = [];
    jQuery.getJSON("/json/objects_0_00_00.json", function (tileData) {
        self.stars['0_00_00'] = tileData['stars'];
        self.dsos['0_00_00'] = tileData['dsos'];
        self.typename = tileData['typeNames'];
        self.stars_tiles = tileData['tiles'];
        self.setup_2();
    });
    jQuery.getJSON("/json/constellations.json", function (con) {
        self.conb = con['boundaries'];
        self.conl = con['lines'];
        self.conp = con['name_places'];
        self.cona = con['abbrevs'];
        self.conn = con['names'];
        self.setup_2();
    });
}

Planetarium.prototype.setup_2 = function () {
    var self = this;
    var i, switches;

    this.itemsToLoad -= 1;

    // Update counter showing how many items we still have to load
    if (this.itemsToLoad > 0) return;

    // If we've been told to go to particular central RA,Dec, go there now
    this.ready = 1;

    // Update display when any settings change
    switches = ["chkss", "chkls", "chksn", "chkln", "chkcb", "chkcl", "chkcn",
        "chkragrid", "chkaltazg"];
    for (i = 0; i < switches.length; i++) {
        $("." + switches[i], self.context).click(function () {
            self.refresh = 1;
        });
    }

    // Draw Planetarium
    this.resize();

    $(window).resize(function () {
        self.resize()
    });

    setInterval(function () {
        self.updateAlarm();
    }, 200); // poll for mouse moves at 5fps
};

Planetarium.prototype.rotate_xy = function(a, theta) {
    var a0 = a[0] * Math.cos(theta) + a[1] * -Math.sin(theta);
    var a1 = a[0] * Math.sin(theta) + a[1] * Math.cos(theta);
    var a2 = a[2];
    return [a0, a1, a2];
};

Planetarium.prototype.rotate_xz = function(a, theta) {
    var a0 = a[0] * Math.cos(theta) + a[2] * -Math.sin(theta);
    var a1 = a[1];
    var a2 = a[0] * Math.sin(theta) + a[2] * Math.cos(theta);
    return [a0, a1, a2];
};

Planetarium.prototype.make_zenithal = function(ra, dec) {
    var x = Math.cos(ra) * Math.cos(dec);
    var y = Math.sin(ra) * Math.cos(dec);
    var z = Math.sin(dec);
    var a = [x, y, z];
    a = this.rotate_xy(a, -this.settings['ra0']);
    a = this.rotate_xz(a, Math.PI / 2 - this.settings['dec0']);
    if (a[2] > 0.999999999) a[2] = 1.0;
    if (a[2] < -0.999999999) a[2] = -1.0;
    var altitude = Math.asin(a[2]);
    var azimuth = 0;
    if (Math.abs(Math.cos(altitude)) < 1e-7) azimuth = 0.0;
    else azimuth = Math.atan2(a[1] / Math.cos(altitude), a[0] / Math.cos(altitude));
    var zenith_angle = Math.PI / 2 - altitude;

    var za = zenith_angle;
    var az = azimuth;
    return [za, az];
};

Planetarium.prototype.ang_dist = function(ra0, dec0, ra1, dec1) {
    var x0 = Math.cos(ra0) * Math.cos(dec0);
    var y0 = Math.sin(ra0) * Math.cos(dec0);
    var z0 = Math.sin(dec0);
    var x1 = Math.cos(ra1) * Math.cos(dec1);
    var y1 = Math.sin(ra1) * Math.cos(dec1);
    var z1 = Math.sin(dec1);
    var d = Math.sqrt(Math.pow(x0 - x1, 2) + Math.pow(y0 - y1, 2) + Math.pow(z0 - z1, 2));
    return 2 * Math.asin(d / 2);
};

Planetarium.prototype.gnomonic_project = function(ra, dec) {
    var dist = this.ang_dist(ra, dec, this.settings['ra0'], this.settings['dec0']);

    if (dist > Math.PI / 2) {
        return null;
    }

    var altaz = this.make_zenithal(ra, dec, this.settings['ra0'], this.settings['dec0']);
    var za = altaz[0];
    var az = altaz[1];
    var radius = Math.tan(za);
    az += this.settings['pos_ang'];

    // Correction for barrel distortion
    var r = radius / Math.tan(this.settings['scale_x'] / 2);
    if (r > 1.4) return null;
    var bc_kn = 1. - this.settings['barrel_k1'] - this.settings['barrel_k2'];
    var r2 = r / (bc_kn + this.settings['barrel_k1'] * (r ** 2) + this.settings['barrel_k2'] * (r ** 4));
    radius = r2 * Math.tan(this.settings['scale_x'] / 2);

    var yd = radius * Math.cos(az) * (this.height / 2. / Math.tan(this.settings['scale_y'] / 2.)) + this.height/2;
    var xd = radius * -Math.sin(az) * (this.width / 2. / Math.tan(this.settings['scale_x'] / 2.)) + this.width/2;

    return [xd, yd];
};

Planetarium.prototype.inv_gnom_project = function(x, y)
{
    var x2 = (x - this.width / 2.) / (this.width / 2. / Math.tan(this.settings['scale_x'] / 2.));
    var y2 = (y - this.height / 2.) / (this.height / 2. / Math.tan(this.settings['scale_y'] / 2.));

    var za = Math.atan(Math.hypot(x2, y2));
    var az = Math.atan2(-x2, y2) - this.settings['pos_ang'];

    var r = za / Math.tan(this.settings['scale_y'] / 2.);
    za = r * Math.tan(this.settings['scale_y'] / 2.);

    var altitude = Math.PI / 2 - za;
    var a = [Math.cos(altitude) * Math.cos(az), Math.cos(altitude) * Math.sin(az), Math.sin(altitude)];

    a = this.rotate_xz(a, -Math.PI / 2 + this.settings['dec0']);
    a = this.rotate_xy(a, this.settings['ra0']);

    var ra = Math.atan2(a[1], a[0]);
    var dec = Math.asin(a[2]);

    return [ra, dec];
};

Planetarium.prototype.updateAlarm = function () {
    if (!this.refresh) return;
    this.refresh = this.draw();
};

// Return the radius of a star of magnitude mag. fv is field of view in degrees.
Planetarium.prototype.magnitudeRadius_normalise = function () {
    this.magnitudeRadius_peak = 4;
};

Planetarium.prototype.magnitudeRadius = function (mag) {
    var peak = this.magnitudeRadius_peak;
    return Math.min(5, peak / Math.pow(1.25, mag * 2)) + 4;
};

// Read the value of an HTML checkbox, with default value if the checkbox doesn't exist
Planetarium.prototype.getInputSwitch = function (name, def) {
    var l = $("." + name, self.context);
    if (l.length === 0) return def;
    return l.prop("checked");
};

Planetarium.prototype.resize = function () {
    this.width = $(".planetarium_image", this.context).width();
    this.height = $(".planetarium_image", this.context).height();

    // Set element sizes
    $(".PLbuf0", this.context).width(this.width).height(this.height);

    // Redraw
    this.draw();
};

// Main entry point for redrawing the Planetarium
Planetarium.prototype.draw = function () {
    var self = this;
    if (this.lock) return 1;
    this.lock = 1;

    // Set up graphics drawing context
    var ca_el = $(".PLbuf0", this.context);
    var ca = ca_el[0];
    ca.width = this.width; // Clear canvas
    ca.height = this.height;
    var co = ca.getContext("2d");

    var _width = this.width;
    var _height = this.height;

    var i, j, k, x, y, p, x0, y0, p0, x1, y1, p1;
    var names, penUp;

    var conb = this.conb; // constellation boundary data
    var conl = this.conl['simplified']; // constellation stick figure data
    var conn = this.conp; // constellation labels data

    // Limiting magnitude
    this.limitmag = 4;

    // Fetch settings
    var showStars = this.getInputSwitch("chkss", true);
    var labelStars = this.getInputSwitch("chkls", true);
    var showConb = this.getInputSwitch("chkcb", false);
    var showConl = this.getInputSwitch("chkcl", true);
    var showConn = this.getInputSwitch("chkcn", true);
    var showDSO = this.getInputSwitch("chksn", true);
    var labelDSO = this.getInputSwitch("chkln", false);
    var showRADec = this.getInputSwitch("chkragrid", true);

    // Draw RA/Dec grid
        if (showRADec) {
            co.strokeStyle = this.styling["radecol"];
            co.lineWidth = this.settings["radewid"];
            co.beginPath();
            penUp = 1;
            for (i = -80; i < 89; i += 10) {
                penUp = 1;
                for (j = 0; j < 361; j += 2) {
                    p0 = this.gnomonic_project(j * Math.PI / 180, i * Math.PI / 180);
                    if (p0 === null) {
                        penUp = 1;
                        continue;
                    }
                    x0 = p0[0];
                    y0 = p0[1];
                    if (penUp) co.moveTo(x0, y0);
                    else co.lineTo(x0, y0);
                    penUp = 0;
                }
            }
            for (j = 0; j < 359; j += 15) {
                penUp = 1;
                for (i = -89; i < 90; i += 2) {
                    p0 = this.gnomonic_project(j * Math.PI / 180, i * Math.PI / 180);
                    if (p0 === null) {
                        penUp = 1;
                        continue;
                    }
                    x0 = p0[0];
                    y0 = p0[1];
                    if (penUp) co.moveTo(x0, y0);
                    else co.lineTo(x0, y0);
                    penUp = 0;
                }
            }
            co.stroke();
        }

    // Draw constellation sticks
    if (showConl) {
        co.strokeStyle = self.styling["conlcol"];
        co.lineWidth = self.styling["conlwid"];
        for (i = 0; i < conl.length; i++) {
            if (conl[i][4] > self.limitmag) continue;
            p0 = this.gnomonic_project(conl[i][0], conl[i][1]);
            if (p0 === null) continue;
            p1 = this.gnomonic_project(conl[i][2], conl[i][3]);
            if (p1 === null) continue;
            x0 = p0[0];
            y0 = p0[1];
            x1 = p1[0];
            y1 = p1[1];
            co.beginPath();
            co.moveTo(x0, y0);
            co.lineTo(x1, y1);
            co.stroke();
        }
    }

    // Draw constellation boundaries
    if (showConb) {
        co.strokeStyle = self.styling["conbcol"];
        co.lineWidth = self.styling["conbwid"];
        co.beginPath();
        for (i = 0; i < conb.length; i++) {
            var first_point = false;
            var pen_up = true;
            var is_ursa_minor = (conb[i][0][1] === "Ursa Minor");

            // First item in list is the name of the constellation
            for (j = 1; j < conb[i].length; j++) {
                // The boundary of Ursa Minor is a bit dodgy, and skirt around the pole star in the wrong direction.
                // If we don't draw it, then the boundary of Cepheus is in the right place
                if ((conb[i][j][1] > 87. * Math.PI / 180) && is_ursa_minor) {
                    pen_up = true;
                    continue;
                }

                p0 = this.gnomonic_project(conb[i][j][0], conb[i][j][1]);
                if (p0 !== null) {
                    x0 = p0[0];
                    y0 = p0[1];
                    if (pen_up) co.moveTo(x0, y0);
                    else co.lineTo(x0, y0);
                    pen_up = false;
                } else {
                    pen_up = true;
                }
                if (j === 0) first_point = [x0, y0];
            }
            if ((!pen_up) && first_point) {
                co.lineTo(first_point[0], first_point[1]);
            }
        }
        co.stroke();
    }

    // Write constellation names
    if (showConn) {
        for (i = 0; i < conn.length; i++) {
            var n = conn[i].length;
            if (conn[i][n - 1][0] > self.limitmag) continue;
            for (j = 1; j < n - 1; j += 2) {
                p = this.gnomonic_project(conn[i][j], conn[i][j + 1]);
                if (p === null) continue;
                x = p[0];
                y = p[1];

                // Create text
                co.fillStyle = this.styling["conncol"];
                co.textAlign = "center";
                co.textBaseline = "middle";
                co.fillText(conn[i][0], x, y);

                break;
            }
        }
    }

    // If we're drawing either stars or DSOs, we need to download object tile data
    if (showStars || showDSO) {
        // Work out which tiles we are displaying
        var tileList = ['0_00_00'];
        for (i = 1; i < this.stars_tiles.length; i++) if (self.limitmag > this.stars_tiles[i - 1][0]) {
            for (x = 0; x <= 10; x++) for (y = 0; y <= 10; y++) {
                p = this.inv_gnom_project(_width * x / 10, _height * y / 10);
                var ra_tile = Math.floor((((p[0] + 4 * Math.PI) / (2 * Math.PI)) % 1) * this.stars_tiles[i][1]);
                var dec_tile = Math.floor((p[1] / Math.PI + 0.5) * this.stars_tiles[i][2]);
                if (ra_tile < 0) ra_tile = 0;
                if (ra_tile >= this.stars_tiles[i][1]) ra_tile = this.stars_tiles[i][1] - 1;
                if (dec_tile <= 0) {
                    dec_tile = 0;
                    ra_tile = 0;
                }
                if (dec_tile >= (this.stars_tiles[i][2] - 1)) {
                    dec_tile = this.stars_tiles[i][2] - 1;
                    ra_tile = 0;
                }
                var tileName = i + "_" + padStr(ra_tile) + "_" + padStr(dec_tile);

                if ($.inArray(tileName, tileList) !== -1) continue; // We already have this tile

                // See whether we need to download this tile
                if (!this.stars.hasOwnProperty(tileName)) {
                    var fn = function (tileName) {
                        self.stars[tileName] = [];
                        self.dsos[tileName] = [];
                        jQuery.getJSON("/json/objects_" + tileName + ".json", function (tileData) {
                            self.stars[tileName] = tileData['stars'];
                            self.dsos[tileName] = tileData['dsos'];
                            self.refresh = 1;
                        });
                    };
                    fn(tileName); // Do this to stop tileName variable from changing value while we're downloading
                } else {
                    tileList.push(tileName);
                }
            }
        }
    }

    // Draw deep sky objects
    if (showDSO) {
        // Display DSOs which two fainter than surrounding stars
        var dso_mag_offset = 2;
        co.textStyle = "13px Arial,Helvetica,sans-serif";
        co.fillStyle = self.styling["dso_col"];
        co.strokeStyle = self.styling["dso_col"];
        co.lineWidth = 1.5;
        var ns = 3;

        // Loop over all of the tiles which we are going to display
        // Display tiles in inverse order, so bright stars like Castor are drawn in front of faint companions
        for (k = tileList.length - 1; k >= 0; k--) {
            var dsos = this.dsos[tileList[k]];
            for (i = dsos.length - 1; i >= 0; i--) {
                if (dsos[i][5] > self.limitmag + dso_mag_offset) continue;
                p = this.gnomonic_project(dsos[i][1], dsos[i][2]);
                if (p === null) continue;
                x = p[0];
                y = p[1];
                co.beginPath();
                co.moveTo(x - ns, y - ns);
                co.lineTo(x + ns, y + ns);
                co.moveTo(x - ns, y + ns);
                co.lineTo(x + ns, y - ns);
                co.stroke();
                if (labelDSO) {
                    co.textAlign = "left";
                    co.textBaseline = "middle";
                    co.fillText(dsos[i][0], x + ns + 3, y);
                }
            }
        }
    }

    // Draw stars
    if (showStars) {
        this.magnitudeRadius_normalise();

        co.fillStyle = self.styling["starcol"];
        co.strokeStyle = self.styling["starcol"];
        co.lineWidth = self.styling["starwid"];
        co.textStyle = "13px Arial,Helvetica,sans-serif";

        // Loop over all of the tiles which we are going to display
        // Display tiles in inverse order, so bright stars like Castor are drawn in front of faint companions
        for (k = tileList.length - 1; k >= 0; k--) {
            var stars = this.stars[tileList[k]];
            for (i = stars.length - 1; i >= 0; i--) {
                if (stars[i][4] > self.limitmag) continue;
                p = this.gnomonic_project(stars[i][1], stars[i][2]);
                if (p === null) continue;
                co.beginPath();
                x = p[0];
                y = p[1];
                var M = this.magnitudeRadius(stars[i][4]);
                co.globalCompositeOperation = "destination-out";
                co.arc(x, y, M, 0, 2 * Math.PI, false);
                co.fill();
                co.globalCompositeOperation = "source-over";
                co.arc(x, y, M, 0, 2 * Math.PI, false);
                co.stroke();

                names = [];
                if (stars[i][0]) names.push(stars[i][0]);
                if (stars[i][5]) names.push(stars[i][5]);
                if (stars[i][6]) names.push(stars[i][6]);

                if (labelStars && (stars[i][4] < (self.limitmag - 2.5))) {
                    co.textAlign = "left";
                    co.textBaseline = "middle";
                    co.fillText(names[0], x + M + 4, y);
                }
            }
        }
    }

    this.lock = 0;
    return 0;
};

$(function () {
    $(".planetarium").each(function (i, el) {
        var context = $(el);
        var meta = context.data("meta");
        var handler = new Planetarium(meta, context);
        context.data("handler", handler);
    });
});

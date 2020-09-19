// sky_coverage.js

// Library for producing sky coverage canvases

function SkyCoverageChart(settings, polygons, context) {
    var self = this;
    this.settings = settings;
    this.polygons = polygons;
    this.context = context;
    this.width = 1;
    this.width_on_last_resize = 1;
    this.height = 1;
    this.refresh = 0;
    this.lock = 0;

    // Margins
    this.margin_left = 60;
    this.margin_right = 5;
    this.margin_top = 5;
    this.margin_bottom = 45;

    // Styling information
    this.styling = {
        "radecol": "rgba(255,255,255,0.2)",
        "radewid": 0.5,
        "conlcol": "rgba(255,255,0,0.5)",
        "conlwid": 0.5,
        "conbcol": "rgba(255,255,255,0.7)",
        "conbwid": 0.5,
        "conncol": "rgba(255,255,255,0.6)",
        "starcol": "rgba(255,255,0,0.7)"
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

SkyCoverageChart.prototype.setup_2 = function () {
    var self = this;

    this.itemsToLoad -= 1;

    // Update counter showing how many items we still have to load
    if (this.itemsToLoad > 0) return;

    // Set up hover manager
    this.hoverman = new HoverManager($("canvas", this.context), false,
        function (id, x, y) {
            self.hoverHover(id, x, y);
        }, function (id, x, y) {
            self.hoverClick(id, x, y);
        }, false);
    this.hovermankeys = {};
    this.hovermannextkey = 1;

    // We are now ready to display the sky coverage chart
    this.ready = 1;

    // Draw chart
    this.resize();

    // Update display when the window is resized
    $(window).resize(function () {
        self.resize()
    });

    // Poll for configuration changes 4 times a second
    setInterval(function () {
        self.updateAlarm();
    }, 250);
};

SkyCoverageChart.prototype.project = function (ra, dec) {
    var x = this.margin_left + (this.width - this.margin_left - this.margin_right) * (1 - ra / (2 * Math.PI));
    var y = this.margin_top + (this.height - this.margin_top - this.margin_bottom) * (1 - Math.sin(dec)) / 2;
    return [x, y];
};

SkyCoverageChart.prototype.stroke_line = function (co, hover_key, ra0, dec0, ra1, dec1) {
    var p0 = this.project(ra0, dec0);
    var p1 = this.project(ra1, dec1);
    var w_sum, w0, w1;

    if ((ra0 < Math.PI * 0.5) && (ra1 > Math.PI * 1.5)) {
        w_sum = ra0 + (2 * Math.PI - ra1) + 1e-8;
        w1 = ra0 / w_sum;
        w0 = 1 - w1;

        co.beginPath();
        co.moveTo(p0[0], p0[1]);
        co.lineTo(this.width - this.margin_right, p0[1] * w0 + p1[1] * w1);
        co.moveTo(this.margin_left, p0[1] * w0 + p1[1] * w1);
        co.lineTo(p1[0], p1[1]);
        co.stroke();

        if (hover_key !== null) {
            this.hoverman.hoverLine(hover_key, p0[0], p0[1], this.width - this.margin_right, p0[1] * w0 + p1[1] * w1);
            this.hoverman.hoverLine(hover_key, this.margin_left, p0[1] * w0 + p1[1] * w1, p1[0], p1[1]);
        }
    } else if ((ra1 < Math.PI * 0.5) && (ra0 > Math.PI * 1.5)) {
        w_sum = ra1 + (2 * Math.PI - ra0) + 1e-8;
        w1 = ra1 / w_sum;
        w0 = 1 - w1;

        co.beginPath();
        co.moveTo(p1[0], p1[1]);
        co.lineTo(this.width - this.margin_right, p1[1] * w0 + p0[1] * w1);
        co.moveTo(this.margin_left, p1[1] * w0 + p0[1] * w1);
        co.lineTo(p0[0], p0[1]);
        co.stroke();

        if (hover_key !== null) {
            this.hoverman.hoverLine(hover_key, p1[0], p1[1], this.width - this.margin_right, p1[1] * w0 + p0[1] * w1);
            this.hoverman.hoverLine(hover_key, this.margin_left, p1[1] * w0 + p0[1] * w1, p0[0], p0[1]);
        }
    } else {
        co.beginPath();
        co.moveTo(p0[0], p0[1]);
        co.lineTo(p1[0], p1[1]);
        co.stroke();

        if (hover_key !== null) {
            this.hoverman.hoverLine(hover_key, p0[0], p0[1], p1[0], p1[1]);
        }
    }
};

SkyCoverageChart.prototype.updateAlarm = function () {
    // Check if the image has been resized
    var current_width = this.context.width();
    if (current_width !== this.width_on_last_resize) this.resize();

    // Check if we need to update display
    if (!this.refresh) return;
    this.refresh = this.draw();
};

// Return the radius of a star of magnitude mag. fv is field of view in degrees.
SkyCoverageChart.prototype.magnitudeRadius_normalise = function () {
    this.magnitudeRadius_peak = 4;
};

SkyCoverageChart.prototype.magnitudeRadius = function (mag) {
    var peak = this.magnitudeRadius_peak;
    return Math.min(3, peak / Math.pow(1.2, mag * 2));
};

SkyCoverageChart.prototype.resize = function () {
    this.height = Math.min(window.innerHeight * 0.9, this.context.width() * 0.5);
    this.width = this.height * 2;
    this.width_on_last_resize = this.context.width();

    // Set element sizes
    $(".sky_chart_canvas", this.context).width(this.width).height(this.height);

    // Redraw
    this.draw();
};

// Main entry point for redrawing the sky coverage chart
SkyCoverageChart.prototype.draw = function () {
    var self = this;
    if (this.lock) return 1;
    this.lock = 1;

    // Set up graphics drawing context
    var ca_el = $(".sky_chart_canvas", this.context);
    var ca = ca_el[0];
    ca.width = this.width; // Clear canvas
    ca.height = this.height;
    var co = ca.getContext("2d");

    var _width = this.width;
    var _height = this.height;

    // Reset HoverManager library
    this.hoverman.reset();
    this.hovermankeys = {};
    this.hovermannextkey = 1;

    var i, j, k, x, y, p;

    var conb = this.conb; // constellation boundary data
    var conl = this.conl['simplified']; // constellation stick figure data
    var conn = this.conp; // constellation labels data

    // Limiting magnitude
    this.limitmag = 4;

    // Draw black background
    co.fillStyle = "#000";
    co.beginPath;
    co.rect(this.margin_left, this.margin_top,
        this.width - this.margin_left - this.margin_right,
        this.height - this.margin_top - this.margin_bottom);
    co.fill();

    // Draw RA/Dec grid
    co.strokeStyle = this.styling["radecol"];
    co.lineWidth = this.settings["radewid"];
    co.font = "14px Arial,Helvetica,sans-serif";
    co.fillStyle = "#000";
    co.textAlign = "center";
    co.textBaseline = "middle";
    co.save();
    co.translate(this.margin_left * 0.2, this.height * 0.5);
    co.rotate(-Math.PI / 2);
    co.fillText("Declination", 0, 0);
    co.restore();

    co.textAlign = "right";
    for (i = -75; i < 89; i += 15) {
        p = this.project(0, i * Math.PI / 180);
        co.beginPath();
        co.moveTo(this.margin_left, p[1]);
        co.lineTo(this.width - this.margin_right, p[1]);
        co.stroke();
        co.fillText(i + "°", this.margin_left - 4, p[1]);
    }

    co.font = "14px Arial,Helvetica,sans-serif";
    co.fillStyle = "#000";
    co.textAlign = "center";
    co.textBaseline = "middle";
    co.fillText("Right Ascension", this.width * 0.5, this.height - this.margin_bottom * 0.2);

    co.textBaseline = "top";
    for (j = 0, i = 0; i < 359; i += 30, j += 2) {
        p = this.project(i * Math.PI / 180, 0);
        co.beginPath();
        co.moveTo(p[0], this.margin_top);
        co.lineTo(p[0], this.height - this.margin_bottom);
        co.stroke();
        co.fillText(j + "ʰ", p[0], this.height - this.margin_bottom + 4);
    }

    // Draw constellation sticks
    co.strokeStyle = self.styling["conlcol"];
    co.lineWidth = self.styling["conlwid"];
    for (i = 0; i < conl.length; i++) {
        if (conl[i][4] > self.limitmag) continue;
        this.stroke_line(co, null, conl[i][0], conl[i][1], conl[i][2], conl[i][3]);
    }

    // Draw constellation boundaries
    co.strokeStyle = self.styling["conbcol"];
    co.lineWidth = self.styling["conbwid"];
    for (i = 0; i < conb.length; i++) {
        var first_point = false;
        var previous_point = null;
        var is_ursa_minor = (conb[i][0][1] === "Ursa Minor");

        // First item in list is the name of the constellation
        for (j = 1; j < conb[i].length; j++) {
            // The boundary of Ursa Minor is a bit dodgy, and skirt around the pole star in the wrong direction.
            // If we don't draw it, then the boundary of Cepheus is in the right place
            if ((conb[i][j][1] > 87. * Math.PI / 180) && is_ursa_minor) {
                previous_point = null;
                continue;
            }

            if (previous_point !== null) {
                this.stroke_line(co, null, previous_point[0], previous_point[1], conb[i][j][0], conb[i][j][1]);
            }
            previous_point = [conb[i][j][0], conb[i][j][1]];
            if (j === 0) first_point = [conb[i][j][0], conb[i][j][1]];
        }
        if ((previous_point !== null) && first_point) {
            co.stroke_line(co, null, first_point[0], first_point[1], previous_point[0], previous_point[1]);
        }
    }

    // Write constellation names
    for (i = 0; i < conn.length; i++) {
        var n = conn[i].length;
        if (conn[i][n - 1][0] > self.limitmag) continue;

        p = this.project(conn[i][1], conn[i][2]);

        // Create text
        co.font = "bold 11px Arial,Helvetica,sans-serif";
        co.fillStyle = this.styling["conncol"];
        co.textAlign = "center";
        co.textBaseline = "middle";
        co.fillText(conn[i][0], p[0], p[1]);
    }

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

    // Draw stars
    this.magnitudeRadius_normalise();

    co.fillStyle = self.styling["starcol"];

    // Loop over all of the tiles which we are going to display
    for (k = tileList.length - 1; k >= 0; k--) {
        var stars = this.stars[tileList[k]];
        for (i = stars.length - 1; i >= 0; i--) {
            if (stars[i][4] > self.limitmag) continue;
            p = this.project(stars[i][1], stars[i][2]);
            if (p === null) continue;
            co.beginPath();
            x = p[0];
            y = p[1];
            var M = this.magnitudeRadius(stars[i][4]);
            co.arc(x, y, M, 0, 2 * Math.PI, false);
            co.fill();
        }
    }

    // Draw frame around images
    co.lineWidth = 2;
    for (i = 0; i < this.polygons.length; i++) {
        for (j = 2; j < this.polygons[i].length; j++) {
            co.strokeStyle = this.polygons[i][0][2];
            this.hovermankeys[this.hovermannextkey] = this.polygons[i][0];
            this.stroke_line(co, this.hovermannextkey,
                this.polygons[i][j - 1][0] * Math.PI / 12,
                this.polygons[i][j - 1][1] * Math.PI / 180,
                this.polygons[i][j][0] * Math.PI / 12,
                this.polygons[i][j][1] * Math.PI / 180);
            this.hovermannextkey++;
        }
    }

    // Draw border of chart
    co.strokeStyle = "#888";
    co.lineWidth = 2;
    co.beginPath;
    co.rect(this.margin_left, this.margin_top,
        this.width - this.margin_left - this.margin_right,
        this.height - this.margin_top - this.margin_bottom);
    co.stroke();

    this.lock = 0;
    return 0;
};

SkyCoverageChart.prototype.hoverHover = function (id, x, y) {
    var el = $(".annotation-hover", this.context);

    if (this.hovermankeys.hasOwnProperty(id)) {
        el.css("width", "160px");
        el.css("left", (x - 80) + "px");
        el.css("top", (y + 12) + "px");
        el.css("display", "block");
        el.html(this.hovermankeys[id][0]);
        this.context.css("cursor", "pointer");
    } else {
        // If we are not hovering over a marker, remove the hover text box now
        el.css("display", "none");
        this.context.css("cursor", "auto");

    }
};

SkyCoverageChart.prototype.hoverClick = function (id, x, y) {
    // Call any hook functions for a click event on a marker
    if (this.hovermankeys.hasOwnProperty(id)) {
        window.location = this.hovermankeys[id][1];
    }
};

$(function () {
    $(".sky_coverage_chart").each(function (i, el) {
        var context = $(el);
        var meta = context.data("meta");
        var polygons = context.data("polygons");
        var handler = new SkyCoverageChart(meta, polygons, context);
        context.data("handler", handler);
    });
});

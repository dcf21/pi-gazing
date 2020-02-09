// galleryMarkers.js
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2015-2020 Dominic Ford.

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

// This class implements markers which show the positions of moving objects in an image gallery

function GalleryMarkers(parent) {
    var self = this;

    // The outer div representing the whole image gallery
    this.parent = parent;

    // A list of all the items within this gallery for which we should show paths
    this.children = $("div[data-path]", parent);

    // Flag indicating whether the markers are enabled
    this.show_paths = true;

    // The marker alternates between the ends of the path of the moving object
    this.bezier_index = 0;

    // Wire up button to toggle whether to display paths
    $(".paths-toggle",this.parent).click(function () {
        self.show_paths = !self.show_paths;
        self.update();
    });

    // Delaying turning markers on, and then fade them in. Looks better this way, as images may take a moment to load.
    setTimeout((function (self) {
        return function () {
            self.init_2();
        }
    })(this), 1000);
}

GalleryMarkers.prototype.init_2 = function () {
    var self = this;
    self.update();
    self.alarm();

    // Wobble marker along the length of the track, moving once every 2 seconds
    setInterval((function (self) {
        return function () {
            self.alarm();
        }
    })(this), 2000);
};

GalleryMarkers.prototype.alarm = function () {
    if (!this.show_paths) return;

    // Alternate which end of the track has the markers
    this.bezier_index += 2;
    if (this.bezier_index > 2) this.bezier_index = 0;

    // Move the markers to their new positions
    this.setPositions(this.bezier_index, true)
};

GalleryMarkers.prototype.setPositions = function (bezierIndex, animate) {
    if (!this.show_paths) return;

    // Loop over children, positioning cross hairs
    this.children.each(function (i, el) {
        var elj = $(el);
        var animate_this = animate;
        var path = elj.data("path");
        var image = $(".gallery_img", elj);

        // Fetch the crosshair's HTML element (if it exists)
        var crosshair = $(".gallery_path_marker", elj);
        if (!crosshair) return true;

        // If the path is not an array, don't show a crosshair
        if (!$.isArray(path)) {
            crosshair.remove();
            return true;
        }

        // We will need to scale the pixel coordinates of the moving object to the size of the thumbnail image
        var image_xsize = image.width();
        var image_ysize = image.height();

        // Hide crosshair if image has not loaded yet!
        if (image_ysize<50) {
            return true;
        }

        // If the crosshair was not previously visible, we gently fade it in
        if (!crosshair.is(":visible"))
        {
            animate_this=false;
            crosshair.fadeIn(400);
        }

        // Look up the size of the original frame, in whose pixel coordinates the position of the object is reported
        var raw_width = parseFloat(elj.data("width"));
        var raw_height = parseFloat(elj.data("height"));

        var object_xpos = path[bezierIndex][0];
        var object_ypos = path[bezierIndex][1];
        var crosshair_x = image_xsize * object_xpos / raw_width - 15;
        var crosshair_y = image_ysize * object_ypos / raw_height - 15;
        if (animate_this) {
            crosshair.animate({"left": crosshair_x, "top": crosshair_y}, 1500)
        }
        else {
            crosshair.css("left", crosshair_x).css("top", crosshair_y);
        }
    });
};

GalleryMarkers.prototype.update = function () {
    var self = this;
    if (self.show_paths) {
        this.bezier_index = 0;
        this.setPositions(this.bezier_index, false);
    }
    else {
        $(".gallery_path_marker",this.parent).stop().fadeOut(400);
    }
};

// Initialise all HTML elements with class pane-sequence
function galleryMarkersRegister() {
    $(".gallery_with_markers").each(function (i, el) {
        var elj = $(el);
        var markers = new GalleryMarkers(elj);
        elj.data("handler", markers);
    });
}

$(galleryMarkersRegister);

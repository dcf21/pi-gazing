// videoMarkers.js
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2019 Dominic Ford.

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

// This class implements markers which overlay videos to show the positions of moving objects

function VideoMarkers(parent) {
    var self = this;

    // The outer div representing the whole image gallery
    this.parent = parent;
    this.path = parent.data("path");
    this.time_start = parseFloat(parent.data("start"));
    this.width_original = parseFloat(parent.data("width"));
    this.height_original = parseFloat(parent.data("height"));

    // Flag indicating whether the markers are enabled
    this.show_paths = true;

    // Wire up button to toggle whether to display paths
    $(".video_marker").click(function () {
        self.show_paths = $(".video_marker")[0].checked;
        self.update();
    });

    // Delaying turning markers on, and then fade them in. Looks better this way, as images may take a moment to load.
    setTimeout((function (self) {
        return function () {
            self.init_2();
        }
    })(this), 1000);
}

VideoMarkers.prototype.init_2 = function () {
    var self = this;
    self.update();
    self.alarm();

    // Move marker as video plays, updating every 100 ms
    setInterval((function (self) {
        return function () {
            self.alarm();
        }
    })(this), 100);
};

VideoMarkers.prototype.alarm = function () {
    if (!this.show_paths) return;

    var current_time = $("video", this.parent)[0].currentTime + this.time_start;

    // Move the markers to their new positions
    this.setPositions(current_time)
};

VideoMarkers.prototype.setPositions = function (time_point) {
    var self = this;
    if (!this.show_paths) return;

    // Positioning cross-hairs
    var video = $("video", this.parent);

    // Fetch the cross-hair's HTML element (if it exists)
    var crosshair = $(".video_path_marker", this.parent);
    if (!crosshair) return;

    // If the path is not an array, don't show a cross-hair
    if (!$.isArray(this.path)) {
        crosshair.remove();
        return;
    }

    // Find position for cross hair
    var object_xpos = null;
    var object_ypos = null;
    for (var i = 0; i < this.path.length - 1; i++) {
        if ((time_point >= this.path[i][3]) && (time_point <= this.path[i + 1][3])) {
            var weight_0 = (this.path[i + 1][3] - time_point) / (this.path[i + 1][3] - this.path[i][3]);
            var weight_1 = (time_point - this.path[i][3]) / (this.path[i + 1][3] - this.path[i][3]);

            object_xpos = this.path[i][0] * weight_0 + this.path[i + 1][0] * weight_1;
            object_ypos = this.path[i][1] * weight_0 + this.path[i + 1][1] * weight_1;
            break;
        }
    }

    if (object_xpos === null) {
        crosshair.hide();
        return;
    }

    // We will need to scale the pixel coordinates of the moving object to the size of the thumbnail image
    var image_xsize = video.width();
    var image_ysize = video.height();

    // Hide cross-hair if image has not loaded yet!
    if (image_ysize < 50) {
        return;
    }

    // If the cross-hair was not previously visible, we gently fade it in
    if (!crosshair.is(":visible")) {
        crosshair.fadeIn(400);
    }

    var crosshair_x = image_xsize * object_xpos / self.width_original - 15;
    var crosshair_y = image_ysize * object_ypos / self.height_original - 15;

    crosshair.css("left", crosshair_x).css("top", crosshair_y);
};

VideoMarkers.prototype.update = function () {
    var self = this;
    if (self.show_paths) {
        this.bezier_index = 0;
        this.setPositions(this.bezier_index, false);
    } else {
        $(".video_path_marker", this.parent).stop().fadeOut(400);
    }
};

// Initialise all HTML elements with class pane-sequence
function VideoMarkersRegister() {
    $(".video_marker_overlay").each(function (i, el) {
        var elj = $(el);
        var markers = new VideoMarkers(elj);
        elj.data("handler", markers);
    });
}

$(VideoMarkersRegister);

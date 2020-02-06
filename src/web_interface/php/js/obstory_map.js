// obstory_map.js
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

// Module for observatory maps
function ObstoryMap(parent) {
    var self = this;
    self.parent = parent;

    self.obstories = self.parent.data('meta');

    // Set up Google Map
    self.mapOptions = {
        center: new google.maps.LatLng(52.20, 0.12),
        zoom: (self.obstories.length>1) ? 7 : 9,
        mapTypeId: google.maps.MapTypeId.HYBRID,
        streetViewControl: false,
        mapTypeControl: false
    };
    self.mapCanvas = $(".map_canvas", self.parent)[0];
    self.map = new google.maps.Map(self.mapCanvas, self.mapOptions);

    self.markers = {};
    $.each(self.obstories, function (index, obstory) {
        var marker = new google.maps.Marker({
            position: new google.maps.LatLng(obstory['latitude'], obstory['longitude']),
            map: self.map,
            title: obstory['name']
        });
        marker.addListener('click', function () {
            window.location = "/observatory.php?id="+obstory['publicId'];
        });
        self.markers[obstory['publicId']] = marker;
    });
}

// Initialise all HTML elements with class sliding_pane
function obstoryMapRegister() {
    $(".camera_map").each(function (i, el) {
        var elj = $(el);
        var handler = new ObstoryMap(elj);
        elj.data("handler", handler);
    });
}

$(obstoryMapRegister);

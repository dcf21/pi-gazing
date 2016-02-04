// obstory_map.js
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

// Module for observatory maps
function ObstoryMap(parent) {
    var self = this;
    self.parent = parent;

    // Set up Google Map
    self.mapOptions = {
        center: new google.maps.LatLng(52.208602, 0.120618),
        zoom: 7,
        mapTypeId: google.maps.MapTypeId.HYBRID,
        streetViewControl: false,
        mapTypeControl: false
    };
    self.mapCanvas = $(".map_canvas", self.parent)[0];
    self.map = new google.maps.Map(self.mapCanvas, self.mapOptions);

    self.obstories = self.parent.data('meta');
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

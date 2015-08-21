define(['jquery', 'knockout', 'text!./status-page.html', 'client'], function ($, ko, templateMarkup, client) {

    function StatusPage(params) {
        var self = this;
        // Available cameras
        self.cameras = ko.observableArray();
        // The selected value in the camera drop-down
        self.selectedCamera = ko.observable();
        // The status for this current camera
        self.status = ko.observable();
        self.statuses = ko.observableArray();
        // Set up Google Map
        self.mapOptions = {
            center: new google.maps.LatLng(52.208602, 0.120618),
            zoom: 4,
            mapTypeId: google.maps.MapTypeId.HYBRID,
            streetViewControl: false,
            mapTypeControl: false
        };
        self.map = new google.maps.Map(document.getElementById("map_canvas"), self.mapOptions);

        // Get the cameras
        client.listCameras(function (err, cameras) {
            self.cameras(cameras);
            if (params.camera && (params.camera in cameras)) self.setCamera(params.camera);
            $.each(self.cameras(), function (index, camera) {
                client.getStatus(camera, null, function (err, status) {
                    self.statuses[camera] = status;
                    var marker = new google.maps.Marker({
                        position: new google.maps.LatLng(status.location.lat, status.location.long),
                        map: self.map,
                        title: camera
                    });
                });
            });
        });
    }

    /**
     * This is called whenever a value is set, including on first load, so
     * we can use it to initialise the status panel as well as to respond to
     * any user selections.
     */
    StatusPage.prototype.setCamera = function (selected) {
        var self = this;
        self.selectedCamera(selected);
        if (selected != null) {
            if (!selected in self.statuses) {
                self.status(self.statuses[selected])
            }
            else {
                client.getStatus(selected, null, function (err, status) {
                    self.status(status);});
            }
        }
    };

    StatusPage.prototype.dispose = function () {
        //
    };

    return {viewModel: StatusPage, template: templateMarkup};

})
;

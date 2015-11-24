define(['jquery', 'knockout', 'text!./status-page.html', 'client'], function ($, ko, templateMarkup, client) {

    function StatusPage(params) {
        var self = this;
        self.user = client.user;
        self.time = ko.observable(new Date(Date.now()));
        // Available cameras
        self.cameras = ko.observableArray();
        // The selected value in the camera drop-down
        self.selectedCamera = ko.observable();
        // The status for this current camera
        self.status = ko.observable();
        self.statuses = [];
        self.markers = [];
        // Set up Google Map
        self.mapOptions = {
            center: new google.maps.LatLng(52.208602, 0.120618),
            zoom: 7,
            mapTypeId: google.maps.MapTypeId.HYBRID,
            streetViewControl: false,
            mapTypeControl: false
        };
        self.map = new google.maps.Map(document.getElementById("map_canvas"), self.mapOptions);

        // Get the cameras
        client.listCameras(function (err, cameras) {
            self.cameras(cameras);
            $.each(self.cameras(), function (index, camera) {
                client.getStatus(camera, null, function (err, status) {
                    self.statuses[camera] = status;
                    var marker = new google.maps.Marker({
                        position: new google.maps.LatLng(status.location.lat, status.location.long),
                        map: self.map,
                        title: camera
                    });
                    marker.addListener('click', function () {
                        self.setCamera(camera);
                    });
                    self.markers[camera] = marker;
                });
            });
            if (params.time) self.time(new Date(params.time));
            if (params.camera && (params.camera in cameras)) self.setCamera(params.camera);
            else self.setCamera(null);
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
                self.status(self.statuses[selected]);
                $.each(self.markers, function (index, marker) {
                    marker.setMap((index == selected) ? self.map : null);
                });
                self.map.setCenter(new google.maps.LatLng(self.status().location.lat, self.status().location.long));
            }
            else {
                client.getStatus(selected, self.time(), function (err, status) {
                    self.status(status);
                    $.each(self.markers, function (index, marker) {
                        marker.setMap((index == selected) ? self.map : null);
                    });
                    self.map.setCenter(new google.maps.LatLng(self.status().location.lat, self.status().location.long));
                });
            }

            // Update list of log files
            self.logSearch = {
                after: null,
                before: null,
                exclude_events: true,
                mime_type: "text/plain",
                camera_ids: [selected],
                limit: 20,
                skip: 0,
                semantic_type: "meteorpi:logfile"
            };
            var search = utils.getSearchObject(self.logSearch, {skip: 0});
            client.searchFiles(search, function (error, results) {
                jQuery.each(results.files, function (index, item) {
                    item.url = client.filenameForFile(item);
                    item.title = new Date(item.file_time);
                });
            });
        }
        else {
            $.each(self.markers, function (index, marker) {
                marker.setMap(self.map);
            });
        }
        google.maps.event.trigger(self.map, "resize");
    };

    StatusPage.prototype.refreshCamera = function () {
        var self = this;
        self.setCamera(self.selectedCamera());
    };

    StatusPage.prototype.setTime = function (ut) {
        var self = this;
        self.time(new Date(ut));
        self.refreshCamera();
    };

    StatusPage.prototype.dispose = function () {
        //
    };

    return {viewModel: StatusPage, template: templateMarkup};

})
;

/** status-page.js
 * Meteor Pi, Cambridge Science Centre
 * Dominic Ford, Tom Oinn
 */

define(['jquery', 'knockout', 'text!./status-page.html', 'client', 'utils'], function ($, ko, templateMarkup, client, utils) {

    function StatusPage(params) {
        var self = this;
        self.user = client.user;
        // Available cameras
        self.obstoryIds = ko.observableArray();
        // The selected value in the camera drop-down
        self.selectedObstory = ko.observable();
        // The status for this current camera
        self.obstoryObjs = {};
        self.obstoryMetadata = {};
        self.logFiles = ko.observableArray();
        self.markers = {};
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
        client.listObstories(function (err, obstoryObjs) {
            $.each(obstoryObjs, function (index, obstoryObj) {
                self.obstoryObjs[obstoryObj.publicId] = obstoryObj;
                client.getObstoryStatusAll(obstoryObj.publicId, function (err, metadata) {
                    self.obstoryMetadata[obstoryObj.publicId] = metadata;
                    var marker = new google.maps.Marker({
                        position: new google.maps.LatLng(obstoryObj.latitude, obstoryObj.longitude),
                        map: self.map,
                        title: obstoryObj.name
                    });
                    marker.addListener('click', function () {
                        self.setObstory(obstoryObj.publicId);
                    });
                    self.markers[obstoryObj.publicId] = marker;
                    self.obstoryIds.push(obstoryObj.publicId);
                    if (params.obstory && (params.obstory == obstoryObj.publicId)) self.setObstory(obstoryObj.publicId);
                });
            });
        });
    }

    /**
     * This is called whenever a value is set, including on first load, so
     * we can use it to initialise the status panel as well as to respond to
     * any user selections.
     */
    StatusPage.prototype.setObstory = function (selected) {
        var self = this;
        if ((selected == null) || !jQuery.inArray(selected,self.obstoryIds)) selected=null;
        self.selectedObstory(selected);
        if (selected != null) {
            self.map.setCenter(new google.maps.LatLng(self.obstoryObjs[selected].latitude,
                self.obstoryObjs[selected].longitude));

            // Update list of log files
            self.logSearch = {
                after: 0,
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
                    item.url = client.urlForFile(item);
                    item.title = new Date(item.file_time);
                });
                self.logFiles(results.files);
            });
        }
        else {
            self.logFiles([]);
        }
        google.maps.event.trigger(self.map, "resize");
    };

    StatusPage.prototype.dispose = function () {
        //
    };

    return {viewModel: StatusPage, template: templateMarkup};

})
;

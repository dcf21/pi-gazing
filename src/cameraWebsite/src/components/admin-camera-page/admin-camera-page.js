define(['knockout', 'text!./admin-camera-page.html', 'client'], function (ko, templateMarkup, client) {

    function AdminCameraPage(route) {
        var self = this;
        // Available cameras
        self.cameras = ko.observableArray();
        // The selected value in the camera drop-down
        self.selectedCamera = ko.observable();

        // Get the cameras
        client.listCameras(function (err, cameras) {
            self.cameras(cameras);
        });
        self.imageURL = ko.observable("https://placekitten.com/g/600/500");

        self.status_id = ko.observable();

        self.status = {
            inst_name: ko.observable(),
            inst_url: ko.observable(),
            regions: ko.observableArray()
        };
    }

    AdminCameraPage.prototype.setStatus = function (status) {
        var self = this;
        if (status != null) {
            self.status.inst_name(status.inst_name);
            self.status.inst_url(status.inst_url);
            self.status_id(status.status_id);
            self.status.regions(status.regions);
            var nonKitten = {
                semantic_type: 'meteorpi:timelapse/frame',
                limit: 1,
                camera_ids: self.status.camera_id
            };
            client.searchFiles(nonKitten, function (error, results) {
                if (results.files.length == 0) {
                    self.imageURL("https://placekitten.com/g/600/500")
                }
                else {
                    fileRecord = results.files[0];
                    self.imageURL(client.urlForFile(fileRecord));
                }
            });
        } else {
            self.status_id(null);
            self.status.inst_name(null);
            self.status.inst_url(null);
            self.status.regions([]);
        }
    };

    /**
     * This is called whenever a value is set, including on first load, so
     * we can use it to initialise the status panel as well as to respond to
     * any user selections.
     */
    AdminCameraPage.prototype.setCamera = function () {
        var self = this;
        var selected = ko.unwrap(self.selectedCamera());
        if (selected != null) {
            client.getStatus(selected, null, function (err, status) {
                self.setStatus(status);
            });
        } else {
            self.setStatus(null);
            self.imageURL(null);
        }
    };

    AdminCameraPage.prototype.saveChanges = function () {
        var self = this;
        client.updateCameraStatus(self.selectedCamera(), ko.toJS(self.status), function (err, updated_status) {
            self.setStatus(updated_status);
        });
    };

    AdminCameraPage.prototype.dispose = function () {
        //
    };

    return {viewModel: AdminCameraPage, template: templateMarkup};

});

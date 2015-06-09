define(['knockout', 'text!./admin-camera-page.html', 'client'], function (ko, templateMarkup, client) {

    function AdminCameraPage(route) {
        var self = this;
        // Available cameras
        self.cameras = ko.observableArray();
        // The selected value in the camera drop-down
        self.selectedCamera = ko.observable();
        // The status for this current camera
        self.status = ko.observable();
        // Get the cameras
        client.listCameras(function (err, cameras) {
            self.cameras(cameras);
        });
    }

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
                self.status(status);
            });
        }
    };

    AdminCameraPage.prototype.dispose = function () {
        //
    };

    return {viewModel: AdminCameraPage, template: templateMarkup};

});

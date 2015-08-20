define(['knockout', 'text!./status-page.html', 'client'], function (ko, templateMarkup, client) {

    function StatusPage(params) {
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
            if (params.camera && (params.camera in cameras)) self.setCamera(params.camera);
        });
    }

    /**
     * This is called whenever a value is set, including on first load, so
     * we can use it to initialise the status panel as well as to respond to
     * any user selections.
     */
    StatusPage.prototype.setCamera = function () {
        var self = this;
        var selected = ko.unwrap(self.selectedCamera());
        if (selected != null) {
            client.getStatus(selected, null, function (err, status) {
                self.status(status);
            });
        }
    };

    StatusPage.prototype.dispose = function () {
        //
    };

    return {viewModel: StatusPage, template: templateMarkup};

});

define(["knockout", "text!./home.html", "client", "router"], function (ko, homeTemplate, client, router) {

    function HomeViewModel(route) {
        var self = this;
        // Available cameras
        self.cameras = ko.observableArray();
        // The selected value in the camera drop-down
        self.selectedCamera = ko.observable();
        // The status for this current camera
        self.status = ko.observable();
        self.imageURL = ko.observable("https://placekitten.com/g/600/500");
        self.polygons = ko.observableArray();
        self.polygons([[{x: 0, y: 0}, {x: 100, y: 100}, {x: 0, y: 100}],
            [{x: 200, y: 200}, {x: 400, y: 400}, {x: 200, y: 300}],
            [{x: 500, y: 200}, {x: 300, y: 300}, {x: 200, y: 200}, {x: 140, y: 100}]]);
        self.status.subscribe(function (newValue) {
            console.log(newValue);
        });
        client.listCameras(function (err, cameras) {
            self.cameras(cameras);
        });

    }

    /**
     * This is called whenever a value is set, including on first load, so
     * we can use it to initialise the status panel as well as to respond to
     * any user selections.
     */
    HomeViewModel.prototype.setCamera = function () {
        var self = this;
        var selected = ko.unwrap(self.selectedCamera());
        if (selected != null) {
            client.getStatus(selected, null, function (err, status) {
                self.status(status);
            });
        }
    };

    HomeViewModel.prototype.listCameras = function () {
        var self = this;
        client.listCameras(function (err, cameras) {
            self.message(cameras);
        });
    };

    HomeViewModel.prototype.searchEvents = function () {
        var self = this;
        client.searchEvents(new model.EventSearch(), function (err, results) {
            self.message(results.map(function (item) {
                return JSON.stringify(item)
            }));
        });
    };

    HomeViewModel.prototype.searchFiles = function () {
        var search = new model.FileRecordSearch();
        search.setExcludeEvents();
        search.setBefore(new Date(Date.now()));
        router.goTo("files", {search: search.getSearchString()});
    };

    return {viewModel: HomeViewModel, template: homeTemplate};

});

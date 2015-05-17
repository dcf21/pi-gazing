define(["knockout", "text!./home.html", "client", "model"], function (ko, homeTemplate, client, model) {


    function HomeViewModel(route) {
        this.message = ko.observable('Welcome to MeteorPi Camera Control!');
    }

    HomeViewModel.prototype.listCameras = function () {
        var self = this;
        client.listCameras(function (err, cameras) {
            self.message('Cameras are ' + cameras);
        });
        self.message('Fetching cameras...');
    };

    HomeViewModel.prototype.searchEvents = function () {
        var self = this;
        client.searchEvents({}, function (err, results) {
            self.message('Results are ' + results.map(function (item) {
                    return JSON.stringify(item)
                }));
        });
    };

    HomeViewModel.prototype.searchFiles = function () {
        var self = this;
        client.searchFiles(new model.FileRecordSearch().setExcludeEvents(), function (err, results) {
            self.message('Results are ' + results.map(function (item) {
                    return JSON.stringify(item)
                }));
        });
    };

    return {viewModel: HomeViewModel, template: homeTemplate};

});

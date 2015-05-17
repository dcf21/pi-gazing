define(["knockout", "text!./home.html", "client", "model"], function (ko, homeTemplate, client, model) {


    function HomeViewModel(route) {
        this.message = ko.observable('Welcome to MeteorPi Camera Control!');
    }

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
        var self = this;
        client.searchFiles(new model.FileRecordSearch().setExcludeEvents().setBefore(new Date(Date.now())), function (err, results) {
            self.message(results.map(function (item) {
                return JSON.stringify(item)
            }));
        });
    };

    return {viewModel: HomeViewModel, template: homeTemplate};

});

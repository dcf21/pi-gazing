define(["knockout", "text!./home.html", "client", "model", "router"], function (ko, homeTemplate, client, model, router) {


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
        var search = new model.FileRecordSearch();
        search.setExcludeEvents();
        search.setBefore(new Date(Date.now()));
        router.goTo("file-results", {search: search.getSearchString()});
    };


    return {viewModel: HomeViewModel, template: homeTemplate};

});

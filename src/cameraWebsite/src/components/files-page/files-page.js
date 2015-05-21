define(['knockout', 'text!./files-page.html', 'client', 'router'], function (ko, templateMarkup, client, router) {

    function FilesPage(params) {
        var self = this;

        self.search = {
            after: ko.observable(),
            before: ko.observable(),
            exclude_events: ko.observable(false)
        };

        self.results = ko.observableArray();

        if (params.search) {
            // Configure the observable from the search
            client.populateObservables(self.search, params.search, {
                "before": "date",
                "after": "date",
                "exclude_events": "bool"
            });
            client.searchFiles(self.search, function (error, results) {
                self.results(results);
            });
        }

    }

    FilesPage.prototype.searchFiles = function () {
        var self = this;
        router.goTo("files", {"search": client.stringFromObservables(self.search)})
    };

    // This runs when the component is torn down. Put here any logic necessary to clean up,
    // for example cancelling setTimeouts or disposing Knockout subscriptions/computeds.
    FilesPage.prototype.dispose = function () {
    };

    return {viewModel: FilesPage, template: templateMarkup};

});

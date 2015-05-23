define(['knockout', 'text!./files-page.html', 'client', 'router'], function (ko, templateMarkup, client, router) {


    function FilesPage(params) {

        var self = this;


        self.search = {
            after: ko.observable(),
            before: ko.observable(),
            exclude_events: ko.observable(false),
            after_offset: ko.observable(),
            before_offset: ko.observable()
        };

        /**
         * Computed value, maps between the numeric value actually held in the search observable
         * and the date model required by the various UI components.
         */
        self.afterOffsetDate = client.wrapTimeOffsetObservable(self.search.after_offset);
        self.beforeOffsetDate = client.wrapTimeOffsetObservable(self.search.before_offset);

        /**
         * Used to set up the range shown by the time picker
         */
        self.minTime = new Date(2000, 0, 1, 15, 0, 0);
        self.maxTime = new Date(2000, 0, 1, 10, 0, 0);

        self.results = ko.observableArray();

        self.urlForFile = client.urlForFile;
        self.filenameForFile = client.filenameForFile;

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

})
;

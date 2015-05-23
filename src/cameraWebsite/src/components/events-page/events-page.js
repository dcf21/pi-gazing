define(['knockout', 'text!./events-page.html', 'client', 'router'], function (ko, templateMarkup, client, router) {

    function EventsPage(params) {
        var self = this;

        self.search = {
            after: ko.observable(),
            before: ko.observable(),
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
                "after": "date"
            });
            client.searchEvents(self.search, function (error, results) {
                self.results(results);
            });
        }

    }

    EventsPage.prototype.searchEvents = function () {
        var self = this;
        router.goTo("events", {"search": client.stringFromObservables(self.search)})
    };

    // This runs when the component is torn down. Put here any logic necessary to clean up,
    // for example cancelling setTimeouts or disposing Knockout subscriptions/computeds.
    EventsPage.prototype.dispose = function () {
    };

    return {viewModel: EventsPage, template: templateMarkup};

});

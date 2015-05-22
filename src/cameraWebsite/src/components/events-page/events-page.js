define(['knockout', 'text!./events-page.html', 'client', 'router'], function (ko, templateMarkup, client, router) {

    function EventsPage(params) {
        var self = this;

        self.search = {
            after: ko.observable(),
            before: ko.observable(),
            exclude_events: ko.observable(false)
        };

        self.results = ko.observableArray();

        self.urlForFileId = client.urlForFileId;

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

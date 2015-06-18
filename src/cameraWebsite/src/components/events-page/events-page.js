define(['knockout', 'text!./events-page.html', 'client', 'router', 'jquery', 'utils'], function (ko, templateMarkup, client, router, jquery, utils) {

    function EventsPage(params) {
        var self = this;

        self.search = {
            after: ko.observable(),
            before: ko.observable(),
            after_offset: ko.observable(),
            before_offset: ko.observable(),
            event_type: ko.observable(),
            limit: ko.observable(20),
            skip: ko.observable(),
            meta: ko.observableArray()
        };

        self.results = ko.observableArray();
        self.resultCount = ko.observable(0);
        self.firstResultIndex = ko.observable(0);
        self.pages = ko.observableArray();
        self.hasQuery = ko.observable();

        self.urlForFile = client.urlForFile;
        self.filenameForFile = client.filenameForFile;


        if (params.search) {
            utils.updateSearchObject(self.search, params.search);
            // Get the search object and use it to retrieve results
            var search = utils.getSearchObject(self.search, {skip: 0});
            // Reset the skip parameter, if any
            self.search.skip(0);
            client.searchEvents(search, function (error, results) {
                self.results(results.events);
                self.resultCount(results.count);
                self.firstResultIndex(search.hasOwnProperty("skip") ? search.skip : 0);
                self.pages(utils.getSearchPages(search, results.events.length, results.count));
                self.hasQuery(true);
            });
        } else {
            self.hasQuery(false);
        }

        self.changePage = function () {
            // 'this' is bound to the page object clicked on, the search property of this
            // object contains the search corresponding to that page of results.
            router.goTo("events", {"search": utils.encodeString(this.search)});
        };

        self.searchEvents = function () {
            router.goTo("events", {"search": utils.encodeString(utils.getSearchObject(self.search))})
        };
    }

    return {viewModel: EventsPage, template: templateMarkup};

});

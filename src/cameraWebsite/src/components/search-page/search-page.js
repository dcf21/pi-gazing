define(['knockout', 'text!./search-page.html', 'client', 'router', 'utils'], function (ko, templateMarkup, client, router, utils) {


    function FilesPage(params) {

        var self = this;

        self.searchTypes = ["Timelapse images","Moving objects"];

        self.inputs = {
            after: ko.observable(),
            before: ko.observable(),
            camera: ko.observable("Any"),
            flag_bgsub: ko.observable(false),
            flag_highlights: ko.observable(true),
            flag_lenscorr: ko.observable(false),
            searchtype: ko.observable(self.searchTypes[0]),
            skyclarity: ko.observable(0),
            duration_min: ko.observable(0),
            duration_max: ko.observable(60),
            limit: ko.observable(20),
            skip: ko.observable()
        }

        self.search = {
            after: ko.computed( function() { return self.inputs.after; } ),
            before: ko.computed( function() { return self.inputs.before; } ),
            exclude_events: ko.computed( function() { return self.inputs.searchtype()==self.searchTypes[0]; } ),
            camera_ids: ko.computed( function() { return (self.inputs.camera()=="Any")?"":self.inputs.camera; } ),
            limit: ko.computed( function() { return self.inputs.limit; } ),
            skip: ko.computed( function() { return self.inputs.skip; } ),
            meta: ko.computed( function() {
                constraints = [];
                if (self.inputs.searchtype()!=self.searchTypes[0] && self.inputs.duration_min()>0) constraints.push({
                    type: ko.observable('greater'),
                    key: ko.observable('meteorpi:duration'),
                    number_value: self.inputs.duration_min,
                    string_value: ko.observable(''),
                    date_value: ko.observable(new Date(Date.now()))
                });
                if (self.inputs.searchtype()!=self.searchTypes[0] && self.inputs.duration_max()>0) constraints.push({
                    type: ko.observable('less'),
                    key: ko.observable('meteorpi:duration'),
                    number_value: self.inputs.duration_max,
                    string_value: ko.observable(''),
                    date_value: ko.observable(new Date(Date.now()))
                });
                if (self.inputs.searchtype()==self.searchTypes[0] && self.inputs.skyclarity()>0) constraints.push({
                    type: ko.observable('greater'),
                    key: ko.observable('meteorpi:skyClarity'),
                    number_value: self.inputs.skyclarity,
                    string_value: ko.observable(''),
                    date_value: ko.observable(new Date(Date.now()))
                });
                return constraints;
            }),
            semantic_type: ko.computed( function() {
                imgType = "meteorpi:timelapse/frame";
                if (self.inputs.flag_bgsub) imgType+="/bgrdSub";
                if (self.inputs.flag_lenscorr) imgType+="/lensCorr";
                return imgType;
            } ),
        };

        self.results = ko.observableArray();
        self.resultCount = ko.observable(0);
        self.firstResultIndex = ko.observable(0);
        self.pages = ko.observableArray();
        self.hasQuery = ko.observable();

        self.urlForFile = client.urlForFile;
        self.filenameForFile = client.filenameForFile;

        if (params.search) {
            utils.updateSearchObject(self.inputs, params.search);
            // Get the search object and use it to retrieve results
            var search = utils.getSearchObject(self.search, {skip: 0});
            // Reset the skip parameter, if any
            self.inputs.skip(0);
            if (self.inputs.searchtype()==self.searchTypes[0]) {
                client.searchFiles(search, function (error, results) {
                    self.results(results.files);
                    self.resultCount(results.count);
                    self.firstResultIndex(search.hasOwnProperty("skip") ? search.skip : 0);
                    self.pages(utils.getSearchPages(search, results.files.length, results.count));
                    self.hasQuery(true);
                });
            } else {
                client.searchEvents(search, function (error, results) {
                    self.results(results.events);
                    self.resultCount(results.count);
                    self.firstResultIndex(search.hasOwnProperty("skip") ? search.skip : 0);
                    self.pages(utils.getSearchPages(search, results.events.length, results.count));
                    self.hasQuery(true);
                });
            }
        } else {
            self.hasQuery(false);
        }

        self.changePage = function () {
            // 'this' is bound to the page object clicked on, the search property of this
            // object contains the search corresponding to that page of results.
            router.goTo("skysearch", {"search": utils.encodeString(this.inputs)});
        };

        self.searchFiles = function () {
            router.goTo("skysearch", {"search": utils.encodeString(utils.getSearchObject(self.inputs))})
        };

    }

    return {viewModel: FilesPage, template: templateMarkup};

});

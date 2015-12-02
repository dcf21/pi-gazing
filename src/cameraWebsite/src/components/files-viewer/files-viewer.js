define(['knockout', 'text!./files-viewer.html', 'client', 'router', 'utils'], function (ko, templateMarkup, client, router, utils) {


    function FilesViewer(params) {

        var self = this;

        self.searchTypes = ["Moving objects", "Timelapse images"];

        self.search = {
            after: ko.observable(0),
            before: ko.observable(0),
            camera_ids: ko.observable("Any"),
            searchtype: ko.observable(self.searchTypes[0]),
            semantic_type: ko.observable("meteorpi:timelapse/frame"),
            limit: ko.observable(1),
            skip: ko.observable(0)
        }

        self.results = ko.observableArray();
        self.resultCount = ko.observable(0);
        self.firstResultIndex = ko.observable(0);
        self.pages = ko.observableArray();
        self.hasQuery = ko.observable();

        self.urlForFile = client.urlForFile;
        self.filenameForFile = client.filenameForFile;

        if (params.search) {
            utils.updateSearchObject(self.search, params.search);
            self.search.limit(1);
            // Get the search object and use it to retrieve results
            var search = utils.getSearchObject(self.search, {skip: 0});
            if (self.search.searchtype() == self.searchTypes[0]) {
                client.searchFiles(search, function (error, results) {
                    self.results(results.files);
                    self.resultCount(results.count);
                    self.firstResultIndex(0);
                    self.hasQuery(true);
                });
            } else {
                client.searchEvents(search, function (error, results) {
                    $.each(results.events, function (index, item) {
                        item.imgURL = '';
                        item.imgFname = '';
                        $.each(item.files, function (index, f) {
                            if (f.semantic_type == 'meteorpi:triggers/event') {
                                item.imgURL = self.urlForFile(f);
                                item.imgfname = self.filenameForFile(f);
                            }
                        });
                    });
                    self.results(results.events);
                    self.resultCount(results.count);
                    self.firstResultIndex(0);
                    self.hasQuery(true);
                });
            }
        } else {
            self.hasQuery(false);
        }

        self.searchFiles = function () {
            router.goTo("skysearch", {"search": utils.encodeString(utils.getSearchObject({"camera": self.search.camera_ids}))});
        };

        self.cameraInfo = function () {
            router.goTo("status", {"camera": utils.encodeString(self.search.camera_ids)});
        };

    }

    return {viewModel: FilesViewer, template: templateMarkup};

});

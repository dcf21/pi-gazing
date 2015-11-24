define(['jquery', 'knockout', 'text!./search-page.html', 'client', 'router', 'utils'], function (jQuery, ko, templateMarkup, client, router, utils) {


    function FilesPage(params) {

        var self = this;

        self.searchTypes = ["Moving objects", "Timelapse images"];

        var cameraDefault = "Any";
        var searchTerms = [];
        if (params.search) searchTerms = utils.decodeString(params.search);
        if (searchTerms.camera) cameraDefault = searchTerms.camera;

        self.inputs = {
            after: ko.observable(),
            before: ko.observable(),
            camera: ko.observable("Any"),
            flag_bgsub: ko.observable(false),
            flag_highlights: ko.observable(true),
            flag_lenscorr: ko.observable(true),
            searchtype: ko.observable(self.searchTypes[0]),
            skyclarity: ko.observable(0),
            duration_min: ko.observable(0),
            duration_max: ko.observable(60),
            limit: ko.observable(20),
            skip: ko.observable(0)
        };

        // Available cameras
        self.cameras = ko.observableArray(["Any"]);
        // Get the cameras
        client.listCameras(function (err, cameras) {
            var camerasTrimmed = ["Any"];
            jQuery.each(cameras, function(index,item){camerasTrimmed.push(item.trim())});
            camerasTrimmed.sort();
            self.cameras(camerasTrimmed);
            self.inputs.camera(cameraDefault);
        });

        self.search = {
            after: ko.computed(function () {
                return self.inputs.after;
            }),
            before: ko.computed(function () {
                return self.inputs.before;
            }),
            exclude_events: ko.computed(function () {
                return self.inputs.searchtype() == self.searchTypes[0];
            }),
            mime_type: ko.computed(function () {
                return (self.inputs.searchtype() == self.searchTypes[0]) ? 'image/png' : '';
            }),
            camera_ids: ko.computed(function () {
                return (self.inputs.camera() == "Any") ? null : self.inputs.camera;
            }),
            limit: ko.computed(function () {
                return self.inputs.limit;
            }),
            skip: ko.computed(function () {
                return self.inputs.skip;
            }),
            meta: ko.computed(function () {
                var constraints = [];
                if (self.inputs.searchtype() == self.searchTypes[1] && self.inputs.flag_highlights()) constraints.push({
                    type: ko.observable('greater'),
                    key: ko.observable('meteorpi:highlight'),
                    number_value: 0.5,
                    string_value: ko.observable(''),
                    date_value: ko.observable(new Date(Date.now()))
                });
                if (self.inputs.searchtype() != self.searchTypes[1] && self.inputs.duration_min() > 0) constraints.push({
                    type: ko.observable('greater'),
                    key: ko.observable('meteorpi:duration'),
                    number_value: self.inputs.duration_min,
                    string_value: ko.observable(''),
                    date_value: ko.observable(new Date(Date.now()))
                });
                if (self.inputs.searchtype() != self.searchTypes[1] && self.inputs.duration_max() > 0) constraints.push({
                    type: ko.observable('less'),
                    key: ko.observable('meteorpi:duration'),
                    number_value: self.inputs.duration_max,
                    string_value: ko.observable(''),
                    date_value: ko.observable(new Date(Date.now()))
                });
                if (self.inputs.searchtype() == self.searchTypes[1] && self.inputs.skyclarity() > 0) constraints.push({
                    type: ko.observable('greater'),
                    key: ko.observable('meteorpi:skyClarity'),
                    number_value: self.inputs.skyclarity,
                    string_value: ko.observable(''),
                    date_value: ko.observable(new Date(Date.now()))
                });
                return constraints;
            }),
            semantic_type: ko.computed(function () {
                var imgType = "meteorpi:timelapse/frame";
                if (self.inputs.flag_bgsub()) imgType += "/bgrdSub";
                if (self.inputs.flag_lenscorr()) imgType += "/lensCorr";
                return imgType;
            })
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
            if (self.inputs.searchtype() == self.searchTypes[1]) {
                client.searchFiles(search, function (error, results) {
                    self.pages(utils.getSearchPages(self.inputs, results.files.length, results.count));
                    jQuery.each(results.files, function (index, item) {
                        item.linkurl = '#' + router.routes['file'].interpolate({
                                "search": utils.encodeString(utils.getSearchObject(
                                    {
                                        'camera_ids': item.camera_id,
                                        'searchtype': self.searchTypes[1],
                                        'semantic_type': item.semantic_type,
                                        'before': item.file_time + 1000,
                                        'after': item.file_time - 1000
                                    }))
                            });
                    });
                    self.results(results.files);
                    self.resultCount(results.count);
                    self.firstResultIndex(self.inputs.skip());
                    self.hasQuery(true);
                });
            } else {
                client.searchEvents(search, function (error, results) {
                    self.pages(utils.getSearchPages(self.inputs, results.events.length, results.count));
                    jQuery.each(results.events, function (index, item) {
                        item.imgURL = '';
                        item.imgFname = '';
                        item.duration = 0;
                        item.linkurl = '#' + router.routes['file'].interpolate({
                                "search": utils.encodeString(utils.getSearchObject(
                                    {
                                        'camera_ids': item.camera_id,
                                        'searchtype': self.searchTypes[0],
                                        'before': item.event_time + 1000,
                                        'after': item.event_time - 1000
                                    }))
                            });
                        jQuery.each(item.files, function (index, f) {
                            if (f.semantic_type == 'meteorpi:triggers/event/maxBrightness/lensCorr') {
                                item.imgURL = self.urlForFile(f);
                                item.imgfname = self.filenameForFile(f);
                            }
                        });
                        jQuery.each(item.meta, function (index, m) {
                            if (m.key == 'meteorpi:duration') item.duration = "Duration: "+m.value.toFixed(2)+" sec";
                        });
                    });
                    self.results(results.events);
                    self.resultCount(results.count);
                    self.firstResultIndex(self.inputs.skip());
                    self.hasQuery(true);
                });
            }
        } else {
            self.hasQuery(false);
        }

        self.changePage = function () {
            // 'this' is bound to the page object clicked on, the search property of this
            // object contains the search corresponding to that page of results.
            router.goTo("skysearch", {"search": utils.encodeString(this.search)});
        };

        self.searchFiles = function () {
            self.inputs.skip(0);
            router.goTo("skysearch", {"search": utils.encodeString(utils.getSearchObject(self.inputs))})
        };

    }

    return {viewModel: FilesPage, template: templateMarkup};

});

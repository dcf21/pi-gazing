define(['knockout', 'text!./files-page.html', 'client', 'router', 'jquery'], function (ko, templateMarkup, client, router, jquery) {


    function FilesPage(params) {

        var self = this;


        self.search = {
            after: ko.observable(),
            before: ko.observable(),
            exclude_events: ko.observable(false),
            after_offset: ko.observable(),
            before_offset: ko.observable()
        };

        self.meta = ko.observableArray();

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

        /**
         * Function called from the UI to remove the given meta constraint from the list
         * @param meta
         */
        self.removeMeta = function (meta) {
            self.meta.remove(meta);
        };

        if (params.search) {
            // Configure the observable from the search
            client.populateObservables(self.search, params.search, {
                "before": "date",
                "after": "date",
                "exclude_events": "bool"
            });
            // Configure the observable array of file meta
            var sourceMeta = JSON.parse(decodeURIComponent(params.search))['meta_constraints'];
            if (sourceMeta) {
                ko.utils.arrayForEach(sourceMeta, function (meta) {
                    var type = meta['type'];
                    var isNumber = (type == "less" || type == "greater" || type == "number_equals");
                    var isDate = (type == "after" || type == "before");
                    var isString = (type == "string_equals");
                    d = {
                        type: ko.observable(type),
                        key: ko.observable(meta['key']),
                        string_value: ko.observable(isString ? meta['value'] : ''),
                        date_value: ko.observable(isDate ? new Date(meta['value'] * 1000) : new Date(Date.now())),
                        number_value: ko.observable(isNumber ? meta['value'] : 0)
                    };
                    self.meta.push(d);
                });
            }
            // Get the search object and use it to retrieve results
            var search = self.getSearchObject();
            client.searchFiles(search, function (error, results) {
                self.results(results);
            });
        }
    }

    FilesPage.prototype.addMeta = function () {
        var self = this;
        self.meta.push({
            type: ko.observable('string_equals'),
            key: ko.observable('meteorpi:meta_key_1'),
            string_value: ko.observable('meta_value_1'),
            date_value: ko.observable(new Date(Date.now())),
            number_value: ko.observable(0)
        });
    };

    FilesPage.prototype.getSearchObject = function () {
        var self = this;
        // Build the appropriate file meta query to send to the server
        var meta = self.meta.map(function (m) {
            var func = {};
            var type = ko.unwrap(m.type);
            if (type == "string_equals") {
                func.value = ko.unwrap(m.string_value);
                if (func.value.length == 0) {
                    func.value = null;
                }
            } else if (type == "after" || type == "before") {
                if (ko.unwrap(m.date_value) != null) {
                    func.value = ko.unwrap(m.date_value).getTime() / 1000.0;
                } else {
                    func.value = null;
                }
            } else if (type == "less" || type == "greater" || type == "number_equals") {
                func.value = ko.unwrap(m.number_value);
            }
            if (func.value == null) {
                return null;
            }
            return {
                key: ko.unwrap(m.key),
                type: type,
                value: func.value
            }
        }).filter(function (m) {
            return m != null;
        });
        var search = jquery.extend({}, self.search, {meta_constraints: meta});
        return search;
    };

    FilesPage.prototype.searchFiles = function () {
        var self = this;
        router.goTo("files", {"search": client.stringFromObservables(self.getSearchObject())})
    };

// This runs when the component is torn down. Put here any logic necessary to clean up,
// for example cancelling setTimeouts or disposing Knockout subscriptions/computeds.
    FilesPage.prototype.dispose = function () {
    };

    return {viewModel: FilesPage, template: templateMarkup};

})
;

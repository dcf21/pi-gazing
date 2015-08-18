define(['knockout', 'text!./search-editor.html', 'utils', 'jquery', 'client'], function (ko, templateMarkup, utils, jquery, client) {

    function SearchEditor(params) {
        var self = this;
        // Available cameras
        self.cameras = ko.observableArray(["Any"]);
        // Get the cameras
        client.listCameras(function (err, cameras) { self.cameras(["Any"].concat(cameras)); });

        self.searchTypes = ["Timelapse images","Moving objects"];

        self.search = params.search;
        if (params.hasOwnProperty('onSearch')) {
            self.performSearch = params.onSearch;
        } else {
            self.performSearch = false;
        }

        /**
         * Used to set up the range shown by the time picker
         */
        self.minTime = new Date(2000, 0, 1, 15, 0, 0);
        self.maxTime = new Date(2000, 0, 1, 10, 0, 0);

        /**
        self.removeMeta = function (meta) {
            console.log(self);
            self.search.meta.remove(meta);
        };

        self.addMeta = function () {
            self.search.meta.push({
                type: ko.observable('string_equals'),
                key: ko.observable('meteorpi:meta_key_1'),
                string_value: ko.observable('meta_value_1'),
                date_value: ko.observable(new Date(Date.now())),
                number_value: ko.observable(0)
            });
        };
         */
    }

    // This runs when the component is torn down. Put here any logic necessary to clean up,
    // for example cancelling setTimeouts or disposing Knockout subscriptions/computeds.
    SearchEditor.prototype.dispose = function () {
        jquery("body > div").slice(1).remove();
    };

    return {viewModel: SearchEditor, template: templateMarkup, synchronous: true};

});

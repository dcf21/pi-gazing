/** chart-triggerrate.js
 * Meteor Pi, Cambridge Science Centre
 * Dominic Ford, Tom Oinn
 */

define(['knockout', 'text!./chart-triggerrate.html', 'utils', 'jquery', 'client', 'dcfplot'], function (ko, templateMarkup, utils, jQuery, client, dcfplot) {

    function TriggerRatePlot(params, componentInfo) {
        var self = this;

        self.element = componentInfo.element;
        self.holder = $(componentInfo.element).find('.plotholder');
        self.canvas = $(componentInfo.element).find('.plotcanvas');
        self.haveData = ko.observable(false);
        // Input parameters
        self.camera = params.camera;
        self.time = params.time;

        self.plotobj = ko.computed(function () {
            self.search = {
                before: self.time,
                exclude_events: false,
                camera_ids: self.camera,
                limit: 250,
                skip: 0,
                semantic_type: "meteorpi:triggers/event"
            };

            self.binsize = 3600;
            self.histogram = {};
            self.tmin = 0;
            self.tmax = 0;
            var search = utils.getSearchObject(self.search, {skip: 0});
            client.searchFiles(search, function (error, results) {
                $.each(results.files, function (index, item) {
                    var ut = item.file_time / 1000;
                    var datum = 0;
                    $.each(item.meta, function (index, m) {
                        if (m.key == 'meteorpi:skyClarity') datum = m.value;
                    });
                    var bin = Math.floor(ut / self.binsize) * self.binsize;
                    if ((!self.tmin) || (bin < self.tmin)) self.tmin = bin;
                    if ((!self.tmax) || (bin > self.tmax)) self.tmax = bin;
                    if (!(bin in self.histogram)) self.histogram[bin] = 1;
                    else {
                        self.histogram[bin] += 1;
                    }
                });

                self.datasets = [];
                var emptyDataset = {xdata: [], ydata: [], settings: {styles:['points'],pointsize:0.85}};
                var i, dataset = jQuery.extend(true, [], emptyDataset);
                for (i = self.tmin; i <= self.tmax; i += self.binsize) {
                    if (!(i in self.histogram)) {
                        if (dataset.xdata.length) {
                            self.datasets.push(dataset);
                            dataset = jQuery.extend(true, [], emptyDataset);
                        }
                    } else {
                        dataset.xdata.push(i);
                        dataset.ydata.push(self.histogram[i]);
                    }
                }
                self.datasets.push(dataset);
                self.haveData(self.tmax > self.tmin);
                return new dcfplot.graph(self.holder, self.canvas, self.datasets, {},
                    {label:'Date',date:1}, {label:'Triggers per hour', min: 0});
            });
        });
    }

    return {
        viewModel: {
            createViewModel: function (params, componentInfo) {
                return new TriggerRatePlot(params, componentInfo);
            }
        },
        template: templateMarkup, synchronous: true
    };

});

/** search-editor.js
 * Meteor Pi, Cambridge Science Centre
 * Dominic Ford, Tom Oinn
 */

define(['knockout', 'text!./search-editor.html', 'utils', 'jquery', 'client'], function (ko, templateMarkup, utils, jquery, client) {

    function SearchEditor(params, componentInfo) {
        var self = this;
        self.element = $(componentInfo.element);

        // Set up tooltips
        self.showHelp = false;
        self.tooltip_placement();
 
        $('#searchtype').click(function() { self.tooltip_placement(); });

        $('.help-toggle', self.element).click(function() {
            self.showHelp = !self.showHelp;
            self.tooltip_placement();
        });

        // Available cameras
        self.cameras = params.cameras;
        self.searchTypes = params.searchTypes;

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
    }

    SearchEditor.prototype.tooltip_placement = function () {
            $('[data-pos="tooltip-right"]', this.element).tooltip({'placement':'right'});
            $('[data-pos="tooltip-above"]', this.element).tooltip({'placement':'top'});
            $('[data-pos="tooltip-below"]', this.element).tooltip({'placement':'bottom'});
            $('[data-toggle="tooltip"]', this.element).tooltip( this.showHelp ? "show" : "hide");
    };

    // This runs when the component is torn down. Put here any logic necessary to clean up,
    // for example cancelling setTimeouts or disposing Knockout subscriptions/computeds.
    SearchEditor.prototype.dispose = function () {
        jquery("body > div").slice(1).remove();
    };

    return {viewModel: {createViewModel: function (params, componentInfo) {
                return new SearchEditor(params, componentInfo);
            }
        }, template: templateMarkup, synchronous: true};

});

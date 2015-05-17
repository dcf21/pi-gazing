/**
 * Created by tom on 17/05/15.
 */
define(function () {
    "use strict";

    function FileRecordSearch() {
        if (!(this instanceof FileRecordSearch)) {
            throw new TypeError("FileRecordSearch constructor cannot be called as a function.");
        }
    }

    FileRecordSearch.prototype = {

        constructor: FileRecordSearch,

        /**
         * Call to exclude FileRecord instances which are associated with an Event.
         * @returns {FileRecordSearch}
         */
        setExcludeEvents: function () {
            this.exclude_events = 1;
            return this;
        },

        /**
         * Call to force only the latest FileRecord or set of FileRecords
         * (where more than one result shares the same file time) to be returned.
         * @returns {FileRecordSearch}
         */
        setLatest: function () {
            this.latest = 1;
            return this;
        },

        /**
         * Used to build a URI component compatible string representing this search.
         * @returns {string}
         */
        getSearchString: function () {
            var string = encodeURIComponent(JSON.stringify(this));
            console.log(string);
            return string;
        }

    };

    return {
        FileRecordSearch: FileRecordSearch
    };

});
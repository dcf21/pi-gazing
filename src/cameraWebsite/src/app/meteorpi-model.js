/**
 * Created by tom on 17/05/15.
 */
define(["jquery"], function (jquery) {
    "use strict";

    /**
     * Used to map JS objects into JSON suitable for the meteorPi API
     * @param key
     * @param value
     * @returns {*}
     */
    var dateReplacer = function (key, value) {
        if (value == null) {
            return undefined;
        }
        if (jquery.type(this[key]) == "date") {
            return this[key].getTime() / 1000.0;
        }
        return value;
    };

    function FileRecordSearch() {
        if (!(this instanceof FileRecordSearch)) {
            throw new TypeError("FileRecordSearch constructor cannot be called as a function.");
        }
    }

    FileRecordSearch.prototype = {

        constructor: FileRecordSearch,

        setAfter: function (date) {
            this.after = date;
            return this;
        },

        setBefore: function (theDate) {
            this.before = theDate;
            return this;
        },

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
            var string = encodeURIComponent(JSON.stringify(this, dateReplacer));
            return string;
        }

    };

    function EventSearch() {
        if (!(this instanceof EventSearch)) {
            throw new TypeError("EventSearch constructor cannot be called as a function.");
        }
    }

    EventSearch.prototype = {

        constructor: EventSearch,

        setAfter: function (date) {
            this.after = date;
            return this;
        },

        setBefore: function (theDate) {
            this.before = theDate;
            return this;
        },

        getSearchString: function () {
            var string = encodeURIComponent(JSON.stringify(this, dateReplacer));
            return string;
        }

    };


    return {
        FileRecordSearch: FileRecordSearch,
        EventSearch: EventSearch
    };

});
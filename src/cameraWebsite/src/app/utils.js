/**
 * Created by tom on 18/06/15.
 */
define(["jquery", "knockout"], function (jquery, ko) {

    return {

        /**
         * Update a dict defining a search with values from an encoded search string as used in the URL fragments for
         * search pages.
         * @param search a dict containing search properties.
         * @param searchString a string containing the double encoded search JSON from which the search should be
         * built.
         */
        updateSearchObject: function (search, searchString) {
            var o = this.decodeString(searchString, {
                "before": "date",
                "after": "date"
            });
            var sourceMeta = [];
            if (o.hasOwnProperty("meta")) {
                sourceMeta = o.meta;
                delete o.meta;
            }
            this.populateObservables(search, o);
            if (search.hasOwnProperty("meta")) {
                search.meta([]);
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
                    search.meta.push(d);
                });
            }
        },


        /**
         * Get a serializable search object copy from a dict of observables. Metadata must be specified as a knockout
         * observable array within the search parameter with key "meta".  Creates a copy of the supplied object using
         * ko.toJS(..), then strips any values from the resultant dict that  are either null, undefined, empty arrays,
         * or where the supplied defaults dict has a key with the same name  as the property and the two values, those
         * in the copied dict and those in the default dict, are equal. This is used to strip out default values so we
         * can encode more efficiently.
         * @param search a dict of observables containing search parameters.
         * @param defaults optionally a dict of default values.
         */
        getSearchObject: function (search, defaults) {
            var copy = ko.toJS(search);
            if (search.hasOwnProperty("meta")) {
                // Build the appropriate meta constraints to send to the server
                copy.meta = ko.unwrap(search.meta).map(function (m) {
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
            }
            var isEmptyArray = function (o) {
                return (toString.call(o) === "[object Array]" && o.length == 0)
            };
            for (var key in copy) {
                if (copy.hasOwnProperty(key)) {
                    var val = copy[key];
                    if (val === null || val === undefined || isEmptyArray(val)) {
                        delete copy[key];
                    } else if (defaults != null && defaults.hasOwnProperty(key) && defaults[key] === val) {
                        delete copy[key];
                    }
                }
            }
            return copy;
        },

        /**
         * Get pages, where a page is a from index, to index, a search and whether the page is the current one.
         * @param searchObject a search object, as returned by getSearchObject
         * @param returnedResultCount the number of results which were returned by this search
         * @param totalResultCount the total number of results available for the search
         * @returns {Array} an array of {from, to, search, current}. If pagination is not applicable this array will
         * be empty.
         */
        getSearchPages: function (searchObject, returnedResultCount, totalResultCount) {
            var pages = [];
            var skip = searchObject.hasOwnProperty("skip") ? searchObject.skip : 0;
            // Only do pagination if we have a search limit
            if (searchObject.limit > 0 && (skip > 0 || returnedResultCount < totalResultCount)) {
                var i = 0;
                while (i < totalResultCount) {
                    var newSearch = jquery.extend(true, {}, searchObject);
                    newSearch.skip = i;
                    var page = {
                        from: i + 1,
                        to: Math.min(i + searchObject.limit, totalResultCount) + 1,
                        search: newSearch,
                        current: (skip == newSearch.skip)
                    };
                    pages.push(page);
                    i += searchObject.limit;
                }
            }
            return pages;
        },

        /**
         * Pull out values from an observable or other object and builds an encoded JSON string. Encoding is performed
         * twice to work around issues where encoded forward slash characters in URL fragments are rejected by certain
         * application servers (including Apache and some WSGI containers used behind such servers).
         *
         * Dates are encoded with value.getTime()/1000.0, boolean values are encoded by representing them as a '1' if
         * true and excluding them from the result if false.
         *
         * @param ob the object to encode, any immediate properties of this object will be included as will their
         * descendants. Values will be passed through ko.unwrap(..) so this method handles Knockout observables as well
         * as regular JS objects.
         * @returns {string} a double URL component encoded representation of the supplied object.
         */
        encodeString: function (ob) {
            var jsonString = JSON.stringify(ob, function (key, ob_value) {
                    var value = ko.unwrap(this.hasOwnProperty(key) ? this[key] : ob_value);
                    if (value == null || value == false) {
                        return undefined;
                    }
                    if (jquery.type(value) == "date") {
                        return value.getTime() / 1000.0;
                    }
                    if (typeof value === "boolean") {
                        return value ? 1 : undefined;
                    }
                    return value;
                }
            );
            return encodeURIComponent(encodeURIComponent(jsonString));
        },

        /**
         * Decode a string encoded twice with URI component encoding into a JSON object,
         * optionally mapping named keys to particular types.
         *
         * @param s the encoded string, as produced by the stringFromObservables function.
         * @param types a dict of key name to value, values can be either 'bool' or 'date'. In the case
         * of booleans the value is set to True if the key value is 1, and False otherwise. For dates the
         * value is treated as time since the unix epoch and converted to a Javascript
         * Date object with new Date(value * 1000) - Javascript having a higher time resolution than the server.
         */
        decodeString: function (s, types) {
            var jsonString = decodeURIComponent(decodeURIComponent(s));
            return JSON.parse(jsonString, function (key, value) {
                if (types && key) {
                    if (types[key] === "date") {
                        value = new Date(value * 1000);
                    }
                    if (types[key] === "bool") {
                        value = (value == 1);
                    }
                    if (types[key] === "skip") {
                        value = undefined;
                    }
                }
                return value;
            });
        },

        /**
         * Push values from a dict into a dict of observables, matching by key.
         * @param ob an observable or dictionary of observables
         * @param o a dict of decoded values.
         * @param types - a dict of keys to types, where a type can be 'date'
         * or 'bool' to handle mappings to those types particularly.
         */
        populateObservables: function (ob, o, types) {
            for (var key in ob) {
                if (ob.hasOwnProperty(key)) {
                    if (key in o) {
                        if (ko.isObservable(ob[key])) {
                            ob[key](ko.unwrap(o[key]));
                        } else {
                            ob[key] = o[key];
                        }
                    }
                }
            }
        },

        /**
         * Build and return a pure computed knockout observable which wraps up a supplied observable containing a time
         * offset and exposes a date. The date can be written or read and will update the underlying observable data
         * accordingly.
         * @param ob the observable to wrap to create the computed value.
         */
        wrapTimeOffsetObservable: function (ob) {
            /**
             * Take a number of seconds since mid-day and produce a date object representing that number of
             * seconds after 2000-1-1 12:00 PM. This can be used in e.g. a TimePicker to show the times.
             * @param offset
             * @returns {Date}
             */
            var secondsOffsetToDate = function (offset) {
                var midday = new Date(2000, 0, 1, 12, 0, 0);
                var theDate = new Date(2000, 0, 1, 12, 0, 0);
                theDate.setSeconds(midday.getSeconds() + offset);
                return theDate;

            };

            /**
             * Take a date, and return the number of seconds between that date and the most recent mid-day
             * @param date
             * @returns {*}
             */
            var dateToSecondsOffset = function (date) {
                if (date == null) {
                    return null;
                }
                var theDate;
                if (date.getHours() < 12) {
                    theDate = new Date(2000, 0, 2, date.getHours(), date.getMinutes(), 0);
                } else {
                    theDate = new Date(2000, 0, 1, date.getHours(), date.getMinutes(), 0);
                }
                var midday = new Date(2000, 0, 1, 12, 0, 0);
                return (theDate.getTime() - midday.getTime()) / 1000;
            };

            return ko.pureComputed({
                read: function () {
                    return secondsOffsetToDate(ob());
                },
                write: function (value) {
                    ob(dateToSecondsOffset(value));
                }
            });
        }
    };

});
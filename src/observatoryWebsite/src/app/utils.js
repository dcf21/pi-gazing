/** utils.js
 * Meteor Pi, Cambridge Science Centre
 * Dominic Ford, Tom Oinn
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
            var o = this.decodeString(searchString);
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
                    var isString = (type == "string_equals");
                    d = {
                        type: ko.observable(type),
                        key: ko.observable(meta['key']),
                        string_value: ko.observable(isString ? meta['value'] : ''),
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
            var skip  = searchObject.skip();
            var perPage = searchObject.limit();
            // Only do pagination if we have a search limit
            if (perPage>0 && (skip>0 || returnedResultCount<totalResultCount)) {
                var Npages = Math.ceil(totalResultCount/perPage);
                var pageCurrent = Math.floor(skip/perPage);
                var pageMin = Math.max(pageCurrent-5,0);
                var pageMax = Math.min(pageMin+9,Npages-1);
                for (var i=pageMin; i<=pageMax; i++) {
                    var newSearch = jquery.extend(true, {}, searchObject);
                    newSearch.skip = i*perPage;
                    var page = {
                        pageNo: i+1,
                        search: newSearch,
                        current: (skip == newSearch.skip)
                    };
                    pages.push(page);
                }
            }
            return pages;
        },

        /**
         * Pull out values from an observable or other object and builds an encoded JSON string. Encoding is performed
         * twice to work around issues where encoded forward slash characters in URL fragments are rejected by certain
         * application servers (including Apache and some WSGI containers used behind such servers).
         *
         * @param ob the object to encode, any immediate properties of this object will be included as will their
         * descendants. Values will be passed through ko.unwrap(..) so this method handles Knockout observables as well
         * as regular JS objects.
         * @returns {string} a double URL component encoded representation of the supplied object.
         */
        encodeString: function (ob) {
            var jsonString = JSON.stringify(ob, function (key, ob_value) {
                    var value = ko.unwrap(this.hasOwnProperty(key) ? this[key] : ob_value);
                    if (value == null) {
                        return undefined;
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
         */
        decodeString: function (s) {
            var jsonString = decodeURIComponent(decodeURIComponent(s));
            return JSON.parse(jsonString);
        },

        /**
         * Push values from a dict into a dict of observables, matching by key.
         * @param ob an observable or dictionary of observables
         * @param o a dict of decoded values.
         * or 'bool' to handle mappings to those types particularly.
         */
        populateObservables: function (ob, o) {
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
        }


    };

});
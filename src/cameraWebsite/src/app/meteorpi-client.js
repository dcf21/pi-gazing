/**
 * Created by tom on 17/05/15.
 */

define(["jquery", "knockout"], function (jquery, ko) {

    return new MeteorPiClient({
        urlPrefix: "http://localhost:12345/"
    });

    /**
     * Client to the MeteorPi REST API
     * @param config initialise with configuration parameters, currently only urlPrefix which is applied to all URLs
     * @constructor
     */
    function MeteorPiClient(config) {

        var self = this;

        var ajaxAuth = function (uri, method, data) {
            var request = {
                url: config.urlPrefix + uri,
                type: method,
                contentType: "application/json",
                accepts: "application/json",
                cache: false,
                dataType: 'jsonp',
                data: JSON.stringify(data),
                beforeSend: function (xhr) {
                    xhr.setRequestHeader("Authorization",
                        "Basic " + btoa(self.username + ":" + self.password));
                }
            };
            return jquery.ajax(request)
        };

        var ajax = function (uri, method, data) {
            var request = {
                url: config.urlPrefix + uri,
                type: method,
                contentType: "application/json",
                accepts: "application/json",
                cache: false,
                dataType: 'jsonp'
            };
            if (data != null) {
                request.data = JSON.stringify(data)
            }
            return jquery.ajax(request)
        };

        var applyCallback = function (request, name, callback) {
            request.done(function (data) {
                callback(null, data[name]);
            });
            request.fail(function (jqXHR, textStatus) {
                callback(textStatus, null)
            });
        };

        /**
         * Pull out values from an observable
         * @param ob
         * @returns {string}
         */
        self.stringFromObservables = function (ob) {
            return encodeURIComponent(JSON.stringify(ob, function (key, ob_value) {
                    var value = ko.unwrap(ob_value);
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
            ));
        };

        /**
         * Push values from an encoded string into an observable
         * @param ob an observable or dictionary of observables
         * @param s an encoded string produced by stringFromObservable
         * @param types - a dict of keys to types, where a type can be 'date'
         * or 'bool' to handle mappings to those types particularly.
         */
        self.populateObservables = function (ob, s, types) {
            var o = JSON.parse(decodeURIComponent(s), function (key, value) {
                if (key && types[key] === "date") {
                    value = new Date(value * 1000);
                }
                if (key && types[key] === "bool") {
                    value = (value == 1);
                }
                return value;
            });
            for (var key in ob) {
                if (key in o) {
                    if (ko.isObservable(ob[key])) {
                        console.log("Pushing " + ko.unwrap(o[key]) + " into " + key);
                        ob[key](ko.unwrap(o[key]));
                    } else {
                        ob[key] = o[key];
                    }
                }
            }
        };

        /**
         * Set the username and password to be used for authenticated requests
         * @param username
         * @param password
         */
        self.setCredentials = function (username, password) {
            self.username = username;
            self.password = password;
        };

        /**
         * Get all currently active cameras for this installation
         * @param callback called with (err:string, [cameraID:string])
         */
        self.listCameras = function (callback) {
            applyCallback(ajax("cameras", "GET"), "cameras", callback)
        };

        /**
         * Search for Event objects from the API
         * @param search an EventSearch used to define the search
         * @param callback callback called with (err:string, [event:{}])
         */
        self.searchEvents = function (search, callback) {
            var searchString = (typeof(search) === 'string' || search instanceof String) ? search : self.stringFromObservables(search);
            applyCallback(ajax("events/" + searchString, "GET"), "events", callback);
        };

        /**
         * Search for FileRecord objects from the API
         * @param search a FileRecordSearch used to define the search
         * @param callback callback called with (err:string, [filerecord:{}])
         */
        self.searchFiles = function (search, callback) {
            var searchString = (typeof(search) === 'string' || search instanceof String) ? search : self.stringFromObservables(search);
            applyCallback(ajax("files/" + searchString, "GET"), "files", callback);
        };

        /**
         * Get the camera status for a given camera and time. If the time is not specified (is null) this
         * is interpreted to mean 'now'.
         * @param cameraID camera ID for which status should be retrieved
         * @param date the time at which the status applies
         * @param callback callback called with (err:string, status:{})
         */
        self.getStatus = function (cameraID, date, callback) {
            applyCallback(ajax("cameras/" + cameraID + "/status" + (date == null ? "" : date.getTime())), "status", callback)
        };

    }

});
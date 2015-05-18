/**
 * Created by tom on 17/05/15.
 */

define(["jquery"], function (jquery) {

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
            var searchString = encodeURIComponent(JSON.stringify(search));
            applyCallback(ajax("events/" + search.getSearchString(), "GET"), "events", callback);
        };

        /**
         * Search for FileRecord objects from the API
         * @param search a FileRecordSearch used to define the search
         * @param callback callback called with (err:string, [filerecord:{}])
         */
        self.searchFiles = function (search, callback) {
            var searchString = (typeof(search) === 'string' || search instanceof String) ? search : search.getSearchString();
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
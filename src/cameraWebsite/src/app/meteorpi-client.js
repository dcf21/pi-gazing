define(["jquery", "knockout", "utils"], function (jquery, ko, utils) {

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

        /**
         * Maintains the current user state, any UI or other elements can subscribe to this to be notified of log in and
         * log out events.
         */
        self.user = ko.observable();

        /**
         * Get the current export configurations
         *
         * @param callback called with a list of all current export configurations
         */
        self.getExports = function (callback) {
            applyCallback(ajaxAuth("export", "GET"), "configs", callback)
        };

        /**
         * Create a new export config, returning the record from the database (including the generated uuid). A search
         * of an appropriate type will be created as a default, and the export will be marked as inactive.
         *
         * @param newExport an object containing at least the following:
         * <code>
         *     type        : 'file' or 'event'
         *     target_url  : url of the importing API
         *     user_id     : userID to use when accessing the importing API
         *     password    : password for the importing API
         *     name        : short name for this export configuration
         *     description : longer description if required
         * </code>
         * @param callback called with the newly created callback
         */
        self.createExport = function (newExport, callback) {
            applyCallback(ajaxAuth("export", "POST", newExport), "config", callback)
        };

        self.deleteExport = function (exportId, callback) {
            applyCallback(ajaxAuth("export/" + exportId, "DELETE"), null, callback)
        };

        self.updateExport = function (exportConfig, callback) {
            applyCallback(ajaxAuth("export/" + exportConfig.config_id, "PUT", exportConfig), null, callback)
        };

        /**
         * Retrieve the current set of users, requires a logged in user with camera_admin role.
         *
         * @param callback called with a list of all current users.
         */
        self.getUsers = function (callback) {
            applyCallback(ajaxAuth("users", "GET"), "users", callback)
        };

        /**
         * Update a set of roles
         *
         * @param newRoles
         * @param callback
         */
        self.updateUserRoles = function (newRoles, callback) {
            applyCallback(ajaxAuth("users/roles", "PUT", {new_roles: newRoles}), "users", callback);
        };

        /**
         * Create a new user, or change the password for an existing one.
         *
         * @param userID the new or existing UserID
         * @param password the new password
         * @param callback called with a list of all current users.
         */
        self.changePasswordOrCreateUser = function (userID, password, callback) {
            applyCallback(ajaxAuth("users", "POST", {
                user_id: userID,
                password: password
            }), "users", function (error, userList) {
                /**
                 * If we just updated our own password, change the internal state used by the ajaxAuth calls,
                 * otherwise we won't be able to make any more calls without a logout.
                 */
                if (userList != null) {
                    if (userID === self.username) {
                        self.password = password;
                        localStorage.setItem("meteorpiPassword", password);
                    }
                }
                /* Continue the callback */
                callback(error, userList);
            });
        };

        /**
         * Delete a user on the server
         *
         * @param userID the ID of the user to delete.
         * @param callback called with the list of all current users after the deletion.
         */
        self.deleteUser = function (userID, callback) {
            var wrappedUserID = encodeURIComponent(encodeURIComponent(userID));
            applyCallback(ajaxAuth("users/" + wrappedUserID, "DELETE"), "users", callback);
        };

        /**
         * Get all currently active cameras for this installation
         *
         * @param callback called with (err:string, [cameraID:string])
         */
        self.listCameras = function (callback) {
            applyCallback(ajax("cameras", "GET"), "cameras", callback)
        };

        /**
         * Search for Event objects from the API
         *
         * @param search an EventSearch used to define the search
         * @param callback callback called with (err:string, [event:{}])
         */
        self.searchEvents = function (search, callback) {
            applyCallback(ajax("events/" + utils.encodeString(search), "GET"), null, callback);
        };

        /**
         * Search for FileRecord objects from the API
         *
         * @param search a FileRecordSearch used to define the search
         * @param callback callback called with (err:string, [filerecord:{}])
         */
        self.searchFiles = function (search, callback) {
            applyCallback(ajax("files/" + utils.encodeString(search), "GET"), null, callback);
        };


        /**
         * Get the camera status for a given camera and time. If the time is not specified (is null) this
         * is interpreted to mean 'now'.
         *
         * @param cameraID camera ID for which status should be retrieved
         * @param date the time at which the status applies
         * @param callback callback called with (err:string, status:{})
         */
        self.getStatus = function (cameraID, date, callback) {
            applyCallback(ajax("cameras/" + cameraID + "/status" + (date == null ? "" : "/" + date.getTime()), "GET"),
                "status", callback)
        };

        /**
         * Update the manually modifiable parts of the camera status, specifically the installation URL and name and the
         * visible regions array. Requires a current users with camera_admin role.
         *
         * @param cameraID ID of the camera for which status is to be updated.
         * @param newStatus the updated values.
         * @param callback called with the updated camera status.
         */
        self.updateCameraStatus = function (cameraID, newStatus, callback) {
            applyCallback(ajaxAuth("cameras/" + cameraID + "/status", "POST", newStatus), "status", callback)
        };


        /**
         * Get a URL which can be used to retrieve the contents of the given file.
         *
         * @param file a file structure.
         * @returns {string} URL pointing at the file contents on the server.
         */
        self.urlForFile = function (file) {
            if (file['file_name'] == null) {
                return config.urlPrefix + "files/content/" + file['file_id']
            } else {
                return config.urlPrefix + "files/content/" + file['file_id'] + "/" + self.filenameForFile(file);
            }
        };

        /**
         * Return a filename for the given file
         *
         * @param file a file structure
         * @returns {string} a filename to be shown for the given file in the UI, this will also be the file used
         * when generating links so the browser downloads with this name.
         */
        self.filenameForFile = function (file) {
            if (file['file_name'] == null || file['file_name'].length == 0) {
                return file['file_id'];
            }
            else {
                return file['file_name'];
            }
        };

        /**
         * Attempt to log into the server. If successful this sets the 'user' observable on this object to contain
         * details of the logged in user including its name and roles, otherwise this is set to null. Other components
         * such as the navbar listen to this observable and expose appropriate navigation options based on roles.
         *
         * @param username the user to log in.
         * @param password password.
         * @param callback a callback which is called with either null (in the event of an authentication failure) or
         * the new value of the user observable otherwise. This is called after the observable has been updated.
         */
        self.login = function (username, password, callback) {
            self.username = username;
            self.password = password;
            applyCallback(ajaxAuth("login", "GET"), "user", function (err, user) {
                if (err) {
                    console.log(err);
                    self.username = null;
                    self.password = null;
                    self.user(null);
                    if (callback) {
                        callback(null);
                    }
                }
                if (user) {
                    self.user(user);
                    if (typeof(Storage) !== "undefined") {
                        localStorage.setItem("meteorpiUser", username);
                        localStorage.setItem("meteorpiPassword", password);
                    }
                    if (callback) {
                        callback(user)
                    }
                }
            });
        };

        /**
         * Called when the application first loads, checks for login credentials stored in HTML5 localStorage, and uses
         * them to log in if available.
         *
         * @param callback a callback, called with either null (indicating an authentication failure or no previously
         * stored credentials) or with the logged in user object.
         */
        self.tryAutoLogin = function (callback) {
            if (typeof(Storage) !== "undefined" && localStorage.meteorpiUser) {
                self.login(localStorage.meteorpiUser, localStorage.meteorpiPassword, callback);
            } else {
                callback(null);
            }
        };

        /**
         * Logs out, setting the user observable to null and removing any previously stored credentials in localStorage
         */
        self.logout = function () {
            self.user(null);
            if (typeof(Storage) !== "undefined") {
                localStorage.removeItem("meteorpiUser");
                localStorage.removeItem("meteorpiPassword");
            }
        };

        /**
         * Build an authenticated cross-domain ajax request. Self.user() must not be null. Pass the result of this on
         * to applyCallback to make the call and be notified of response or failure.
         *
         * @param uri the URI under config.urlPrefix to use as the target.
         * @param method HTTP method, if not specified then assumed to be 'GET'
         * @param data request body, if specified this is serialised with JSON.stringify and set as request.data
         * @returns {*} the request.
         */
        var ajaxAuth = function (uri, method, data) {
            if (method == null) {
                method = "GET"
            }
            var request = {
                beforeSend: function (xhr) {
                    xhr.setRequestHeader("Authorization",
                        "Basic " + btoa(self.username + ":" + self.password));
                },
                url: config.urlPrefix + uri,
                type: method,
                contentType: "application/json",
                accepts: "application/json",
                cache: false,
                dataType: 'json'
            };
            if (data != null) {
                request.data = JSON.stringify(data)
            }
            return jquery.ajax(request)
        };

        /**
         * Build an non-authenticated cross-domain ajax request. Pass the result of this on
         * to applyCallback to make the call and be notified of response or failure.
         *
         * @param uri the URI under config.urlPrefix to use as the target.
         * @param method HTTP method, if not specified then assumed to be 'GET'
         * @param data request body, if specified this is serialised with JSON.stringify and set as request.data
         * @returns {*} the request.
         */
        var ajax = function (uri, method, data) {
            if (method == null) {
                method = "GET"
            }
            var request = {
                url: config.urlPrefix + uri,
                type: method,
                contentType: "application/json",
                accepts: "application/json",
                cache: false,
                dataType: 'json'
            };
            if (data != null) {
                request.data = JSON.stringify(data)
            }
            return jquery.ajax(request)
        };

        /**
         * Apply a callback, adding .done(..) and .fail(..) listeners to the supplied XHR instance such that the
         * callback is called with either success or failure appropriately. Optionally also unwraps the data in the
         * result.
         *
         * @param request an XHR, use ajax(..) and ajaxAuth(..) to generate.
         * @param name if specified, the name of the desired root object in the de-serialised JSON response. For example
         * if the server responds with {foo:[bar]} and you just want the [bar] this argument should be defined and set
         * to 'foo'.
         * @param callback a callback, called with (err, result) where err is null if there's a result and vice versa.
         */
        var applyCallback = function (request, name, callback) {
            request.done(function (data) {
                if (name == null) {
                    callback(null, data);
                } else {
                    callback(null, data[name]);
                }
            });
            request.fail(function (jqXHR, textStatus) {
                callback(textStatus, null)
            });
        };

    }

});
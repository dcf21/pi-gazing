define(["knockout", "crossroads", "hasher", "client"], function (ko, crossroads, hasher, client) {

    // This module configures crossroads.js, a routing library. If you prefer, you
    // can use any other routing library (or none at all) as Knockout is designed to
    // compose cleanly with external libraries.
    //
    // You *don't* have to follow the pattern established here (each route entry
    // specifies a 'page', which is a Knockout component) - there's nothing built into
    // Knockout that requires or even knows about this technique. It's just one of
    // many possible ways of setting up client-side routes.


    function Router(config) {
        var self = this;
        var currentRoute = this.currentRoute = ko.observable({});
        this.routes = {};

        /**
         * Push routes into a dict, allowing us to use the goTo functionality later
         */
        ko.utils.arrayForEach(config.routes, function (route) {
            self.routes[route.name] = crossroads.addRoute(route.url, function (requestParams) {
                currentRoute(ko.utils.extend(requestParams, route.params));
            });
        });

        var attemptedLogin = false;

        /**
         * Check for permissions when we change route, including on startup. Attempt to log in if we
         * haven't already, delay doing this until the first time we're routed to prevent race conditions.
         */
        crossroads.routed.add(function (request, data) {

            var checkPermissions = function () {
                if (data.params[0].role) {
                    var userRoles = client.user() == null ? [] : client.user().roles;
                    if (userRoles.indexOf(data.params[0].role) < 0) {
                        self.goTo("home");
                    }
                }
            };
            if (attemptedLogin) {
                checkPermissions();
            }
            else {
                client.tryAutoLogin(function () {
                    attemptedLogin = true;
                    checkPermissions();
                })
            }
        });

        /**
         * Explicitly subscribe to the client.user observable to detect logout, at which point check the route
         * permissions and redirect to the home if needed.
         */
        client.user.subscribe(function (newValue) {
            if (newValue == null) {
                var requiredRoles = currentRoute() == null ? null : currentRoute().role;
                if (requiredRoles != null) {
                    self.goTo("home");
                }
            }
        });

        /** Go */
        activateCrossroads();
    }

    /**
     * Call to explicitly navigate to a named page.
     * @param name name for the page, passed as a key in the dict used to initialise the Router
     * @param params params to interpolate into the route for that page
     */
    Router.prototype.goTo = function (name, params) {
        var newHash = this.routes[name].interpolate(params);
        hasher.setHash(newHash);
    };

    /**
     * Bind hasher and crossroads so crossroads handles changes to the hash part of the URL
     */
    function activateCrossroads() {
        function parseHash(newHash, oldHash) {
            crossroads.parse(newHash);
        }

        crossroads.normalizeFn = crossroads.NORM_AS_OBJECT;
        hasher.initialized.add(parseHash);
        hasher.changed.add(parseHash);
        hasher.init();
    }

    /**
     * Routes configured here, including role restrictions
     */
    return new Router({
        routes: [
            {name: 'home', url: '', params: {page: 'home-page'}},
            {name: 'about', url: 'about', params: {page: 'about-page'}},
            {name: 'status', url: 'status', params: {page: 'status-page'}},
            {name: 'files', url: 'files/:search:', params: {page: 'files-page'}},
            {name: 'events', url: 'events/:search:', params: {page: 'events-page'}},
            {name: 'admin-camera', url: 'admin/camera', params: {page: 'admin-camera-page', role: 'camera_admin'}},
            {name: 'admin-users', url: 'admin/users', params: {page: 'admin-users-page', role: 'camera_admin'}}
        ]
    });

});
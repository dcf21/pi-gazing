define(["knockout", "crossroads", "hasher"], function (ko, crossroads, hasher) {

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
        ko.utils.arrayForEach(config.routes, function (route) {
            self.routes[route.name] = crossroads.addRoute(route.url, function (requestParams) {
                currentRoute(ko.utils.extend(requestParams, route.params));
            });
        });
        activateCrossroads();
    }

    Router.prototype.goTo = function (name, params) {
        var newHash = this.routes[name].interpolate(params);
        hasher.setHash(newHash);
    };

    function activateCrossroads() {
        function parseHash(newHash, oldHash) {
            crossroads.parse(newHash);
        }

        crossroads.normalizeFn = crossroads.NORM_AS_OBJECT;
        hasher.initialized.add(parseHash);
        hasher.changed.add(parseHash);
        hasher.init();
    }

    return new Router({
        routes: [
            {name: 'home', url: '', params: {page: 'home-page'}},
            {name: 'about', url: 'about', params: {page: 'about-page'}},
            {name: 'status', url: 'status', params: {page: 'status-page'}},
            {name: 'files', url: 'files/:search:', params: {page: 'files-page'}},
            {name: 'events', url: 'events/:search:', params: {page: 'events-page'}},
            {name: 'admin-camera', url: 'admin/camera', params: {page: 'admin-camera-page'}},
            {name: 'admin-users', url: 'admin/users', params: {page: 'admin-users-page'}}
        ]
    });

});
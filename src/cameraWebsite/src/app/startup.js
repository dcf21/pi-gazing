define(['jquery', 'knockout', 'router', 'bootstrap', 'knockout-projections', 'kendo', 'kendobindings', 'chart', 'knockout-postbox'], function ($, ko, router) {

    // Components can be packaged as AMD modules, such as the following:
    ko.components.register('nav-bar', {require: 'components/nav-bar/nav-bar'});
    ko.components.register('home-page', {require: 'components/home-page/home'});

    // ... or for template-only components, you can just point to a .html file directly:
    ko.components.register('about-page', {
        template: {require: 'text!components/about-page/about.html'}
    });

    ko.components.register('chart-test', {require: 'components/chart-test/chart-test'});

    ko.components.register('status-page', {require: 'components/status-page/status-page'});

    ko.components.register('files-page', {require: 'components/files-page/files-page'});

    ko.components.register('events-page', {require: 'components/events-page/events-page'});

    // [Scaffolded component registrations will be inserted here. To retain this feature, don't remove this comment.]

    // Start the application
    ko.applyBindings({route: router.currentRoute});
});

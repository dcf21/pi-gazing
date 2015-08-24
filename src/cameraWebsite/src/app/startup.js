define(['jquery', 'knockout', 'router', 'client', 'bootstrap', 'knockout-projections', 'kendo', 'kendobindings', 'chart', 'knockout-postbox'], function ($, ko, router, client) {

    // Components can be packaged as AMD modules, such as the following:
    ko.components.register('nav-bar', {require: 'components/nav-bar/nav-bar'});
    ko.components.register('home-page', {require: 'components/home-page/home'});

    // ... or for template-only components, you can just point to a .html file directly:
    ko.components.register('about-page', {
        template: {require: 'text!components/about-page/about.html'}
    });

    ko.components.register('chart-test', {require: 'components/chart-test/chart-test'});

    ko.components.register('chart-skyclarity', {require: 'components/chart-skyclarity/chart-skyclarity'});

    ko.components.register('chart-triggerrate', {require: 'components/chart-triggerrate/chart-triggerrate'});

    ko.components.register('faqs', {
        template: {require: 'text!components/faqs/faqs.html'}
    });

    ko.components.register('projects', {
        template: {require: 'text!components/projects/projects.html'}
    });

    ko.components.register('status-page', {require: 'components/status-page/status-page'});

    ko.components.register('search-page', {require: 'components/search-page/search-page'});

    ko.components.register('files-viewer', {require: 'components/files-viewer/files-viewer'});

    ko.components.register('region-editor', {require: 'components/region-editor/region-editor'});

    ko.components.register('login-modal', {require: 'components/login-modal/login-modal'});

    ko.components.register('admin-camera-page', {require: 'components/admin-camera-page/admin-camera-page'});

    ko.components.register('admin-users-page', {require: 'components/admin-users-page/admin-users-page'});

    ko.components.register('search-editor', {require: 'components/search-editor/search-editor'});

    ko.components.register('change-password-modal', { require: 'components/change-password-modal/change-password-modal' });

    ko.components.register('admin-exports-page', { require: 'components/admin-exports-page/admin-exports-page' });

    ko.components.register('new-export-modal', { require: 'components/new-export-modal/new-export-modal' });

    ko.components.register('search-editor-modal', { require: 'components/search-editor-modal/search-editor-modal' });

    ko.components.register('what-to-do', {
        template: {require: 'text!components/what-to-do/what-to-do.html'}
    });

    // [Scaffolded component registrations will be inserted here. To retain this feature, don't remove this comment.]

    Date.prototype.toString = function () {
        return this.toUTCString();
    };


    // Start the application
    ko.applyBindings({route: router.currentRoute});


});

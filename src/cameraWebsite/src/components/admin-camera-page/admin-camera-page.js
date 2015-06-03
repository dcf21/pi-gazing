define(['knockout', 'text!./admin-camera-page.html'], function (ko, templateMarkup) {

    function AdminCameraPage(params) {
        this.message = ko.observable('Hello from the admin-camera-page component!');
    }

    // This runs when the component is torn down. Put here any logic necessary to clean up,
    // for example cancelling setTimeouts or disposing Knockout subscriptions/computeds.
    AdminCameraPage.prototype.dispose = function () {
    };

    return {viewModel: AdminCameraPage, template: templateMarkup};

});

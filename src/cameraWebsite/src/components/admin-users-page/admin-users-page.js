define(['knockout', 'text!./admin-users-page.html'], function (ko, templateMarkup) {

    function AdminUsersPage(params) {
        this.message = ko.observable('Hello from the admin-users-page component!');
    }

    // This runs when the component is torn down. Put here any logic necessary to clean up,
    // for example cancelling setTimeouts or disposing Knockout subscriptions/computeds.
    AdminUsersPage.prototype.dispose = function () {
    };

    return {viewModel: AdminUsersPage, template: templateMarkup};

});

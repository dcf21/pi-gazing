define(['knockout', 'text!./page-footer.html', 'client', "modal", "../login-modal/login-modal"], function (ko, template, client, modal, login) {

    function PageFooterViewModel(params) {
        var modal=this;
        this.route = params.route;
        this.user = client.user;

    }

    PageFooterViewModel.prototype.logout = function () {
        client.logout();
    };

    PageFooterViewModel.prototype.login = function () {
        modal.showModal(login);
    };

    return {viewModel: PageFooterViewModel, template: template};
});

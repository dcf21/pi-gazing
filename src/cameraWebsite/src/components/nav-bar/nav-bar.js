define(['knockout', 'text!./nav-bar.html', 'client', "modal", "../login-modal/login-modal"], function (ko, template, client, modal, login) {

    function NavBarViewModel(params) {
        this.route = params.route;
        this.user = client.user;
    }

    NavBarViewModel.prototype.logout = function () {
        client.logout();
    };

    NavBarViewModel.prototype.login = function () {
        modal.showModal(login);
    };

    return {viewModel: NavBarViewModel, template: template};
});

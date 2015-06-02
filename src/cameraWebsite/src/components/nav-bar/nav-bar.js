define(['knockout', 'text!./nav-bar.html', 'client'], function (ko, template, client) {

    function NavBarViewModel(params) {

        // This viewmodel doesn't do anything except pass through the 'route' parameter to the view.
        // You could remove this viewmodel entirely, and define 'nav-bar' as a template-only component.
        // But in most apps, you'll want some viewmodel logic to determine what navigation options appear.

        this.route = params.route;

        this.user = client.user;

        this.logout = function () {
            client.logout();
        };

    }

    return {viewModel: NavBarViewModel, template: template};
});

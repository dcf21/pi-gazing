define(["knockout", "text!./home.html", "client", "router"], function (ko, homeTemplate, client, router) {

    function HomeViewModel(route) {
        var self = this;
    }

    return {viewModel: HomeViewModel, template: homeTemplate};

});

define(["knockout", "text!./home.html", "client"], function (ko, homeTemplate, client) {

    function HomeViewModel(route) {
        this.message = ko.observable('Welcome to MeteorPi Camera Control!');
    }

    HomeViewModel.prototype.doSomething = function () {
        client.listCameras(function (err, cameras) {
            console.log(cameras)
        });
        this.message('You invoked doSomething() on the viewmodelfoo.');
    };

    return {viewModel: HomeViewModel, template: homeTemplate};

});

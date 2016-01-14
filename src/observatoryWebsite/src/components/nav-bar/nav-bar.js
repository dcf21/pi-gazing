define(['knockout', 'text!./nav-bar.html', 'client', "modal", "../login-modal/login-modal"], function (ko, template, client, modal, login) {

    function NavBarViewModel(params) {
        var modal=this;
        this.route = params.route;
        this.user = client.user;

        this.animate =
            function (f) {
                setTimeout(f, 1000 / 60)
            };

        window.addEventListener('scroll', function () { // on page scroll
            modal.animate(modal.parallax_banner); // call parallaxbanner() on next available screen paint
        }, false);

    }

    NavBarViewModel.prototype.parallax_banner = function () {
        var banner1 = document.getElementById('bannerppl');
        var banner2 = document.getElementById('bannerfull');

        var scrolltop = window.pageYOffset; // get number of pixels document has scrolled vertically
        banner1.style.bottom = -scrolltop * 0.4 + 'px';
        banner2.style.bottom = -scrolltop * 0.9 + 'px';
    };


    NavBarViewModel.prototype.logout = function () {
        client.logout();
    };

    NavBarViewModel.prototype.login = function () {
        modal.showModal(login);
    };

    return {viewModel: NavBarViewModel, template: template};
});

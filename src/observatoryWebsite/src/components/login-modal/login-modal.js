/** login-modal.js
 * Meteor Pi, Cambridge Science Centre
 * Dominic Ford, Tom Oinn
 */

define(['knockout', 'text!./login-modal.html', 'client'], function (ko, templateMarkup, client) {

    function LoginModal(params) {
        this.userID = ko.observable();
        this.password = ko.observable();
        this.state = ko.observable();
    }

    LoginModal.prototype.login = function () {
        var self = this;
        client.login(this.userID(), this.password(), function (user) {
            if (user == null) {
                self.userID(null);
                self.password(null);
                self.state("failed");
            }
            else {
                self.state("success");
                self.modal.close(client.user());
            }
        });
    };

    LoginModal.prototype.cancel = function () {
        this.modal.close();
    };

    return {viewModel: LoginModal, template: templateMarkup};

});

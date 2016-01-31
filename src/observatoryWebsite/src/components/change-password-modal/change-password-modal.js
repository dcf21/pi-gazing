/** change-password-page.js
 * Meteor Pi, Cambridge Science Centre
 * Dominic Ford, Tom Oinn
 */

define(['knockout', 'text!./change-password-modal.html', 'client'], function (ko, templateMarkup, client) {

    function ChangePasswordModal(props) {
        var self = this;
        self.props = props;
        self.userID = ko.observable(props.user_id);
        self.password = ko.observable("");
        self.problems = ko.observable();
        self.savePassword = function () {
            if (props.validate) {
                self.problems(props.validate(self.userID(), self.password()));
            }
            if (!self.problems()) {
                self.modal.close({'user_id': self.userID(), 'password': self.password()});
            }
        };
        self.cancel = function () {
            self.modal.close();
        };
    }

    return {viewModel: ChangePasswordModal, template: templateMarkup};

});

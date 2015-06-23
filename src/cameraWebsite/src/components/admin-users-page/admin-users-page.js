define(['knockout', 'text!./admin-users-page.html', 'client', 'modal', '../change-password-modal/change-password-modal'], function (ko, templateMarkup, client, modal, changeModal) {

    function AdminUsersPage(params) {
        var self = this;

        self.users = ko.observableArray();

        self.deleteUser = function () {
            self.users.remove(this);
        };

        self.getUsers();
    }

    AdminUsersPage.prototype.getUsers = function () {
        var self = this;
        client.getUsers(function (err, users) {
            self.users([]);
            ko.utils.arrayForEach(users, function (user) {
                self.users.push({
                    'user_id': ko.observable(user.user_id),
                    'has_user': ko.observable(user.roles.indexOf('user') >= 0),
                    'has_admin': ko.observable(user.roles.indexOf('camera_admin') >= 0),
                    'has_import': ko.observable(user.roles.indexOf('import') >= 0),
                    'is_current': ko.observable(client.user().user_id.trim() === user.user_id.trim())
                })
            });
        });
    };

    AdminUsersPage.prototype.changePasswordForUser = function (user_id, password) {
        console.log("Change password for " + user_id + " to " + password);
        this.getUsers();
    };

    AdminUsersPage.prototype.createNewUser = function (user_id, password) {
        console.log("Create new user with user_id " + user_id + ", password " + password);
        this.getUsers();
    };

    AdminUsersPage.prototype.saveChanges = function () {
        console.log("Save changes");
        this.getUsers();
    };

    AdminUsersPage.prototype.newUser = function () {
        var self = this;
        var passwordChangeModal = modal.showModal(changeModal, null, {
            title: "Add User",
            submitName: "Create New User",
            editable: true,
            user_id: "",
            validate: function (user_id, password) {
                var errors = [];
                if (password.length < 4) {
                    errors.push("Password too short, must be at least 4 characters");
                }
                if (user_id.length < 4) {
                    errors.push("User ID too short, must be at least 4 characters");
                }
                ko.utils.arrayForEach(self.users(), function (user) {
                    if (user_id.trim() === user.user_id().trim()) {
                        errors.push("User ID already exists, please use a different one");
                    }
                });
                if (errors.length > 0) {
                    return errors.join(", ") + ".";
                }
                else {
                    return null;
                }
            }
        });
        passwordChangeModal.done(function (changedUser) {
            self.createNewUser(changedUser.user_id, changedUser.password);
        });
        passwordChangeModal.fail(function () {
            console.log("New user creation cancelled");
        });
    };


    AdminUsersPage.prototype.updatePassword = function () {
        var passwordChangeModal = modal.showModal(changeModal, null, {
            title: "Change Password",
            submitName: "Update Password",
            editable: false,
            user_id: this.user_id(),
            validate: function (user_id, password) {
                var errors = [];
                if (password.length < 4) {
                    errors.push("Password too short, must be at least 4 characters");
                }
                if (errors.length > 0) {
                    return errors.join(", ") + ".";
                }
                else {
                    return null;
                }
            }
        });
        passwordChangeModal.done(function (changedUser) {
            self.changePasswordForUser(changedUser.user_id, changedUser.password);
        });
        passwordChangeModal.fail(function () {
            console.log("Password change cancelled");
        });
    };

    return {viewModel: AdminUsersPage, template: templateMarkup};

});

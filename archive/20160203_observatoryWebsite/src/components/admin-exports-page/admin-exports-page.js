/** admin-exports-page.js
 * Meteor Pi, Cambridge Science Centre
 * Dominic Ford, Tom Oinn
 */

define(['knockout', 'text!./admin-exports-page.html', 'client', 'modal', '../new-export-modal/new-export-modal',
        '../search-editor-modal/search-editor-modal'],
    function (ko, templateMarkup, client, modal, exportModal, searchModal) {

        function AdminExportsPage(params) {
            var self = this;

            self.exports = ko.observableArray();
            self.doneSearch = ko.observable(false);

            self.newExport = function () {
                var theModal = modal.showModal(exportModal);
                theModal.done(function (spec) {
                    client.createExport(spec, function (err, value) {
                        if (value) {
                            self.getExports();
                        }
                    });
                });
            };

            self.getExports = function () {
                client.getExports(function (err, exports) {
                    self.exports(exports);
                    self.doneSearch(true);
                })
            };

            self.deleteExport = function () {
                client.deleteExport(this.config_id, function (err, result) {
                    self.getExports()
                })
            };

            self.editExport = function () {
                var theModal = modal.showModal(searchModal, null, this);
                theModal.done(function (exportConfig) {
                    client.updateExport(exportConfig, function (err, result) {
                        self.getExports();
                    });
                })
            };

            self.getExports();
        }

        AdminExportsPage.prototype.dispose = function () {
        };

        return {viewModel: AdminExportsPage, template: templateMarkup};

    });

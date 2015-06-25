define(['knockout', 'text!./new-export-modal.html'], function (ko, templateMarkup) {


    function NewExportModal(params) {
        var self = this;
        /* <code>
         *     type        : 'file' or 'event'
         *     target_url  : url of the importing API
         *     user_id     : userID to use when accessing the importing API
         *     password    : password for the importing API
         *     name        : short name for this export configuration
         *     description : longer description if required
         * </code>
         */
        self.spec = {
            type: ko.observable("file"),
            target_url: ko.observable(""),
            user_id: ko.observable(""),
            password: ko.observable(""),
            name: ko.observable(""),
            description: ko.observable("")
        };

        self.add = function () {
            self.modal.close(ko.toJS(self.spec))
        };

        self.cancel = function () {
            self.modal.close()
        };
    }

    return {viewModel: NewExportModal, template: templateMarkup};

});

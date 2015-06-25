define(['knockout', 'text!./search-editor-modal.html', 'utils'], function (ko, templateMarkup, utils) {

    function SearchEditorModal(exportConfig) {
        var self = this;

        if (exportConfig.type === 'file') {
            self.search = {
                after: ko.observable(),
                before: ko.observable(),
                after_offset: ko.observable(),
                before_offset: ko.observable(),
                semantic_type: ko.observable(),
                meta: ko.observableArray()
            };
        }
        else if (exportConfig.type === 'event') {
            self.search = {
                after: ko.observable(),
                before: ko.observable(),
                after_offset: ko.observable(),
                before_offset: ko.observable(),
                event_type: ko.observable(),
                meta: ko.observableArray()
            };
        }

        self.exportType = ko.observable(exportConfig.type);

        self.spec = {
            target_url: ko.observable(exportConfig.target_url),
            user_id: ko.observable(exportConfig.user_id),
            password: ko.observable(exportConfig.password),
            name: ko.observable(exportConfig.config_name),
            description: ko.observable(exportConfig.config_description),
            enabled: ko.observable(exportConfig.enabled)
        };

        var searchString = utils.encodeString(exportConfig.search);
        utils.updateSearchObject(self.search, searchString);

        self.update = function () {
            // This is a bit of a hack, but allows us to use the existing logic to encode dates as milliseconds
            // since the epoch etc.
            var encodedSearchObject = utils.decodeString(utils.encodeString(utils.getSearchObject(self.search)));
            self.modal.close({
                type: exportConfig.type,
                config_description: self.spec.description(),
                config_id: exportConfig.config_id,
                config_name: self.spec.name(),
                enabled: self.spec.enabled(),
                password: self.spec.password(),
                target_url: self.spec.target_url(),
                user_id: self.spec.user_id(),
                search: encodedSearchObject
            })
        };

        self.cancel = function () {
            self.modal.close()
        };
    }

    // This runs when the component is torn down. Put here any logic necessary to clean up,
    // for example cancelling setTimeouts or disposing Knockout subscriptions/computeds.
    SearchEditorModal.prototype.dispose = function () {
    };

    return {viewModel: SearchEditorModal, template: templateMarkup};

});

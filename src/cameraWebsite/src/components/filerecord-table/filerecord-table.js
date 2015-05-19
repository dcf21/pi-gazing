define(['knockout', 'text!./filerecord-table.html'], function (ko, templateMarkup) {

    function FileRecordTable(params) {
        this.fileRecords = params.fileRecords;
    }

    return {
        viewModel: FileRecordTable,
        template: templateMarkup
    };

});

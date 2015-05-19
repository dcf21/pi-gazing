define(['knockout', 'text!./filerecord-table.html'], function (ko, templateMarkup) {

    function FileRecordTable(params) {
        this.fileRecords = params.fileRecords;
    }

    return {
        viewModel: {
            createViewModel: function (params, componentInfo) {
                console.log(componentInfo);
                /*
                 Can retrieve the element with componentInfo.element here, so, if this were a graph component
                 of some kind rather than a simple table, we could build a new Canvas element and inject it here
                 to use as the contents of the view. By manually subscribing to the observables defined by the view
                 model we could pick up changes and use them to redraw the canvas appropriately. Over to you, Dominic...
                 */
                return new FileRecordTable(params);
            }
        }, template: templateMarkup
    };

});

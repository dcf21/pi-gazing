define(['knockout', 'text!./file-results-page.html', 'router', 'client'], function (ko, templateMarkup, router, client) {

    function FileResultsPage(params) {
        var self = this;
        this.fileRecords = ko.observableArray();
        var searchString = router.currentRoute()['search'];
        client.searchFiles(searchString, function (err, results) {
            console.log(results);
            self.fileRecords.removeAll();
            for (var i = 0, len = results.length; i < len; ++i) {
                self.fileRecords.push(results[i]);
            }
        });
    }

    return {viewModel: FileResultsPage, template: templateMarkup};

});

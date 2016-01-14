define(["knockout", "text!./home.html", "client", "router", "utils"], function (ko, homeTemplate, client, router, utils) {

    function HomeViewModel(route) {
        var self = this;

        self.items = [{
            "camera": "Cambridge-South-East",
            "time": 1445279601,
            "caption": "Bright satellite detected by our camera in south-east Cambridge."
        },
            {
                "camera": "Cambridge-East",
                "time": 1443322592,
                "caption": "Bright shooting star spotted by our Cambridge East and Bury St Edmunds cameras."
            },
            {
                "camera": "Bury-St-Edmunds",
                "time": 1444501540,
                "caption": "Bright satellite detected by our camera in Bury St Edmunds."
            },
            {
                "camera": "Bury-St-Edmunds",
                "time": 1446932349,
                "caption": "Bright shooting star detected by our camera in Bury St Edmunds."
            },
            {
                "camera": "Bury-St-Edmunds",
                "time": 1446958959,
                "caption": "Beautiful grouping of the Moon and planets seen from Bury St Edmunds. From the left, the four bright objects in a diagonal line are the Moon, Venus, Mars (faint) and Jupiter."
            }
        ];

        jQuery.each(self.items, function (idx, item) {
            var search = {
                after: ko.observable(1000 * (item['time'] - 1)),
                before: ko.observable(1000 * (item['time'] + 1)),
                camera_ids: ko.observable(item['camera']),
                limit: ko.observable(1),
                skip: ko.observable(0)
            };

            item['link'] = "https://meteorpi.cambridgesciencecentre.org/#file/%257B%2522camera_ids%2522%253A%2522" + item['camera'] + "%2522%252C%2522searchtype%2522%253A%2522Moving%2520objects%2522%252C%2522before%2522%253A" + (item['time'] + 1) + "000%252C%2522after%2522%253A" + (item['time'] - 1) + "000%257D";
            item['imgpath'] = ko.observable("");

            // Get the search object and use it to retrieve results
            var searchObj = utils.getSearchObject(search, {skip: 0});
            client.searchEvents(searchObj, function (error, results) {
                jQuery.each(results.events, function (index, item) {
                    jQuery.each(item.files, function (index, f) {
                        if (f.semantic_type == 'meteorpi:triggers/event/maxBrightness/lensCorr') {
                            self.items[idx]['imgpath'](client.urlForFile(f));
                        }
                    });
                });
            });
        });
    }

    return {viewModel: HomeViewModel, template: homeTemplate};

});

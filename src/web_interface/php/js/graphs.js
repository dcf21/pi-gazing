// graphs.js
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2015-2021 Dominic Ford.

// This file is part of Pi Gazing.

// Pi Gazing is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Pi Gazing is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Pi Gazing.  If not, see <http://www.gnu.org/licenses/>.
// -------------------------------------------------

// Library to plot time lines of metadata values

function MetadataGraph(settings, context) {
    var self = this;

    this._settings = settings;
    this._context = context;
    this._width = $(context).width();

    var utc_min = null;
    var utc_max = null;
    self._graph_data_raw = this._settings['data'];
    self._graph_data_final = [];

    $.each(self._graph_data_raw, function (i, data_set) {
        var data_set_final = [];
        $.each(data_set, function (j, item) {
            var utc = parseFloat(item[0]);
            if ((utc_min === null) || (utc<utc_min)) utc_min = utc;
            if ((utc_max === null) || (utc>utc_max)) utc_max = utc;
            data_set_final.push([utc, parseFloat(item[1])]);
        });
        self._graph_data_final.push(
            new JSPlot_DataSet(
                self._settings['data_set_titles'][i],
                {
                    'plotStyle': 'points'
                },
                data_set_final,
                null));
    });

    // Set dimensions and limits of graph
    var width = self._width - 120;
    var aspect = 0.35;

    // Create canvas to put graph onto
    var canvas = new JSPlot_Canvas({
        "plot": new JSPlot_Graph(
            self._graph_data_final,
            {
                'interactiveMode': 'pan',
                'width': width,
                'aspect': aspect,
                'x1_axis': {
                    'scrollMin': utc_min,
                    'scrollMax': utc_max,
                    'scrollEnabled': true,
                    'zoomEnabled': true,
                    'min': utc_min,
                    'max': utc_max,
                    'dataType': 'timestamp'
                },
                'y1_axis': {
                    'label': self._settings['y-axis']
                }
            })
    }, {});

    // Render plot
    canvas.renderToCanvas(
        $(".chart_div", self._context)[0]
    );
}

$(function () {
    $(".chart_holder").each(function (i, el) {
        var elj = $(el);
        var meta = elj.data("meta");
        var handler = new MetadataGraph(meta, elj);
        elj.data("handler", handler);
    });
});

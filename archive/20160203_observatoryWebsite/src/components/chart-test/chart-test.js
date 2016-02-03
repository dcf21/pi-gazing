/** chart-test.js
 * Meteor Pi, Cambridge Science Centre
 * Dominic Ford, Tom Oinn
 */

define(['knockout', 'text!./chart-test.html', 'jquery', 'chart'], function (ko, templateMarkup, jquery, Chart) {

    /*
     * See http://www.chartjs.org/docs for possible types of chart, usage, config etc etc.
     */

    function ChartTest(element, params) {
        // Get the 2d context for the canvas element defined in chart-test.html
        var ctx = jquery(element).find("#chart-canvas").get(0).getContext("2d");
        // Override global chart.js options here
        var options = {
            percentageInnerCutout: 40
        };
        // Dummy data, obviously use some kind of observable passed into the params object
        var data = [
            {
                value: 300,
                color: "#F7464A",
                highlight: "#FF5A5E",
                label: "Red"
            },
            {
                value: 50,
                color: "#46BFBD",
                highlight: "#5AD3D1",
                label: "Green"
            },
            {
                value: 100,
                color: "#FDB45C",
                highlight: "#FFC870",
                label: "Yellow"
            }

        ];
        // Doughnuts! Animated bouncy doughnuts!
        var testChart = new Chart(ctx).Doughnut(data, options);
    }

    // This runs when the component is torn down. Put here any logic necessary to clean up,
    // for example cancelling setTimeouts or disposing Knockout subscriptions/computeds.
    ChartTest.prototype.dispose = function () {
        // Nothing to do here, I don't think we need to explicitly dispose of canvas elements
    };

    return {
        // Extended here, rather than passing in the ChartTest constructor explicitly we pass
        // in a createViewModel function, this then gets access to the componentInfo from which we
        // can extract the DOM element representing the injected component. This is then used to
        // obtain the canvas and draw the chart into it.
        viewModel: {
            createViewModel: function (params, componentInfo) {
                return new ChartTest(componentInfo.element, params);
            }
        },
        // Trivial template, but if we wanted to, say, allow the size to be defined by the component
        // markup we could pass that through here. Just set self.height, self.width in the constructor
        // and reference in the HTML template.
        template: templateMarkup
    };

});

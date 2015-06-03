// require.js looks for the following global when initializing
var require = {
    baseUrl: ".",
    paths: {
        "bootstrap": "bower_modules/components-bootstrap/js/bootstrap.min",
        "crossroads": "bower_modules/crossroads/dist/crossroads.min",
        "hasher": "bower_modules/hasher/dist/js/hasher.min",
        "jquery": "bower_modules/jquery/dist/jquery",
        "knockout": "bower_modules/knockout/dist/knockout",
        "knockout-projections": "bower_modules/knockout-projections/dist/knockout-projections",
        "signals": "bower_modules/js-signals/dist/signals.min",
        "text": "bower_modules/requirejs-text/text",
        "client": "app/meteorpi-client",
        "model": "app/meteorpi-model",
        "router": "app/router",
        "kendo": "bower_modules/kendo-ui-core/js/kendo.ui.core.min",
        "kendobindings": "bower_modules/knockout-kendo/build/knockout-kendo.min",
        "chart": "bower_modules/chartjs/Chart.min",
        "knockout-postbox": "bower_modules/knockout-postbox/build/knockout-postbox.min",
        "modal": "app/modal"
    },
    shim: {
        "bootstrap": {deps: ["jquery"]},
        "kendo": {deps: ["jquery"]},
        "kendobindings": {deps: ["jquery", "kendo", "knockout"]}
    }
};

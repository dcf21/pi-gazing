/**
 * Created by tom on 03/06/15.
 */
define(["jquery", "knockout"], function (jquery, ko) {

    return new ModalHelper();

    function ModalHelper() {

        var self = this;

        var showTwitterBootstrapModal = function ($ui) {
            $ui.modal({
                backdrop: "static",
                keyboard: false
            });
        };

        var whenModalResultCompleteThenHideUI = function (deferredModalResult, $ui) {
            deferredModalResult.always(function () {
                $ui.modal("hide");
            });
        };

        var whenUIHiddenThenRemoveUI = function ($ui) {
            $ui.on("hidden.bs.modal", function () {
                $ui.each(function (index, element) {
                    ko.cleanNode(element);
                });
                $ui.remove();
            });
        };

        var addModalHelperToViewModel = function (viewModel, deferredModalResult, context) {
            viewModel.modal = {
                close: function (result) {
                    if (typeof result !== "undefined") {
                        deferredModalResult.resolveWith(context, [result]);
                    } else {
                        deferredModalResult.rejectWith(context, []);
                    }
                }
            };
        };

        var createModalElement = function (html, viewModel) {
            var temporaryDiv = addHiddenDivToBody();
            temporaryDiv.innerHTML = html;
            ko.applyBindings(viewModel, temporaryDiv);
            var deferredElement = jquery.Deferred();
            deferredElement.resolve(temporaryDiv);
            return deferredElement;
        };

        var addHiddenDivToBody = function () {
            var div = document.createElement("div");
            div.style.display = "none";
            document.body.appendChild(div);
            return div;
        };

        self.showModal = function (component, context) {
            var viewModel = new component.viewModel();
            var template = component.template;
            return createModalElement(template, viewModel)
                .pipe(jquery) // jQueryify the DOM element
                .pipe(function ($ui) {
                    var deferredModalResult = jquery.Deferred();
                    addModalHelperToViewModel(viewModel, deferredModalResult, context);
                    showTwitterBootstrapModal($ui);
                    whenModalResultCompleteThenHideUI(deferredModalResult, $ui);
                    whenUIHiddenThenRemoveUI($ui);
                    return deferredModalResult;
                });
        };

    }

});
/** modal.js
 * Meteor Pi, Cambridge Science Centre
 * Dominic Ford, Tom Oinn
 *
 * Created by tom on 03/06/15.
 *
 * Helper used to create and show modals with knockout.js bindings, in effect any component can be shown as a modal,
 * although this will only work correctly if the component itself provides the markup for the modal container. This
 * utility class will handle instantiation of the component viewModel, passing of parameters to it, cope with the
 * asynchronous display and binding of the modal itself and return of values to the caller via a jquery deferred.
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

        /**
         * Show a modal dialogue, returning a deferred value which can be used to receive data directly from it, and
         * accepting an optional parameters block which will be passed to the constructor of the component used as a
         * modal. For example:
         * <code>
         *     var mod = modal.showModal(changeModal, null, {param1: someValue});
         *     mod.done(function (result) {
         *       console.log("Done! " + result);
         *     });
         *     mod.fail(function () {
         *       console.log("Cancelled");
         *     });
         * </code>
         *
         * @param component a component, which should be a dict of {viewModel, template}.
         * @param context binding context used when applying bindings. Leave at null to let knockout do its own thing,
         * or specify an alternate root element to use as the context when binding.
         * @param params optional object which will be passed to the constructor of the viewModel class
         * @returns a jquery deferred which can be used to register done(..) and fail() methods. These can be called
         * within the modal itself by 'self.modal.close(..)' - if this is supplied with a value the deferred will be
         * called with 'done', otherwise with 'fail'.
         */
        self.showModal = function (component, context, params) {
            var viewModel = new component.viewModel(params);
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
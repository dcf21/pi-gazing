// search_form.js
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

// Module for observatory maps
function SearchForm(parent) {
    var self = this;
    self.parent = parent;

    // Set up tooltips
    self.showHelp = false;
    self.tooltip_placement();

    $('.help-toggle', self.parent).click(function() {
        self.showHelp = !self.showHelp;
        self.tooltip_placement();
    });
}

SearchForm.prototype.tooltip_placement = function () {
    $('[data-pos="tooltip-right"]', this.parent).tooltip({'placement':'right'});
    $('[data-pos="tooltip-above"]', this.parent).tooltip({'placement':'top'});
    $('[data-pos="tooltip-below"]', this.parent).tooltip({'placement':'bottom'});
    $('[data-toggle="tooltip"]', this.parent).tooltip( this.showHelp ? "show" : "hide");
};

// Initialise all HTML elements with class sliding_pane
function searchFormRegister() {
    $(".search-form").each(function (i, el) {
        var elj = $(el);
        var handler = new SearchForm(elj);
        elj.data("handler", handler);
    });
}

$(searchFormRegister);

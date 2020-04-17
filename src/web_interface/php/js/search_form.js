// search_form.js
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2015-2020 Dominic Ford.

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

// Module for observatory maps
function SearchForm(parent) {
    var self = this;
    self.parent = parent;

    // Set up tooltips
    self.showHelp = false;
    self.tooltip_placement();

    $('.help-toggle', self.parent).click(function () {
        self.showHelp = !self.showHelp;
        self.tooltip_placement();
    });
}

SearchForm.prototype.tooltip_placement = function () {
    $('[data-pos="tooltip-right"]', this.parent).tooltip({'placement': 'right'});
    $('[data-pos="tooltip-above"]', this.parent).tooltip({'placement': 'top'});
    $('[data-pos="tooltip-below"]', this.parent).tooltip({'placement': 'bottom'});
    $('[data-toggle="tooltip"]', this.parent).tooltip(this.showHelp ? "show" : "hide");
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

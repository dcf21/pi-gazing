// paneSequence.js
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

// This class implements a sequence of panes, as on the what to do page

// Module for sequential panels
function SequentialPanes(parent) {
    var self = this;
    var i;
    this.parent = parent;
    this.children = $(".pane-item", parent);
    this.final_next = parent.data("final-next");
    this.number = this.children.length;
    this.current = 0;

    this.titles = this.children.map(function () {
        return $(this).data("title")
    }).get();

    this.contents = "<ul>";
    for (i = 0; i < this.number; i++)
        this.contents += "<li><a class='goto goto" + String(i) + "'>" + this.titles[i] + "</a></li>";
    this.contents += "</ul>";
    $(".pane-list", parent).html(this.contents);

    $(".pane-controls", parent).html(
        '<div style="display:inline-block;padding:10px;">' +
        '<button type="button" class="spprev btn">&#171; Back</button>' +
        '</div><div style="display:inline-block;padding:10px;">' +
        '<button type="button" class="spnext btn btn-primary btn-sm">Next &#187;</button>' +
        '</div>');
    $(".pane-controls-final", parent).html(
        '<div style="display:inline-block;padding:10px;">' +
        '<button type="button" class="spprev btn">&#171; Back</button>' +
        '</div><div style="display:inline-block;padding:10px;">' +
        '<button type="button" class="spnext2 btn btn-primary btn-sm">'+this.final_next[1]+' &#187;</button>' +
        '</div>');
    $(".spprev", parent).click(function () {
        self.prev();
    });
    $(".spnext", parent).click(function () {
        self.next();
    });
    $(".spnext2", parent).click(function () {
        window.location = self.final_next[0];
    });
    for (i = 0; i < this.number; i++) {
        $(".goto" + String(i), parent).click(self.gotoPane(self, i));
    }
    this.selectPane(this.current);
}

SequentialPanes.prototype.prev = function () {
    if (this.current > 0) this.selectPane(this.current - 1);
};

SequentialPanes.prototype.next = function () {
    if (this.current < this.number - 1) this.selectPane(this.current + 1);
};

// This is a hack to retain the values of x and i in a closure
SequentialPanes.prototype.gotoPane = function (x, i) {
    return function() { x.selectPane(i); }
}

SequentialPanes.prototype.selectPane = function (i) {
    var self = this;
    var j = this.children[this.current];
    var k = this.children[i];
    this.children.each(function (l, el) {
        $(el).stop();
        if ((l != i) && (l != self.current)) $(el).css('display', 'none');
    });

    // Change panes with a fade effect
    $(j).fadeOut(400, function () {
        $(k).fadeIn(400);
    });
    this.current=i;

    // Highlight the appropriate item in the contents list
    $(".goto", self.parent).css("font-weight", "normal");
    $(".goto"+this.current, self.parent).css("font-weight", "bold");

    // Disable or enable previous / next buttons as required
    if (i==0) $(".spprev", self.parent).prop("disabled",true);
    else $(".spprev", self.parent).prop("disabled",false);
    if (i==this.number-1) $(".spnext", self.parent).prop("disabled",true);
    else $(".spnext", self.parent).prop("disabled",false);
};

// Initialise all HTML elements with class pane-sequence
function sequentialPanesRegister() {
    $(".pane-sequence").each(function (i, el) {
        var elj = $(el);
        var slider = new SequentialPanes(elj);
        elj.data("handler", slider);
    });
}

$(sequentialPanesRegister);

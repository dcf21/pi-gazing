// slidingPanes.js
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2019 Dominic Ford.

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

// This class implements sliding panes, as seen on the homepage

// Module for sliding panels
function SlidingPanes(parent) {
    this.parent = parent;
    this.children = $(".slidingPane_item", parent);
    this.number = this.children.length;
    this.current = 0;
    this.auto = true;
    this.selectPane(0);
    setInterval((function (self) {
        return function () {
            self.alarm();
        }
    })(this), 8000);
}

SlidingPanes.prototype.prev = function () {
    this.auto = false;
    this.selectPane((this.current + this.number - 1) % this.number);
};

SlidingPanes.prototype.next = function () {
    this.auto = false;
    this.selectPane((this.current + 1) % this.number);
};

SlidingPanes.prototype.alarm = function () {
    if (this.auto) {
        this.selectPane((this.current + 1) % this.number);
    }
    this.auto = true;
};

SlidingPanes.prototype.selectPane = function (i) {
    var obj = this;
    var j = this.children[this.current];
    var k = this.children[i];
    this.children.each(function (l, el) {
        $(el).stop();
        if ((l != i) && (l != obj.current)) $(el).css('visibility', 'hidden');
    });
    $(j).css('z-index', '1');
    $(k).css('z-index', '2');
    $(k).css('opacity', '0');
    $(k).css('visibility', 'visible');
    $(k).stop().animate({'opacity': 1}, 600, function () {
        obj.children.each(function (l, el) {
            if (l != i) $(el).css('visibility', 'hidden');
        });
        obj.current = i;
    });
};

// Initialise all HTML elements with class sliding_pane
function slidingPanesRegister() {
    $(".slidingPane").each(function (i, el) {
        var elj = $(el);
        var slider = new SlidingPanes(elj);
        elj.data("handler", slider);
        $(".slidingPane_prev", elj).click(function () {
            slider.prev();
        });
        $(".slidingPane_next", elj).click(function () {
            slider.next();
        });
    });
}

$(slidingPanesRegister);

// parallax.js
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

// This code implements parallax scrolling in the top banner of each page

// Create cross browser requestAnimationFrame method:
window.requestAnimationFrame = window.requestAnimationFrame
    || window.mozRequestAnimationFrame
    || window.webkitRequestAnimationFrame
    || window.msRequestAnimationFrame
    || function (f) {
        setTimeout(f, 1000 / 60)
    };

function parallax_banner() {
    var banner1 = $('#bannerppl')[0];
    var banner2 = $('#bannerfull')[0];

    var scrolltop = window.pageYOffset; // get number of pixels document has scrolled vertically
    banner1.style.bottom = -scrolltop * 0.4 + 'px';
    banner2.style.bottom = -scrolltop * 0.9 + 'px';
}

window.addEventListener('scroll', function () { // on page scroll
    requestAnimationFrame(parallax_banner); // call parallaxbanner() on next available screen paint
}, false);


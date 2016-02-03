// parallax.js
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

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


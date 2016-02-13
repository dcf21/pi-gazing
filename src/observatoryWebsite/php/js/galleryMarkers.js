// galleryMarkers.js
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

// This class implements markers which show the positions of meteors in the image gallery

function GalleryMarkers(parent) {
    var self = this;
    this.parent = parent;
    this.children = $("div[data-path]", parent);
    this.show_paths = false;

    // Wire up button to toggle whether to display paths
    $(".paths-toggle").click( function() { self.show_paths=!self.show_paths; self.update(); })
}

GalleryMarkers.prototype.update = function()
{
    var self = this;
    if (self.show_paths) $(".gallery_path_marker").fadeIn(400);
    else $(".gallery_path_marker").fadeOut(400);
};

// Initialise all HTML elements with class pane-sequence
function galleryMarkersRegister() {
    $(".gallery_with_markers").each(function (i, el) {
        var elj = $(el);
        var slider = new GalleryMarkers(elj);
        elj.data("handler", slider);
    });
}

$(galleryMarkersRegister);

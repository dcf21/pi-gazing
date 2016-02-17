// paneSequence.js
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

// This class implements a sequence of panes, as on the what to do page

// Module for sequential panels
function SequentialPanes(parent) {
    var self = this;
    var i;
    this.parent = parent;
    this.children = $(".pane-item", parent);
    this.number = this.children.length;
    this.current = 0;

    this.titles = this.children.map(function () {
        return $(this).data("title")
    }).get();

    this.contents = "<ul>";
    for (i = 0; i < this.number; i++)
        this.contents += "<li><a class='goto" + String(i) + "'>" + this.titles[i] + "</a></li>";
    this.contents += "</ul>";
    $(".pane-list", parent).html(this.contents);

    $(".pane-controls", parent).html(
        '<div style="display:inline-block;padding:10px;">' +
        '<button type="button" class="spprev btn">&#171; Back</button>' +
        '</div><div style="display:inline-block;padding:10px;">' +
        '<button type="button" class="spnext btn btn-primary">Next &#187;</button>' +
        '</div>');
    $(".spprev", parent).click(function () {
        self.prev();
    });
    $(".spnext", parent).click(function () {
        self.next();
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

// hover.js

// Library for working out what object the mouse pointer is hovering over

// Function for managing hover texts over a canvas. Element should be jQuery element, $("#foo")
function HoverManager(element, wrapX, hoverHandle, clickHandle, dblClickHandle) {
    var self = this;
    this.element = element;
    this.canvas = document.createElement('canvas');
    this.reset(this.element.width(), this.element.height());
    this._offset_x = 0;
    this._offset_y = 0;
    this._hH = hoverHandle;
    this._cH = clickHandle;
    this._dH = dblClickHandle;
    this._wrap_x = wrapX;
    if (dblClickHandle) {
        element.on({
            "dblclick": function (ev) {
                self.dblClickHandle(ev);
            }
        });
    }
    if (clickHandle) {
        element.on({
            "mousedown": function (ev) {
                self.clickHandle(ev);
            },
            "touchstart": function (ev) {
                ev.preventDefault();
                var oe = ev.originalEvent;
                self.clickHandle(oe.touches[0]);
            }
        });
    }
    if (hoverHandle) {
        element.on({
            "mousemove": function (ev) {
                self.hoverHandle(ev);
            },
            "touchmove": function (ev) {
                ev.preventDefault();
                var oe = ev.originalEvent;
                self.hoverHandle(oe.touches[0]);
            },
            "mouseout": function () {
                self.hoverHandle(null);
            },
            "touchend": function (ev) {
                ev.preventDefault();
                self.hoverHandle(null);
            },
            "touchcancel": function (ev) {
                ev.preventDefault();
                self.hoverHandle(null);
            }
        });
    }
}

HoverManager.prototype.reset = function (width, height) {
    this._width = (width === undefined) ? this.element.width() : width;
    this._height = (height === undefined) ? this.element.height() : height;
    this.canvas.width = this._width;
    this.canvas.height = this._height;
    var context = this.canvas.getContext("2d");
    context.width = this._width;
    context.height = this._height;
    context.rect(0, 0, this._width, this._height);
    context.fillStyle = "#000000";
    context.fill();
    this.keys = {};
};

HoverManager.prototype.hoverHandle = function (ev) {
    var id = 0;
    var p = [0, 0];
    if (ev) {
        p = getCursorPos(ev, this.element);
        var x = toInt(p[0] + this._offset_x);
        var y = toInt(p[1] + this._offset_y);
        if (this._wrap_x && (x >= this._width)) x = toInt(x - this._width);
        var context = this.canvas.getContext("2d");
        var data = context.getImageData(x, y, 1, 1).data;
        id = data[0] * 65536 + data[1] * 256 + data[2];
    }
    if (id in this.keys) this._hH(this.keys[id], p[0], p[1]);
    else this._hH(0, p[0], p[1]);
};

HoverManager.prototype.clickHandle = function (ev) {
    var p = getCursorPos(ev, this.element);
    var x = toInt(p[0] + this._offset_x);
    var y = toInt(p[1] + this._offset_y);
    if (this._wrap_x && (x >= this._width)) x = toInt(x - this._width);
    var context = this.canvas.getContext("2d");
    var data = context.getImageData(x, y, 1, 1).data;
    var id = data[0] * 65536 + data[1] * 256 + data[2];
    if (id in this.keys) this._cH(this.keys[id], p[0], p[1]);
    else this._cH(0, p[0], p[1]);
};

HoverManager.prototype.dblClickHandle = function (ev) {
    var p = getCursorPos(ev, this.element);
    var x = toInt(p[0] + this._offset_x);
    var y = toInt(p[1] + this._offset_y);
    if (this._wrap_x && (x >= this._width)) x = toInt(x - this._width);
    var context = this.canvas.getContext("2d");
    var data = context.getImageData(x, y, 1, 1).data;
    var id = data[0] * 65536 + data[1] * 256 + data[2];
    if (id in this.keys) this._dH(this.keys[id], p[0], p[1]);
};

HoverManager.prototype.hoverPolygon = function (id, path, filled) {
    var key = toInt(Math.random() * 14680063 + 1048576);
    var col = "#" + key.toString(16);
    var context = this.canvas.getContext("2d");
    context.beginPath();
    context.moveTo(path[0][0], path[0][1]);
    for (var i = 1; i < path.length; i++) context.lineTo(path[i][0], path[i][1]);
    context.closePath();
    if (filled) {
        context.fillStyle = col;
        context.fill();
    } else {
        context.strokeStyle = col;
        context.lineWidth = 12;
        context.stroke();
    }
    this.keys[key] = id;
};

HoverManager.prototype.hoverCircle = function (id, x, y, r) {
    var key = parseInt(Math.random() * 14680063 + 1048576);
    col = "#" + key.toString(16);
    var context = this.canvas.getContext("2d");
    context.beginPath();
    context.arc(x, y, r, 0, 2 * Math.PI);
    context.fillStyle = col;
    context.fill();
    this.keys[key] = id;
};

HoverManager.prototype.hoverLine = function (id, x0, y0, x1, y1) {
    var key = toInt(Math.random() * 14680063 + 1048576);
    var col = "#" + key.toString(16);
    var context = this.canvas.getContext("2d");
    context.beginPath();
    context.moveTo(x0, y0);
    context.lineTo(x1, y1);
    context.lineWidth = 15;
    context.strokeStyle = col;
    context.stroke();
    this.keys[key] = id;
};

HoverManager.prototype.hoverBox = function (id, x, y, w, h) {
    var key = toInt(Math.random() * 14680063 + 1048576);
    var col = "#" + key.toString(16);
    var context = this.canvas.getContext("2d");
    context.beginPath();
    context.rect(x, y, w, h);
    context.fillStyle = col;
    context.fill();
    this.keys[key] = id;
};


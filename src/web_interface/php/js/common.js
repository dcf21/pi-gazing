// common.js

function toInt(value) {
    return ~~value;
}

function getCursorPos(e, name) {
    var o = name.offset();
    var posx = e.pageX - o.left;
    var posy = e.pageY - o.top;
    return [posx, posy];
}

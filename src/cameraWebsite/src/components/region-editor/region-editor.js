define(['knockout', 'text!./region-editor.html', 'jquery'], function (ko, templateMarkup, jquery) {

    var colour = function (i, count, alpha) {

        var RGB = function (red, green, blue) {
            return {"red": red, "green": green, "blue": blue};
        };

        var HSVToRGB = function (h, s, v) {
            var region, remainder, p, q, t;
            h = (h + 256) % 256;
            if (s > 255) s = 255;
            if (v > 255) {
                v = 255;
            }
            else {
                v = (v * v) >> 8;
            }
            if (s == 0) {
                return {"red": v, "green": v, "blue": v};
            }
            region = parseInt(h / 43);
            remainder = (h - (region * 43)) * 6;
            p = (v * (255 - s)) >> 8;
            q = (v * (255 - ((s * remainder) >> 8))) >> 8;
            t = (v * (255 - ((s * (255 - remainder)) >> 8))) >> 8;
            switch (region) {
                case 0:
                    return RGB(v, p, t);
                case 1:
                    return RGB(q, p, v);
                case 2:
                    return RGB(p, t, v);
                case 3:
                    return RGB(p, v, q);
                case 4:
                    return RGB(t, v, p);
            }
            return RGB(v, q, p);
        };

        var rgb = HSVToRGB(parseInt(i * 255 / (count)), 255, 255);
        return "rgba(" + rgb.red + "," + rgb.green + "," + rgb.blue + "," + alpha + ")";
    };

    var marginWidth = 30;
    var toggleSize = 10;

    function RegionEditor(element, params) {
        var self = this;
        self.element = jquery(element).find("#container");
        self.canvasElement = self.element.find("#canvas").get(0);
        self.imageElement = self.element.find("#image").get(0);
        jquery(self.imageElement).css("top", marginWidth + "px").css("left", marginWidth + "px");
        self.ctx = self.canvasElement.getContext("2d");
        self.polygons = params.polygons;
        self.imageURL = params.imageURL;
        self.imageURLSubscription = null;
        self.draggedPoint = null;
        if (ko.isObservable(params.imageURL)) {
            self.imageURLSubscription = self.imageURL.subscribe(function (newValue) {
                self.setImage(self.imageURL());
            });
        }
        jquery(self.canvasElement).mousedown(function (event) {
            self.draggedPoint = self.pointAt(event.offsetX - marginWidth, event.offsetY - marginWidth);
        });
        jquery(self.canvasElement).mouseup(function (event) {
            if (self.draggedPoint != null) {
                self.draggedPoint = null;
                self.drawCanvas();
            }
        });
        jquery(self.canvasElement).mouseleave(function (event) {
            if (self.draggedPoint != null) {
                self.draggedPoint = null;
                self.drawCanvas();
            }
        });
        jquery(self.canvasElement).mousemove(function (event) {
            var width = self.imageElement.clientWidth;
            var height = self.imageElement.clientHeight;
            var x = Math.min(Math.max(event.offsetX - marginWidth, 0), width - 1);
            var y = Math.min(Math.max(event.offsetY - marginWidth, 0), height - 1);
            if (self.draggedPoint != null) {
                self.draggedPoint.x = x;
                self.draggedPoint.y = y;
                self.drawCanvas();
            }
        });

        self.setImage(self.imageURL());
    }

    RegionEditor.prototype.pointAt = function (x, y) {
        var self = this;
        if (self.polygons == null) {
            return null;
        }
        for (var polygonIndex = 0; polygonIndex < self.polygons().length; polygonIndex++) {
            for (var pointIndex = 0; pointIndex < self.polygons()[polygonIndex].length; pointIndex++) {
                var point = self.polygons()[polygonIndex][pointIndex];
                if (x < point.x + toggleSize / 2 && x > point.x - toggleSize / 2 && y < point.y + toggleSize / 2 && y > point.y - toggleSize / 2) {
                    return point;
                }
            }
        }
        return null;
    };

    RegionEditor.prototype.setImage = function (imageURL) {
        var self = this;
        jquery(self.imageElement).attr("src", imageURL).load(function () {
            var width = self.imageElement.clientWidth;
            var height = self.imageElement.clientHeight;
            self.ctx.canvas.height = height + marginWidth * 2;
            self.ctx.canvas.width = width + marginWidth * 2;
            self.element.width(width + marginWidth * 2).height(height + marginWidth * 2);
            self.drawCanvas();
        });
    };

    /**
     * Function to refresh the canvas, sets the size (and therefore clears all the polygons, then draws
     * polygons from the polygon array.
     */
    RegionEditor.prototype.drawCanvas = function () {
        var self = this;
        var width = self.ctx.canvas.width;
        var height = self.ctx.canvas.height;
        var max = 1;
        var ctx = self.ctx;
        var numberOfPolygons = self.polygons().length;
        var colours = Math.max(5, numberOfPolygons);
        ctx.clearRect(0, 0, width, height);
        for (var polygonIndex = 0; polygonIndex < numberOfPolygons; polygonIndex++) {
            var polygon = self.polygons()[polygonIndex];
            if (polygon.length > 0) {
                ctx.fillStyle = colour(polygonIndex, colours, 0.3);
                ctx.strokeStyle = colour(polygonIndex, colours, 1);
                ctx.beginPath();
                ctx.moveTo(polygon[0].x + marginWidth, polygon[0].y + marginWidth);
                for (var i = 1; i < polygon.length; i++) {
                    ctx.lineTo(polygon[i].x + marginWidth, polygon[i].y + marginWidth);
                }
                ctx.stroke();
                ctx.closePath();
                ctx.fill();
                for (i = 0; i < polygon.length; i++) {
                    ctx.beginPath();
                    ctx.rect(polygon[i].x + marginWidth - toggleSize / 2, polygon[i].y + marginWidth - toggleSize / 2, toggleSize, toggleSize);
                    ctx.stroke();
                    ctx.fill();
                }
            }
        }
    };

    RegionEditor.prototype.dispose = function () {
        var self = this;
        if (self.imageURLSubscription != null) {
            self.imageURLSubscription.dispose();
        }
    };

    return {
        viewModel: {
            createViewModel: function (params, componentInfo) {
                return new RegionEditor(componentInfo.element, params);
            }
        },
        template: templateMarkup
    };

});

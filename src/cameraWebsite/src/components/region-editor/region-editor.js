define(['knockout', 'text!./region-editor.html', 'jquery'], function (ko, templateMarkup, jquery) {

        /**
         * Get an RGBA format colour string, spacing colours around the colour wheel with full value and
         * saturation, and alpha determined explicitly.
         * @param i the colour number
         * @param count the maximum colour number
         * @param alpha the alpha value (float) to return
         * @returns {string} an rgba(...) format string usable with canvas strokes etc.
         */
        var colour = function (i, count, alpha) {

            var RGB = function (r, g, b) {
                return {"red": r, "green": g, "blue": b};
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
                    return RGB(v, v, v);
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


        /**
         * Canvas based editor used to define an array of polygon regions, displayed on top of an image.
         * @param element
         * @param params
         * @constructor
         */
        function RegionEditor(element, params) {
            var self = this;
            /**
             * Get the image-space coordinates for a mouse event on the canvas, this takes margins into account.
             * @param event
             * @returns {{x: number, y: number}}
             */
            var eventCoordinates = function (event) {
                return {
                    x: Math.min(Math.max(event.offsetX - marginWidth, 0), self.imageElement.clientWidth - 1),
                    y: Math.min(Math.max(event.offsetY - marginWidth, 0), self.imageElement.clientHeight - 1)
                };
            };
            self.element = jquery(element).find("#container");
            self.canvasElement = self.element.find("#canvas").get(0);
            self.imageElement = self.element.find("#image").get(0);
            jquery(self.imageElement).css("top", marginWidth + "px").css("left", marginWidth + "px");
            self.ctx = self.canvasElement.getContext("2d");
            self.polygons = params.polygons;
            if (ko.isObservable(params.polygons)) {
                self.polygonsSubscription = self.polygons.subscribe(function (newValue) {
                    self.draggedPoint = null;
                    self.activePolygon = null;
                    self.drawCanvas();
                });
            }
            self.imageURL = params.imageURL;
            self.imageURLSubscription = null;
            self.draggedPoint = null;
            self.activePolygon = null;
            if (ko.isObservable(params.imageURL)) {
                self.imageURLSubscription = self.imageURL.subscribe(function () {
                    self.setImage(self.imageURL());
                });
            }
            jquery(self.canvasElement).mousedown(function (event) {
                var coords = eventCoordinates(event);
                self.draggedPoint = self.pointAt(coords.x, coords.y);
                if (self.draggedPoint == null) {
                    self.activePolygon = self.polygonAt(coords.x, coords.y);
                } else {
                    self.activePolygon = self.draggedPoint.polygonIndex;
                }
                self.drawCanvas();
            });
            jquery(self.canvasElement).mouseup(function () {
                if (self.draggedPoint != null) {
                    self.draggedPoint = null;
                    self.drawCanvas();
                }
            });
            jquery(self.canvasElement).mouseleave(function () {
                if (self.draggedPoint != null) {
                    self.draggedPoint = null;
                    self.drawCanvas();
                }
            });
            jquery(self.canvasElement).mousemove(function (event) {
                // If we're dragging something...
                if (self.draggedPoint != null) {
                    var coords = eventCoordinates(event);
                    self.draggedPoint.point.x = coords.x;
                    self.draggedPoint.point.y = coords.y;
                    if (event.shiftKey) {
                        nearbyPoints = self.pointsNear(coords.x, coords.y, toggleSize, self.draggedPoint.polygonIndex);
                        if (nearbyPoints.length > 0) {
                            self.draggedPoint.point.x = nearbyPoints[0].point.x;
                            self.draggedPoint.point.y = nearbyPoints[0].point.y;
                        }
                    }
                    self.drawCanvas();
                }
            });

            self.setImage(self.imageURL());
        }

        /**
         * Get the first (lowest index) polygon under the given image-space point, or null if none was found. With
         * thanks to http://www.ecse.rpi.edu/Homepages/wrf/Research/Short_Notes/pnpoly.html for the algorithm.
         * @param x
         * @param y
         * @returns {*}
         */
        RegionEditor.prototype.polygonAt = function (x, y) {
            var self = this;
            var test = function isPointInPoly(poly) {
                for (var c = false, i = -1, l = poly.length, j = l - 1; ++i < l; j = i)
                    ((poly[i].y <= y && y < poly[j].y) || (poly[j].y <= y && y < poly[i].y))
                    && (x < (poly[j].x - poly[i].x) * (y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x)
                    && (c = !c);
                return c;
            };
            for (var polygonIndex = 0; polygonIndex < self.polygons().length; polygonIndex++) {
                if (test(self.polygons()[polygonIndex])) {
                    return polygonIndex;
                }
            }
            return null;
        };

        /**
         * Get the first point at the specified image coordinates (note - not canvas coordinates as these vary based on the
         * border), returning it or null if no point is found under the given coordinate values. Returns the first point
         * found, so will prefer polygon 0 over polygon 1, for example. If a selected polygon exists then we prefer to use it
         * @param x
         * @param y
         * @returns {point: the point pair, an object of x,y; polygonIndex: which polygon? pointIndex: index in polygon}
         */
        RegionEditor.prototype.pointAt = function (x, y) {
            var self = this;
            if (self.polygons == null) {
                return null;
            }
            var bestPoint = null;
            for (var polygonIndex = 0; polygonIndex < self.polygons().length; polygonIndex++) {
                for (var pointIndex = 0; pointIndex < self.polygons()[polygonIndex].length; pointIndex++) {
                    var point = self.polygons()[polygonIndex][pointIndex];
                    if (x < point.x + toggleSize / 2 && x > point.x - toggleSize / 2 && y < point.y + toggleSize / 2 && y > point.y - toggleSize / 2) {
                        /**
                         * If we have an active polygon, and this point is in it, return immediately. If we don't have
                         * an active polygon, also return immediately.
                         */
                        if (self.activePolygon == null ||
                            (self.activePolygon != null && self.activePolygon == polygonIndex)) {
                            return {
                                point: point,
                                polygonIndex: polygonIndex,
                                pointIndex: pointIndex
                            };
                        }
                        /**
                         * Otherwise stash the point if we haven't found one, and continue
                         */
                        else if (bestPoint == null) {
                            bestPoint = {
                                point: point,
                                polygonIndex: polygonIndex,
                                pointIndex: pointIndex
                            };
                        }
                    }
                }
            }
            return bestPoint;
        };


        RegionEditor.prototype.pointsWithinBox = function (x, y, boxWidth) {
            var self = this;
            var result = [];
            if (self.polygons == null) {
                return result;
            }
            for (var polygonIndex = 0; polygonIndex < self.polygons().length; polygonIndex++) {
                for (var pointIndex = 0; pointIndex < self.polygons()[polygonIndex].length; pointIndex++) {
                    var point = self.polygons()[polygonIndex][pointIndex];
                    if (x < point.x + boxWidth / 2 && x > point.x - boxWidth / 2 && y < point.y + boxWidth / 2 && y > point.y - boxWidth / 2) {
                        result.push({
                            point: point,
                            polygonIndex: polygonIndex,
                            pointIndex: pointIndex
                        });
                    }
                }
            }
            return result;
        };

        /**
         * Return an array of points, sorted by increasing distance from the target coordinates and, optionally,
         * omitting any point where coordinates are exactly equal to the target.
         * @param x test X value
         * @param y test Y value
         * @param range range in pixels
         * @param excludePolygon to prevent results from a given polygon (typically a point being dragged)
         * @returns [{point: {x,y}, polgonIndex:int, pointIndex: int, distance:number}]
         */
        RegionEditor.prototype.pointsNear = function (x, y, range, excludePolygon) {
            var self = this;
            return self.pointsWithinBox(x, y, range * 2).map(function (p) {
                return {
                    point: p.point,
                    polygonIndex: p.polygonIndex,
                    pointIndex: p.pointIndex,
                    distance: Math.sqrt(Math.pow(p.point.x - x, 2) + Math.pow(p.point.y - y, 2))
                }
            }).filter(function (p) {
                if (excludePolygon >= 0) {
                    return p.distance <= range && p.polygonIndex != excludePolygon;
                }
                else {
                    return p.distance <= range;
                }
            }).sort(function (a, b) {
                return a.distance - b.distance;
            });
        };

        /**
         * Used to set the image URL, also acts to resize the various HTML components incuding the Canvas
         * element. Implicitly clears the display. The image is placed inside the top level component with
         * a margin around it to help with selecting points on the edge, the margin size is set by the
         * marginWidth variable.
         * @param imageURL
         */
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
            var ctx = self.ctx;
            var numberOfPolygons = self.polygons().length;
            var colours = Math.max(5, numberOfPolygons);
            ctx.clearRect(0, 0, width, height);
            for (var polygonIndex = 0; polygonIndex < numberOfPolygons; polygonIndex++) {
                var polygon = self.polygons()[polygonIndex];
                if (polygon.length > 0) {
                    // Draw the polygon outline and fill
                    var fillOpacity = self.activePolygon != null && self.activePolygon == polygonIndex ? 0.5 : 0.2;
                    ctx.fillStyle = colour(polygonIndex, colours, fillOpacity);
                    ctx.strokeStyle = colour(polygonIndex, colours, 1);
                    ctx.beginPath();
                    ctx.moveTo(polygon[0].x + marginWidth, polygon[0].y + marginWidth);
                    for (var i = 1; i < polygon.length; i++) {
                        ctx.lineTo(polygon[i].x + marginWidth, polygon[i].y + marginWidth);
                    }
                    // Stroke, then close path, then fill, to leave one edge without a stroke
                    ctx.stroke();
                    ctx.closePath();
                    ctx.fill();
                    // Draw the toggles around each point in the polygon
                    for (i = 0; i < polygon.length; i++) {
                        ctx.beginPath();
                        ctx.rect(
                            polygon[i].x + marginWidth - toggleSize / 2,
                            polygon[i].y + marginWidth - toggleSize / 2,
                            toggleSize,
                            toggleSize);
                        ctx.stroke();
                        ctx.fill();
                    }
                }
            }
        };

        /**
         * Get rid of explicit observable subscriptions
         */
        RegionEditor.prototype.dispose = function () {
            var self = this;
            if (self.imageURLSubscription) {
                self.imageURLSubscription.dispose();
            }
            if (self.polygonsSubscription) {
                self.polygonsSubscription.dispose();
            }
        };

        /**
         * Return the viewmodel, binding the top level element at the same time so the constructor
         * can locate the canvas etc.
         */
        return {
            viewModel: {
                createViewModel: function (params, componentInfo) {
                    return new RegionEditor(componentInfo.element, params);
                }
            },
            template: templateMarkup
        };

    }
);

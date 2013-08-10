"use strict";

/*global window, jQuery, _, google */

(function ($) {

  var latitude = function (value) {
    value = parseFloat(value);
    if (value > 90) {
      return NaN;
    }
    if (value < -90) {
      return NaN;
    }
    return value;
  };

  var longitude = function (value) {
    value = parseFloat(value);
    if (value > 180) {
      return NaN;
    }
    if (value < -180) {
      return NaN;
    }
    return value;
  };

  // Geobox

  var BadArgumentException = function () {};

  var Geobox = function () {
    this.name = null;
    this.longName = null;
    this.type = null;
    this.south = null;
    this.north = null;
    this.west = null;
    this.east = null;

    if (!arguments.length) {
      return;
    }

    try {
      this.setFromObject.apply(this, arguments);
      return;
    } catch (e) {
      if (!(e instanceof BadArgumentException)) {
        throw e;
      }
    }

    try {
      this.setFromGoogleBounds.apply(this, arguments);
      return;
    } catch (e) {
      if (!(e instanceof BadArgumentException)) {
        throw e;
      }
    }

    try {
      this.setFromCoords.apply(this, arguments);
      return;
    } catch (e) {
      if (!(e instanceof BadArgumentException)) {
        throw e;
      }
    }

    try {
      this.setFromCoordsString.apply(this, arguments);
      return;
    } catch (e) {
      if (!(e instanceof BadArgumentException)) {
        throw e;
      }
    }

    if (_.isString(arguments[0])) {
      this.name = arguments[0];
    }

    return;
  };

  Geobox.prototype.setFromCoords = function (south, north, west, east) {
    south = latitude(south);
    if (isNaN(south)) {
      throw new BadArgumentException();
    }
    north = latitude(north);
    if (isNaN(north)) {
      throw new BadArgumentException();
    }
    west = longitude(west);
    if (isNaN(west)) {
      throw new BadArgumentException();
    }
    east = longitude(east);
    if (isNaN(east)) {
      throw new BadArgumentException();
    }
    this.south = south;
    this.north = north;
    this.west = west;
    this.east = east;
  };

  Geobox.prototype.setFromCoordsString = function (string) {
    if (! _.isString(string)) {
      throw new BadArgumentException();
    }
    var coords = string.split(",");
    if (coords.length != 4) {
      throw new BadArgumentException();
    }
    return this.setFromCoords.apply(this, coords);
  };

  Geobox.prototype.setFromObject = function (obj) {
    if (!_.isObject(obj)) {
      throw new BadArgumentException();
    }
    if (!(
      obj.hasOwnProperty("south") &&
        obj.hasOwnProperty("north") &&
        obj.hasOwnProperty("west") &&
        obj.hasOwnProperty("east")
    )) {
      throw new BadArgumentException();
    }

    if (obj.hasOwnProperty("name")) {
      this.name = obj.name;  // toString
    }
    if (obj.hasOwnProperty("longName")) {
      this.longName = obj.longName;  // toString
    }
    if (obj.hasOwnProperty("type")) {
      this.type = obj.type;  // toString
    }
    return this.setFromCoords(
      obj.south,
      obj.north,
      obj.west,
      obj.east
    );
  };

  Geobox.prototype.setFromGoogleBounds = function(bounds) {
    if (!(bounds instanceof google.maps.LatLngBounds)) {
      throw new BadArgumentException();
    }
    var southWest = bounds.getSouthWest();
    var northEast = bounds.getNorthEast();
    return this.setFromCoords(
      southWest.lat(),
      northEast.lat(),
      southWest.lng(),
      northEast.lng()
    );
  };

  Geobox.prototype.hasCoords = function () {
    return !(
      isNaN(parseFloat(this.south)) ||
        isNaN(parseFloat(this.north)) ||
        isNaN(parseFloat(this.west)) ||
        isNaN(parseFloat(this.east))
    );
  };

  Geobox.prototype.toText = function () {
    if (!!this.name) {
      return this.name;
    }
    if (this.hasCoords()) {
      return this.south + ", " + this.north + ", " + this.west + ", " + this.east;
    }
    return "";
  };

  Geobox.prototype.toString = function () {
    return this.toText();
  };

  Geobox.prototype.toCoords = function () {
    return {
      south: this.south,
      north: this.north,
      west: this.west,
      east: this.east
    }
  };

  Geobox.prototype.coordsDifference = function (g2) {
    var g1 = this;
    if (!g1.hasCoords() && !g2.hasCoords()) {
      return false;
    }
    if (!g1.hasCoords() || !g2.hasCoords()) {
      return true;
    }
    var latitude = Math.abs(g1.south - g2.south) + Math.abs(g1.north - g2.north);
    var longitude = Math.abs(g1.west - g2.west) + Math.abs(g1.east - g2.east);
    latitude /= (Math.abs(g1.south - g1.north) + Math.abs(g2.south - g2.north));
    longitude /= (Math.abs(g1.west - g1.east) + Math.abs(g2.west - g2.east));
    return latitude + longitude;
  };

  Geobox.prototype.difference = function (g2) {
    var g1 = this;
    if (g1.name !== g2.name) {
      return true;
    }
    return this.coordsDifference(g2);
  }

  Geobox.prototype.area = function () {
    var radiusOfEarth = 6378.1;
    // var circumferenceOfEarth = 40075;
    // var areaOfEarth = 510072000;

    var east = this.east + 360 * (this.east < this.west);
    var height = (
      Math.sin(this.north * Math.PI / 180) -
      Math.sin(this.south * Math.PI / 180)
    );
    var segmentArea = 2 * Math.PI * radiusOfEarth * height * radiusOfEarth;
    var sliceArea = segmentArea * (east - this.west) / 360;
    return sliceArea;
  };

  Geobox.prototype.scale = function (scale) {
    if (!this.hasCoords()) {
      return this;
    }
    var move = (1 - Math.max(0, scale)) / 2;
    var latitude = (this.north - this.south);
    var longitude = this.east - this.west + 360 * (this.east < this.west);
    this.south = Math.max(-90, Math.min(90, this.south + latitude * move));
    this.north = Math.max(-90, Math.min(90, this.north - latitude * move));
    this.west = Math.max(-180, Math.min(180, this.west + longitude * move));
    this.east = Math.max(-180, Math.min(180, this.east - longitude * move));
    return this;
  };

  Geobox.prototype.contains = function (other) {
    var south = this.south <= other.south;
    var north = this.north >= other.north;
    var west = this.west <= other.west;
    var east = this.east >= other.east;
    return south && north && west && east;
  };

  Geobox.prototype.matchesTarget = function (target) {
    var contains = this.contains(target);
    var bigEnough = target.area() > this.area() / 8;  // Estimate
    return contains && bigEnough;
  };

  window.Geobox = Geobox;

}(jQuery));
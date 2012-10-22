"use strict";

/*global window, jQuery, _, Backbone, m, google */

(function ($) {

  // Map

  var alpha = function (index) {
    index %= (26 * 2);
    if (index >= 26) {
      index += 6;
    }
    index += 65;
    return String.fromCharCode(index);
  };

  var mapOptions = {
    zoom: 6,
    center: new google.maps.LatLng(51.498772, -0.1309738),
    mapTypeControl: false,
    streetViewControl: false
  };

  var mapStyles = [
    {
      featureType: "all",
      elementType: "all",
      stylers: [
        { gamma: 1.3 },
        { saturation: -50 }
      ]
    }
  ];

  var styledMapOptions = {
    name: "Grey"
  };

  var greyMapType = new google.maps.StyledMapType(
    mapStyles,
    styledMapOptions
  );

  window.MapView = Backbone.View.extend({
    tagName: "div",
    id: "mango-map-box",

    initialize: function () {
      this.markers = [];
      this.dots = [];
      this.render();
    },

    render: function () {
      if (!this.$canvas) {
        this.$canvas = $("<div id='mango-map-canvas'>Map loading...</div>");
        this.$el.html(this.$canvas);
      }

      this.map = new google.maps.Map(
        this.$canvas[0],
        mapOptions
      );

      var map = this.map;

      this.map.mapTypes.set('grey', greyMapType);
      this.map.setMapTypeId('grey');

      return this;
    },

    contains: function (latitude, longitude) {
      var bounds = this.map.getBounds();
      var point = new google.maps.LatLng(latitude, longitude);
      return bounds.contains(point);
    },

    addMapListener: function (name, callback) {
      return google.maps.event.addListener(this.map, name, callback);
    },

    setBounds: function (geobox) {
      var sw = new google.maps.LatLng(geobox.south, geobox.west);
      var ne = new google.maps.LatLng(geobox.north, geobox.east);
      var bounds = new google.maps.LatLngBounds(sw, ne);
      this.map.fitBounds(bounds);
    },

    clearMarkers: function (latitude, longitude) {
      while (this.markers.length) {
        var marker = this.markers.pop(0);
        marker.setMap(null);
      }
      while (this.dots.length) {
        var dot = this.dots.pop(0);
        dot.setMap(null);
      }
    },

    markerIconUrl: function (style, color, letter) {
      return "/static/image/map/marker/" + style + "-" + color + "-" + letter + ".png";
    },

    dotIconUrl: function (color) {
      return "/static/image/map/marker/dot-" + color + ".png";
    },

    addMarker: function (latitude, longitude, color) {
      color = color || "ee6666";

      var position = new google.maps.LatLng(
        latitude,
        longitude
      );
      var letter = alpha(this.markers.length);
      var pinIconUrl = this.markerIconUrl("pin", color, letter);
      var marker = new google.maps.Marker({
        position: position,
        map: this.map,
        icon: pinIconUrl,
      });

      marker.setZIndex(-(this.markers.length + this.dots.length));

      this.markers.push(marker);

      var circleIconUrl = this.markerIconUrl("circle", color, letter);
      var $circle = $("<img>").attr({
        src: circleIconUrl,
        "class": "map-marker-circle"
      });
      return $circle;
    },

    addDot: function (latitude, longitude, color) {
      color = color || "ee6666";

      var position = new google.maps.LatLng(
        latitude,
        longitude
      );
      var dotIconUrl = this.dotIconUrl(color);
      var marker = new google.maps.Marker({
        position: position,
        map: this.map,
        icon: dotIconUrl,
        title: "Title"
      });

      marker.setZIndex(-(this.markers.length + this.dots.length));

      var helper = function () {};

      google.maps.event.addListener(marker, 'click', helper());
      this.dots.push(marker);
    }
  });

}(jQuery));
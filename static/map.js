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
    zoom: 5,
    center: new google.maps.LatLng(54.666, -4.196),
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

    log: function() {},

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

      this.mapReady = false;
      
      var map = this.map;

      this.map.mapTypes.set('grey', greyMapType);
      this.map.setMapTypeId('grey');

      return this;
    },

    contains: function (latitude, longitude) {
      var bounds = this.map.getBounds();
      if (!bounds) {
        return false;
      }
      var point = new google.maps.LatLng(latitude, longitude);
      return bounds.contains(point);
    },

    addMapListener: function (name, callback) {
      return google.maps.event.addListener(this.map, name, callback);
    },

    setGeobox: function (geobox) {
      if (!geobox.hasCoords()) {
        return;
      }
      if (geobox.south > geobox.north) {
        throw "Inverted bounds";
      }
      var sw = new google.maps.LatLng(geobox.south, geobox.west);
      var ne = new google.maps.LatLng(geobox.north, geobox.east);
      var bounds = new google.maps.LatLngBounds(sw, ne);
      this.log("setGeobox", geobox, bounds);
      this.map.fitBounds(bounds);
      this.target = geobox;
    },

    getGeobox: function () {
      if (!this.mapReady) {
        return null;
      }
      var geobox = new Geobox(this.map.getBounds());
      return geobox;
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
      return m.urlRoot + "static/image/map/marker/" + style + "-" + color + "-" + letter + ".png";
    },

    dotIconUrl: function (color) {
      return m.urlRoot + "static/image/map/marker/dot-" + color + ".png";
    },

    clickDraggableMarker: function (callback, latitude, longitude) {
      var mapView = this;
      var splitCallback = function (position) {
        callback(position.lat(), position.lng());
      };

      var putMarker = function (latitude, longitude) {
        mapView.clearMarkers();
        if (!latitude || !longitude) {
          return;
        }
        var position = new google.maps.LatLng(latitude, longitude);
        var marker = new google.maps.Marker({
          position: position,
          map: mapView.map,
          draggable: true
        });
        google.maps.event.addListener(marker, 'drag', function () {
          splitCallback(marker.getPosition());
        });
        mapView.markers.push(marker);
      };
      
      google.maps.event.addListener(mapView.map, 'click', function (event) {
        var pos = event.latLng;
        putMarker(pos.lat(), pos.lng());
        splitCallback(pos);
      });

      putMarker(latitude, longitude);

      return putMarker;
    },

    addMarker: function (latitude, longitude, color) {
      color = color || "ee6666";

      var circleIconUrl;

      if (latitude && longitude) {
        var position = new google.maps.LatLng(
          latitude,
          longitude
        );
        var letter = alpha(this.markers.length);
        var pinIconUrl = this.markerIconUrl("pin", color, letter);
        var marker = new google.maps.Marker({
          position: position,
          map: this.map,
          icon: pinIconUrl
        });

        marker.setZIndex(-(this.markers.length + this.dots.length));

        this.markers.push(marker);

        circleIconUrl = this.markerIconUrl("circle", color, letter);
      } else {
        circleIconUrl = this.markerIconUrl("circle", "dddddd", "%3F");
      }

      var $circle = $("<img>").attr({
        src: circleIconUrl,
        "class": "map-marker-circle"
      });
      return $circle;
    },

    addDot: function (latitude, longitude, color, title, onClick) {
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
        title: title
      });

      marker.setZIndex(-(this.markers.length + this.dots.length));

      if (onClick) {
        google.maps.event.addListener(marker, 'click', onClick);
      }
      this.dots.push(marker);
    },

    fit: function() {
      if (!this.markers.length) {
        this.setGeobox(m.ukGeobox.scale(0.75));
        return;
      }
      var bounds = new google.maps.LatLngBounds();
      _.each(this.markers, function(marker) {
        var south = new google.maps.LatLng(
          marker.position.lat(),
          marker.position.lng() - 0.01
        );
        var north = new google.maps.LatLng(
          marker.position.lat(),
          marker.position.lng() + 0.01
        );
        bounds.extend(south);
        bounds.extend(north);
      });
      this.map.fitBounds(bounds);
    }
  });

}(jQuery));
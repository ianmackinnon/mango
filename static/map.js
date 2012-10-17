"use strict";

/*global window, jQuery, _, Backbone, m, google */

(function ($) {

  // Map

  var alpha = function (index) {
    index %= (26 * 2);
    if (index > 26) {
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

      this.map.mapTypes.set('grey', greyMapType);
      this.map.setMapTypeId('grey');

      return this;
    },

    clearMarkers: function (latitude, longitude) {
      while (this.markers.length) {
        var marker = this.markers.pop(0);
        marker.setMap(null);
      }
    },

    markerIconUrl: function (style, color, letter) {
      return "/static/image/map/marker/" + style + "-" + color + "-" + letter + ".png";
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
      this.markers.push(marker);

      var circleIconUrl = this.markerIconUrl("circle", color, letter);
      var $circle = $("<img>").attr({
        src: circleIconUrl,
        "class": "map-marker-circle"
      });
      return $circle;
    }
  });

}(jQuery));
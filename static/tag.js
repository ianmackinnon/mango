"use strict";

/*global window, jQuery, _, Backbone, m */

(function ($) {

  // Tag

  window.Tag = Backbone.Model.extend({
    toAutocomplete: function () {
      return {
        value: this.get("base_short"),
        label: this.get("base_short") + " (" + this.get("path") + ")"
      };
    }
  });

  window.Orgtag = window.Tag.extend({
    urlRoot: m.urlRoot + "organisation-tag",
  });

  window.Eventtag = window.Tag.extend({
    urlRoot: m.urlRoot + "event-tag",
  });

  window.OrgtagCollection = Backbone.Collection.extend({
    url: m.urlRoot + "organisation-tag",
    model: window.Orgtag,

    parse: function (response) {
      response = _.sortBy(response, function (orgtag) {
        return orgtag["name_short"];
      });
      return response;
    }
  });

  window.EventtagCollection = Backbone.Collection.extend({
    url: m.urlRoot + "event-tag",
    model: window.Eventtag,

    parse: function (response) {
      response = _.sortBy(response, function (orgtag) {
        return orgtag["name_short"];
      });
      return response;
    }
  });

}(jQuery));

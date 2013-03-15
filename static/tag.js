"use strict";

/*global window, jQuery, _, Backbone, m */

(function ($) {

  // Tag

  window.Tag = Backbone.Model.extend({
    toAutocomplete: function () {
      return {
        value: this.get("base_short"),
        label: this.get("name")
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
    model: window.Orgtag
  });

  window.EventtagCollection = Backbone.Collection.extend({
    url: m.urlRoot + "event-tag",
    model: window.Eventtag
  });

}(jQuery));

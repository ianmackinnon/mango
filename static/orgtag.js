"use strict";

/*global window, jQuery, _, Backbone, m */

(function ($) {

  // Orgtag

  window.Orgtag = Backbone.Model.extend({
    urlRoot: m.urlRoot + "organisation-tag",

    toAutocomplete: function () {
      return {
        value: this.get("short"),
        label: this.get("short") + " (" + this.get("name") + ")"
      };
    }
  });

  window.OrgtagCollection = Backbone.Collection.extend({
    url: m.urlRoot + "organisation-tag",
    model: window.Orgtag
  });

}(jQuery));

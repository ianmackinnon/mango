/*global window, jQuery, _, Backbone, m */

(function ($) {
  "use strict";

  // Address

  window.Address = Backbone.Model.extend({
    urlRoot: m.urlRoot + "address"
  });

  window.AddressCollection = Backbone.Collection.extend({
    initialize: function (models, options) {
      options = options ? _.clone(options) : {};
      if (options.org) {
        this.org = options.org;
      }
      if (options.event) {
        this.event = options.event;
      }
    }
  });

}(jQuery));

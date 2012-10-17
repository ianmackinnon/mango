"use strict";

/*global window, jQuery, _, Backbone, m */

(function ($) {

  // Address

  window.Address = Backbone.Model.extend({
    urlRoot: m.urlRoot + "address"
  });

  window.AddressCollection = Backbone.Collection.extend({
  });


}(jQuery));
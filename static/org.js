"use strict";

/*globals jQuery */
/*globals Backbone */
/*globals m */
/*jslint indent: 2 */

(function ($) {

  window.Org = Backbone.Model.extend({
    urlRoot: m.urlRoot + "organisation"
  });

  window.OrgCollection = Backbone.Collection.extend({
    url: m.urlRoot + "organisation",
    parse: function(resp, xhr) {
      if (!!resp) {
        self.geobox = resp["geobox"];
        self.latlon = resp["latlon"];
        self.count = resp["org_count"];
        return resp["org_list"];
      }
      return resp;
    }
  });

  

  window.OrgViewBox = Backbone.View.extend({
    tagName: "div",
    className: "org-box",
    templateName: "org-box.html",
    render: function() {
      $(this.el).html(m.template(this.templateName, {
        org: this.model.toJSON(),
        m: m,
        parameters: m.parameters,
        geobox: this.model.collection.geobox,
        note: false,
      }));
      return this;
    }
  });


  window.OrgCollectionView = Backbone.View.extend({
    tagName: "div",
    className: "column",
    initialize: function() {
      var that = this;
      this._modelViews = [];
      this.collection.each(function(model) {
        that._modelViews.push(new OrgViewBox({
          model: model,
        }));
      });
    },

    render: function() {
      var that = this;
      $(this.el).empty();
      _(this._modelViews).each(function(modelView) {
        $(that.el).append(modelView.render().el);
      });
      return this;
    }
  });

}(jQuery));
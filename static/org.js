"use strict";

/*globals jQuery */
/*globals Backbone */
/*globals Mango */
/*jslint indent: 2 */

(function ($) {

  window.Org = Backbone.Model.extend({
    urlRoot: Mango.urlRoot + "organisation"
  });

  window.OrgCollection = Backbone.Collection.extend({
    url: Mango.urlRoot + "organisation",
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
    template: new Mango.Template("org-box.html"),
    render: function() {
      var view = this;
      this.template.string().done(function(result) {
        if (result == null) return;
        $(view.el).html(_.template(result, {
          org: view.model.toJSON(),
          m: m,
          parameters: m.parameters,
          geobox: view.model.collection.geobox,
          note: false
        }));
      });
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
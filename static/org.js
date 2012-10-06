"use strict";

/*global window, jQuery, _, Backbone, m */

(function ($) {

  // Org

  window.Org = Backbone.Model.extend({
    urlRoot: m.urlRoot + "organisation"
  });

  window.OrgViewBox = Backbone.View.extend({
    tagName: "div",
    className: "org-box",
    templateName: "org-box.html",
    render: function () {
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


  // OrgCollection

  window.OrgCollection = Backbone.Collection.extend({
    url: m.urlRoot + "organisation",
    parse: function (resp, xhr) {
      if (!!resp) {
        this.geobox = resp.geobox;
        this.latlon = resp.latlon;
        this.count = resp.org_count;
        return resp.org_list;
      }
      return resp;
    }
  });

  window.OrgCollectionView = Backbone.View.extend({
    tagName: "div",
    className: "column",
    initialize: function () {
      var that = this;
      this._modelViews = [];
      this.collection.each(function (model) {
        that._modelViews.push(new window.OrgViewBox({
          model: model,
        }));
      });
    },

    render: function () {
      var that = this;
      $(this.el).empty();
      _(this._modelViews).each(function (modelView) {
        $(that.el).append(modelView.render().el);
      });
      return this;
    }
  });


  // OrgSearch

  window.OrgSearch = Backbone.Model.extend({
    save: function (data, callback) {
      var orgCollection = new window.OrgCollection();
      orgCollection.fetch({
        data: _.extend(data, {
          unique: Math.random()
        }),
        success: function (collection, response) {
          callback(orgCollection);
        },
        error: m.fetchError
      });

    }
  });

  window.OrgSearchView = Backbone.View.extend({
    tagName: "form",
    className: "org-search",
    templateName: "org-search.html",
    events: {'submit': 'submit'},

    initialize: function () {
      this.$orgColumn = this.options.$orgColumn;
    },
    render: function () {
      $(this.el).html(m.template(this.templateName, this.model.toJSON()));
      return this;
    },
    submit: function (event) {
      event.preventDefault();
      this.save();
    },
    save: function () {
      var arr = this.$el.serializeArray();
      var data = _(arr).reduce(function (acc, field) {
        acc[field.name] = field.value;
        return acc;
      }, {});
      var orgSearchView = this;

      this.model.save(data, function (orgCollection) {
        var orgCollectionView = new window.OrgCollectionView({
          collection: orgCollection
        });
        orgSearchView.$orgColumn.replaceWith(orgCollectionView.render().el);
        orgSearchView.$orgColumn = orgCollectionView.render().$el;
      });
    }
  });

}(jQuery));
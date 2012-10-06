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
      var searchId = Math.random();
      orgCollection.fetch({
        data: _.extend(data, {
          searchId: searchId
        }),
        success: function (collection, response) {
          callback(orgCollection);
        },
        error:   function(collection, response) {
          console.log("error", collection, response);
          callback(null);
        }
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
      this.activeSearches = 0;
      if ("$source" in this.options) {
        var data = this.serialize(this.options.$source);
        this.model.set(data);
        this.options.$source.replaceWith(this.render().el);
      }
    },
    render: function () {
      $(this.el).html(m.template(this.templateName, this.model.toJSON()));
      return this;
    },
    submit: function (event) {
      event.preventDefault();
      this.send();
    },
    serialize: function($el) {
      var arr = $el.serializeArray();
      return _(arr).reduce(function (acc, field) {
        acc[field.name] = field.value;
        return acc;
      }, {});
    },
    send: function () {
      var data = this.serialize(this.$el);
      var orgSearchView = this;

      orgSearchView.activeSearches++;
      console.log(orgSearchView.activeSearches);
      this.model.save(data, function (orgCollection) {
        orgSearchView.activeSearches--;
        console.log(orgSearchView.activeSearches);
        if (!orgCollection) return;
        var orgCollectionView = new window.OrgCollectionView({
          collection: orgCollection
        });
        var rendered = orgCollectionView.render();
        orgSearchView.$orgColumn.replaceWith(rendered.el);
        orgSearchView.$orgColumn = rendered.$el;
      });
    }
  });

}(jQuery));
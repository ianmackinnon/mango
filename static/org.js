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
        error:   function (collection, response) {
          console.log("error", collection, response);
          callback(null);
        }
      });

    }
  });

  window.OrgSearchView = Backbone.View.extend({
    tagName: "form",
    id: "org-search",
    templateName: "org-search.html",
    events: {
      'submit': 'submit',
      'change input[name="visibility"]': 'formChange',
      'change input[name="nameSearch"]': 'formChange',
      'change input[name="lookup"]': 'formChange',
      'change label > input[name="tag"]': 'formChange'
    },

    initialize: function () {
      this.$orgColumn = this.options.$orgColumn;
      this.activeSearches = 0;
      if (this.options.hasOwnProperty("$source")) {
        var data = this.serialize(this.options.$source);
        this.model.set(data);
        this.render();
        var $el = this.$el;
        var view = this;
        this.options.$source.replaceWith($el);

        m.getOrgtagDictionary(function (error, orgtags) {
          var orgtagKeys = m.arrayKeys(orgtags);
          var $input = $el.find("input[name='tag']");

          window.$input = $input;

          $input.tagit({
            placeholderText: $input.attr("placeholder"),
            tagSource: function (search, showChoices) {
              var values = m.filterStartFirst(search.term, orgtagKeys);
              var choices = [];
              _(values).each(function (value) {
                choices.push({
                  value: value,
                  label: value + " (" + orgtags[value] + ")"
                });
              });
              showChoices(choices);
            },
            onTagAddedAfter: function (event, tag) {
              $input.trigger("change");
            },
            onTagRemovedAfter: function (event, tag) {
              $input.trigger("change");
            },
          });

          view.addThrobber();
        });
      }
    },

    render: function () {
      $(this.el).html(m.template(this.templateName, {
        currentUser: m.currentUser,
        orgSearch: this.model.toJSON()
      }));
      return this;
    },

    submit: function (event) {
      event.preventDefault();
      this.send();
    },

    serialize: function ($el) {
      if ($el === undefined) {
        $el = this.$el;
      }
      var arr = $el.serializeArray();
      return _(arr).reduce(function (acc, field) {
        acc[field.name] = field.value;
        return acc;
      }, {});
    },

    send: function () {
      var data = this.serialize();
      var orgSearchView = this;

      orgSearchView.searchStartHook();
      this.model.save(data, function (orgCollection) {
        orgSearchView.searchEndHook();
        if (!orgCollection) {
          return;
        }
        var orgCollectionView = new window.OrgCollectionView({
          collection: orgCollection
        });
        var rendered = orgCollectionView.render();
        orgSearchView.$orgColumn.replaceWith(rendered.el);
        orgSearchView.$orgColumn = rendered.$el;
      });
    },

    searchStartHook: function () {
      this.activeSearches += 1;
      this.searchUpdateHook();
    },

    searchEndHook: function () {
      this.activeSearches -= 1;
      this.searchUpdateHook();
    },

    searchUpdateHook: function () {
      if (this.activeSearches > 0) {
        this.$throbber.show();
      } else {
        this.$throbber.hide();
      }
    },

    addThrobber: function () {
      this.$throbber = $('<img class="throbber" width="16px" height="16px" alt="Loading." src="/static/image/throbber.gif" style="display: none;">');
      this.$el.find(".actions").prepend(this.$throbber);
      return this.$throbber;
    },

    formChange: function (event) {
      this.send();
    },

  });

}(jQuery));
"use strict";

/*global window, jQuery, _, Backbone, m */

(function ($) {

  // Address

  var AddressViewRow = Backbone.View.extend({
    tagName: "div",
    className: "address-row",
    templateName: "address-row.html",

    initialize: function () {
      this.mapView = this.options.mapView;
    },

    render: function () {
      var view = this;

      $(this.el).html(m.template(this.templateName, {
        address: this.model.toJSON(),
        m: m,
        parameters: m.parameters,
      }));

      var $circle = view.mapView.addMarker(
        this.model.get("latitude"),
        this.model.get("longitude")
      );
      var $pin = $("<div class='pin'>").append($circle);
      view.$el.prepend($pin);

      return this;
    }
  });

  var AddressViewDot = Backbone.View.extend({
    initialize: function () {
      this.mapView = this.options.mapView;
    },

    render: function () {
      var view = this;

      view.mapView.addDot(
        this.model.get("latitude"),
        this.model.get("longitude")
      );

      return this;
    }
  })

  var AddressCollectionViewRows = Backbone.View.extend({
    tagName: "div",
    className: "org_address_list",

    initialize: function () {
      var view = this;

      view.mapView = this.options.mapView;
      view.letters = this.options.letters;

      this._modelViews = [];
      var bounds = view.mapView.map.getBounds();
      this.collection.each(function (model) {
        if (view.letters.length) {
          var point = new google.maps.LatLng(
            model.get("latitude"),
            model.get("longitude")
          );
          if (bounds.contains(point)) {
            view._modelViews.push(new AddressViewRow({
              model: model,
              mapView: view.mapView,
              letter: view.letters.shift()
            }));
            return;
          }
        }
        view._modelViews.push(new AddressViewDot({
          model: model,
          mapView: view.mapView
        }));
      });
    },

    render: function () {
      var view = this;
      view.$el.empty();
      _(this._modelViews).each(function (modelView) {
        view.$el.append(modelView.render().$el);
      });
      return this;
    }
  });



  // Org

  window.Org = Backbone.Model.extend({
    urlRoot: m.urlRoot + "organisation",

    parse: function (resp, xhr) {
      this.addressCollection = new window.AddressCollection(resp.address_list);
      delete resp.address_list;
      return resp;
    }
  });

  window.OrgViewBox = Backbone.View.extend({
    tagName: "div",
    className: "org-box",
    templateName: "org-box.html",

    initialize: function () {
      this.mapView = this.options.mapView;
      this.letters = this.options.letters;
    },

    render: function () {
      var view = this;

      if (!!this.letters.length) {
        $(this.el).html(m.template(this.templateName, {
          org: this.model.toJSON(),
          m: m,
          parameters: m.parameters,
          geobox: this.model.collection.geobox,
          note: false,
        }));
      }

      var addressCollectionView = new AddressCollectionViewRows({
        collection: this.model.addressCollection,
        mapView: this.mapView,
        letters: this.letters
      });
      addressCollectionView.render();

      var $addressList = this.$el.find(".org_address_list");
      if ($addressList.length) {
        this.$el.find(".org_address_list").replaceWith(addressCollectionView.$el);
        return this;
      }
    }
  });


  // OrgCollection

  window.OrgCollection = Backbone.Collection.extend({
    model: window.Org,
    url: m.urlRoot + "organisation",

    parse: function (resp, xhr) {
      if (!!resp) {
        this.org_address_count = resp.org_address_count;
        this.location = resp.location;
        return resp.org_list;
      }
      return resp;
    }
  });

  window.OrgCollectionView = Backbone.View.extend({
    tagName: "div",
    className: "column",
    letters: "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split(""),

    initialize: function () {
      var view = this;
      
      view.mapView = this.options.mapView;

      this._modelViews = [];
      this._addressModelViews = [];
      if (this.collection.org_address_count > 26 * 3) {
        this.initializeMany();
      } else {
        this.initializeFew();
      }
    },

    initializeFew: function() {
      var view = this;
      var letters = this.letters.slice(0);
      this.collection.each(function (model) {
        view._modelViews.push(new window.OrgViewBox({
          model: model,
          mapView: view.mapView,
          letters: letters
        }));
      });
    },

    initializeMany: function() {
      var view = this;
      this.collection.each(function (model) {
        model.addressCollection.each(function (addressModel) {
          view._modelViews.push(new AddressViewDot({
            model: addressModel,
            mapView: view.mapView
          }));
        });
      });
    },

    render: function () {
      var view = this;
      $(this.el).empty();
      view.mapView.clearMarkers();
      
      _(this._modelViews).each(function (modelView) {
        var viewRendered = modelView.render();
        if (!!viewRendered) {
          $(view.el).append(viewRendered.$el);
        }
      });
      _(this._addressModelViews).each(function (addressModelView) {
        addressModelView.render();
      });
      return this;
    }
  });


  // OrgSearch

  window.OrgSearch = Backbone.Model.extend({
    save: function (data, callback) {
      data = data || {};
      var orgCollection = new window.OrgCollection();
      var searchId = Math.random();
      orgCollection.fetch({
        data: _.extend(data, {
          searchId: searchId
        }),
        success: function (collection, response) {
          if (!!callback) {
            callback(orgCollection);
          }
        },
        error:   function (collection, response) {
          console.log("error", collection, response);
          if (!!callback) {
            callback(null);
          }
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
      'change input[name="location"]': 'formChange',
      'change label > input[name="tag"]': 'formChange'
    },

    initialize: function () {
      this.$orgColumn = this.options.$orgColumn;
      this.activeSearches = 0;
      if (this.options.hasOwnProperty("$source")) {
        var data = this.serialize(this.options.$source);
        this.model.set(data);
        this.mapView = this.options.mapView;
        this.render();
        var $el = this.$el;
        var view = this;

        this.ignoreMapMove = true;
        this.mapIdleListener = google.maps.event.addListener(
          this.mapView.map,
          'idle',
          function () {
            if (view.ignoreMapMove) {
              view.ignoreMapMove = false;
              return;
            }
            var bounds = view.mapView.map.getBounds();
            var geobox = m.mapBoundsToGeobox(bounds);

            if (m.geoboxArea(geobox) > 50000) {
              $el.find("input[name='location']").val("");
            } else {
              $el.find("input[name='location']").val(m.geoboxToString(geobox));
            }
            view.send();
          }
        );
        
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
        
        if (orgCollection.location) {
          var shrunk = m.shrinkGeobox(orgCollection.location);
          orgSearchView.ignoreMapMove = true;
          orgSearchView.mapView.setBounds(shrunk);
        }

        var orgCollectionView = new window.OrgCollectionView({
          collection: orgCollection,
          mapView: orgSearchView.mapView
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
      if (this.$throbber) {
        this.$throbber.toggle(!!this.activeSearches);
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

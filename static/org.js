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
  });

  var AddressCollectionViewRows = Backbone.View.extend({
    tagName: "div",
    className: "org_address_list",

    initialize: function () {
      var view = this;

      view.mapView = this.options.mapView;
      view.limit = this.options.limit;

      this._modelViews = [];
      this.collection.each(function (model) {
        if (!model.get("latitude")) {
          view._modelViews.push(new AddressViewRow({
            model: model,
            mapView: view.mapView,
          }));
          return;
        }
        if (view.mapView.contains(
          model.get("latitude"),
          model.get("longitude")
        )) {
          if (view.limit.offset <= 0 && view.limit.limit > 0) {
            view._modelViews.push(new AddressViewRow({
              model: model,
              mapView: view.mapView,
            }));
            view.limit.limit -= 1;
            return;
          }
          view._modelViews.push(new AddressViewDot({
            model: model,
            mapView: view.mapView
          }));
          view.limit.offset -= 1;
          return;
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
      this.limit = this.options.limit;
    },

    render: function () {
      var view = this;

      $(this.el).html(m.template(this.templateName, {
        org: this.model.toJSON(),
        m: m,
        parameters: m.parameters,
        geobox: this.model.collection.geobox,
        note: false,
      }));

      var addressCollectionView = new AddressCollectionViewRows({
        collection: this.model.addressCollection,
        mapView: this.mapView,
        limit: this.limit
      });
      addressCollectionView.render();

      var $addressList = this.$el.find(".org_address_list");
      if ($addressList.length) {
        if (addressCollectionView.$el.find(".address-row").length) {
          this.$el.find(".org_address_list")
            .replaceWith(addressCollectionView.$el);
          return this;
        }
      }
    }
  });


  // OrgCollection

  window.OrgCollection = Backbone.Collection.extend({
    model: window.Org,
    url: m.urlRoot + "organisation",

    addressLength: function () {
      var sum = 0;
      this.each(function (model) {
        model.addressCollection.each(function (addressModel) {
          sum += 1;
        });
      });
      return sum;
    },

    parse: function (resp, xhr) {
      if (!!resp) {
        this.location = resp.location;
        return resp.org_list;
      }
      return resp;
    }
  });

  window.OrgCollectionView = Backbone.View.extend({
    tagName: "div",
    className: "column",

    initialize: function () {
      var view = this;

      view.mapView = this.options.mapView;
      view.offset = this.options.offset;
      view.limit = this.options.limit;

      this._modelViews = [];
      this._addressModelViews = [];
      view.many = null;
      if (this.collection.addressLength() > view.limit * 3) {
        // Just dots if there are more than 3 pages
        view.many = true;
        this.collection.each(function (model) {
          model.addressCollection.each(function (addressModel) {
            view._modelViews.push(new AddressViewDot({
              model: addressModel,
              mapView: view.mapView
            }));
          });
        });
      } else {
        view.many = false;
        var limit = {
          "offset": view.offset,
          "limit": view.limit
        };
        this.collection.each(function (model) {
          view._modelViews.push(new window.OrgViewBox({
            model: model,
            mapView: view.mapView,
            limit: limit
          }));
        });
      }
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

  //   more than 26 results: results get paged
  //   more than 3 pages of results, don't show any results
  //   location area is too big, search whole world
  //     (won't reload results on map move).

  window.OrgSearch = Backbone.Model.extend({
    initialize: function () {
      this.lastRequest = null;
      this.lastResult = null;
    },

    big: function () {
      var geobox = m.stringToGeobox(this.get("location"));
      if (geobox) {
        return  m.geoboxArea(geobox) > 50000;
      }
      return false;
    },
    
    save: function (callback, cache) {
      if (cache === undefined) {
        cache = true;
      }
      var model = this;
      var sendData = _.extend(_.clone(model.attributes) || {}, {
        json: true,  // Prevent browser caching result in HTML page history.
        offset: 0,
      });

      if (this.big()) {
        sendData.location = null;  // Cache big searches.
      }

      console.log("save", sendData);

      if (cache) {
        if (JSON.stringify(sendData) == JSON.stringify(model.lastRequest)) {
          callback(model.lastResult);
          return;
        }
      }

      model.lastRequest = _.clone(sendData);

      var orgCollection = new window.OrgCollection();
      orgCollection.fetch({
        data: sendData,
        success: function (collection, response) {
          if (!!callback) {
            model.lastResult = collection;
            callback(orgCollection);
          }
        },
        error:   function (collection, response) {
          console.log("error", collection, response);
          if (!!callback) {
            model.lastResult = null;
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
    limit: 26,  // Number of letters in the alphabet for map markers.

    changeOffset: function () {
      var $input = this.$el.find("input[name='offset']");
      if ($input.val() != this.model.get("offset")) {
        $input.val(this.model.get("offset"));
      }
    },

    changeLocation: function () {
      var $input = this.$el.find("input[name='location']");
      if ($input.val() != this.model.get("location")) {
        $input.val(this.model.get("location"));
      }
    },

    initialize: function () {
      _.bindAll(this, "render", "changeLocation", "changeOffset");
      this.model.bind("change:location", this.changeLocation);
      this.model.bind("change:offset", this.changeOffset);

      this.$orgColumn = this.options.$orgColumn;
      this.$orgPaging = this.options.$orgPaging;
      this.mapView = this.options.mapView;

      console.log("initialize", this.serialize(this.options.$source));
      this.model.set(this.serialize(this.options.$source));

      this.activeSearches = 0;

      var view = this;

      this.ignoreMapMove = true;
      this.mapIdleListener = this.mapView.addMapListener("idle", function () {
        if (view.ignoreMapMove) {
          view.ignoreMapMove = false;
          return;
        }
        var bounds = view.mapView.map.getBounds();
        var geobox = m.mapBoundsToGeobox(bounds);
        view.model.set({
          location: m.geoboxToString(geobox),
          offset: 0
        });
        view.send();
      });
      
      this.orgtagCollection = new window.OrgtagCollection();
      this.orgtagCollection.fetch().complete(this.render);
    },

    setupTagInput: function () {
      if (!this.orgtagCollection) {
        return;
      }
      var view = this;

      var $input = view.$el.find("input[name='tag']");
      $input.tagit({
        placeholderText: $input.attr("placeholder"),
        tagSource: function (search, showChoices) {
          var start = [];
          var middle = [];
          view.orgtagCollection.each(function(orgtag) {
            var index = orgtag.get("short").toLowerCase().indexOf(search.term);
            if (index === 0) {
              start.push(orgtag.toAutocomplete());
            } else if (index > 0) {
              middle.push(orgtag.toAutocomplete());
            }
          });
          showChoices(start.concat(middle));
        },
        onTagAddedAfter: function (event, tag) {
          $input.trigger("change");
        },
        onTagRemovedAfter: function (event, tag) {
          $input.trigger("change");
        },
      });
    },

    render: function () {
      $(this.el).html(m.template(this.templateName, {
        currentUser: m.currentUser,
        orgSearch: this.model.toJSON()
      }));
      this.setupTagInput();
      this.addThrobber();
      return this;
    },

    submit: function (event) {
      event.preventDefault();
      this.send(false);
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

    send: function (cache) {
      if (cache === undefined) {
        cache = true;
      }
      this.model.set(this.serialize());
      var orgSearchView = this;

      orgSearchView.searchStartHook();
      this.model.save(function (orgCollection) {
        orgSearchView.searchEndHook();
        if (!orgCollection) {
          return;
        }

        if (orgCollection.location && orgCollection.location.name) {
          var shrunk = m.shrinkGeobox(orgCollection.location);
          orgSearchView.ignoreMapMove = true;
          orgSearchView.mapView.setBounds(shrunk);
        }

        var orgCollectionView = new window.OrgCollectionView({
          collection: orgCollection,
          mapView: orgSearchView.mapView,
          offset: orgSearchView.model.get("offset"),
          limit: orgSearchView.limit
        });
        var rendered = orgCollectionView.render();
        orgSearchView.$orgColumn.replaceWith(rendered.el);
        orgSearchView.$orgColumn = rendered.$el;

        orgSearchView.renderPages(orgCollection, orgCollectionView.many);
      }, cache);
    },

    renderPages: function (orgCollection, many) {
      var orgSearchView = this;
      var length = orgCollection.addressLength();

      orgSearchView.$orgPaging.empty();
      
      if (many) {
        return;
      }
      
      if (length <= orgSearchView.limit) {
        return;
      }

      var $count = $("<span class='resultCount'>").text(length + " results");
      orgSearchView.$orgPaging.append($count);

      var $pages = $("<ul class='pageList'>");

      var helper = function(page) {
        return function (e) {
          if (e.which !== 1 || e.metaKey || e.shiftKey) {
            return;
          }
          e.preventDefault();
          orgSearchView.model.set("offset", page * orgSearchView.limit);
          orgSearchView.send();
        };
      }

      for (var page = 0; page < length / orgSearchView.limit; page += 1) {
        var text = "page " + (page + 1);
        if (page * orgSearchView.limit == orgSearchView.model.get("offset")) {
          var $pageSpan = $("<span>").text(text);
          $pages.append($("<li>").append($pageSpan));
        } else {
          var href = "/";
          var $pageLink = $("<a>").attr("href", href).text(text);
          $pageLink.bind("click", helper(page));
          $pages.append($("<li>").append($pageLink));
        }
      }
      orgSearchView.$orgPaging.append($pages);
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
      console.log("formchange", this.serialize());
      this.model.set(this.serialize());
      this.send();
    },

  });

}(jQuery));
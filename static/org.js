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

      var onClick = function (event) {
        var href=view.model.collection.org.get("url");
        window.document.location.href=href;
      };

      view.mapView.addDot(
        this.model.get("latitude"),
        this.model.get("longitude"),
        undefined,
        this.model.collection.org.get("name"),
        onClick
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
      this.addressCollection = new window.AddressCollection(
        resp.address_list,
        {
          org: this
        }
      );
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
      
      if (model.request) {
        model.request.abort();
      }
      model.request = orgCollection.fetch({
        data: sendData,
        success: function (collection, response) {
          if (!!callback) {
            model.lastResult = collection;
            model.request = null;
            model.trigger("request", model.request);
            callback(orgCollection);
          }
        },
        error:   function (collection, response) {
          if (response.statusText !== "abort") {
            console.log("error", collection, response);
          }
          if (!!callback) {
            model.lastResult = null;
            model.request = null;
            model.trigger("request", model.request);
            callback(null);
          }
        }
      });
      this.trigger("request", this.request);
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
      _.bindAll(
        this,
        "render",
        "changeLocation",
        "changeOffset",
        "changeVisibility",
        "onModelRequest"
      );
      this.model.bind("change:location", this.changeLocation);
      this.model.bind("change:offset", this.changeOffset);
      this.model.bind("change:visibility", this.changeVisibility);
      this.model.bind("request", this.onModelRequest);

      this.$orgColumn = this.options.$orgColumn;
      this.$orgPaging = this.options.$orgPaging;
      this.mapView = this.options.mapView;

      console.log("initialize", this.serialize(this.options.$source));
      this.model.set(this.serialize(this.options.$source));

      this.activeSearches = 0;

      var view = this;

      this.mapView.addMapListener("dragend", function () {
        var bounds = view.mapView.map.getBounds();
        var geobox = m.mapBoundsToGeobox(bounds);
        view.model.set({
          location: m.geoboxToString(geobox),
          offset: 0
        });
        view.send();
      });

      this.orgtagCollection = new window.OrgtagCollection();
      this.fetchOrgtagList().complete(this.render);
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

    changeVisibility: function () {
      this.fetchOrgtagList();
    },

    fetchOrgtagList: function () {
      if (!this.orgtagCollection) {
        return;
      }
      var visibility = this.model.get("visibility");
      if (visibility === 'private' || visibility === 'pending') {
        visibility = 'all';
      }
      if (visibility === this.lastVisibility) {
        return;
      }
      this.lastVisibility = visibility;
      return this.orgtagCollection.fetch({
        data: {
          visibility: visibility
        }
      });
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

    queryString: function (data) {
      data = data ? _.clone(data) : {};

      var serialized = this.serialize();
      
      serialized = _.extend(serialized, data);
      
      return $.param(serialized);
    },

    send: function (cache) {
      if (cache === undefined) {
        cache = true;
      }
      this.model.set(this.serialize());
      var orgSearchView = this;

      this.model.save(function (orgCollection) {
        if (!orgCollection) {
          return;
        }

        if (orgCollection.location) {
          var shrunk = m.shrinkGeobox(orgCollection.location);
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

        orgSearchView.renderPages(orgCollection, orgCollectionView.many);
        orgSearchView.$orgColumn = rendered.$el;
        
        if (orgCollectionView.many) {
          var text = "Zoom in or refine search to see results in detail.";
          var $span = $("<p>").addClass("results-hint").text(text)
          orgSearchView.$orgColumn.append($span);
        }
      }, cache);
    },

    renderPages: function (orgCollection, many) {
      var orgSearchView = this;
      var length = orgCollection.addressLength();

      orgSearchView.$orgPaging.empty();
      
      var $count = $("<span class='resultCount'>").text(length + " results");
      orgSearchView.$orgPaging.append($count);

      if (many) {
        return;
      }
      
      if (length <= orgSearchView.limit) {
        return;
      }

      var $pages = $("<ul class='pageList'>");

      var clickHelper = function(page) {
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
          var query = orgSearchView.queryString({
            offset: page * orgSearchView.limit
          });
          var href = m.urlRoot + "organisation?" + query
          var $pageLink = $("<a>").attr("href", href).text(text);
          $pageLink.bind("click", clickHelper(page));
          $pages.append($("<li>").append($pageLink));
        }
      }
      orgSearchView.$orgPaging.append($pages);
    },

    onModelRequest: function (request) {
      if (this.$throbber) {
        this.$throbber.toggle(!!request);
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

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
      if (!resp) {
        return resp;
      }

      this.location = resp.location;
      return resp.org_list;
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

  var geoboxFactory = function (value) {
    return new window.Geobox(value);
  };

  var geoboxToString = function (geobox) {
    return geobox.toText();
  };

  var ukGeobox = new window.Geobox({
    "south":49.829,
    "north":58.988,
    "west":-12.304,
    "east":3.912
  });

  window.OrgSearch = Backbone.Model.extend({
    // constructor, multiConstructor, compare, default, toString
    expectedParameters: {
      "nameSearch": [null, false, m.compareLowercase, "", null],
      "location": [geoboxFactory, false, m.compareGeobox, ukGeobox, geoboxToString],
      "offset": [parseInt, false, null, 0, null],
      "tag": [m.argumentMulti, m.argumentMulti, m.compareUnsortedList, [], m.multiToString],
      "visibility": [m.argumentVisibility, false, null, "public", null]
    },

    initialize: function () {
      this.lastRequest = null;
      this.lastResult = null;
    },

    typedAttributes: function (attributes) {
      var model = this;

      attributes = attributes ? _.clone(attributes) : {};

      _.each(attributes, function(value, key) {
        if (!_.has(model.expectedParameters, key)) {
          delete attributes[key];
          return;
        }
        if (value === null) {
          return;
        }

        var constructor = model.expectedParameters[key][0];
        if (constructor) {
          value = constructor(value);
        }

        var comparison = model.expectedParameters[key][2];
        var defaultValue = model.expectedParameters[key][3];
        if (!!comparison) {
          if (!comparison(value, defaultValue)) {
            value = null;
          }
        } else {
          if (value === defaultValue) {
            value = null;
          }
        }
        attributes[key] = value;
      });
      return attributes;
    },

    differentAttributes: function (attributes) {
      var model = this;

      attributes = attributes ? _.clone(attributes) : {};

      attributes = this.typedAttributes(attributes);

      _.each(attributes, function(value, key) {
        if (model.get(key) === undefined || model.get(key) === null) {
          return;
        }
        var comparison = model.expectedParameters[key][2];
        if (!!comparison) {
          if (!comparison(model.get(key), attributes[key])) {
            delete attributes[key];
            return;
          }
        } else {
          if (model.get(key) === attributes[key]) {
            delete attributes[key];
            return;
          }
        }
      });
      return attributes;
    },

    set: function (attributes, options) {
      if (attributes === null) {
        return this;
      }

      if (!_.isObject(attributes)) {
        var key = attributes;
        (attributes = {})[key] = options;
        options = arguments[2];
      }

      if (_.isEmpty(attributes)) {
        return this;
      }

      attributes = _.clone(attributes);

      attributes = this.differentAttributes(attributes);
      
      if (!_.isEmpty(attributes) &&
          !attributes.hasOwnProperty("offset") &&
          !!this.get("offset")
         ) {
        attributes["offset"] = null;
      }

      return Backbone.Model.prototype.set.call(this, attributes, options);
    },
    
    save: function (callback, cache) {
      if (cache === undefined) {
        cache = true;
      }
      var model = this;

      var modelData = _.clone(model.attributes);

      var sendData = _.extend(_.clone(model.attributes) || {}, {
        json: true,  // Prevent browser caching result in HTML page history.
        offset: null,
      });

      if (sendData.location && sendData.location.area > 50000) {  // Km
        sendData.location = null;  // Avoid large area searches.
      }

      _.each(sendData, function(value, key) {
        if (_.isNull(value)) {
          delete sendData[key];
        }
      });

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
          // Only add successful page loads to history.
          var queryString = model.toQueryString(modelData);
          queryString = queryString ? "?" + queryString : "";

          if (window.location.search != queryString) {
            var url = m.urlRoot + "organisation";
            url += queryString;
            window.history.pushState(null, null, url);
          }

          if (!!callback) {
            model.lastResult = collection;
            model.request = null;
            model.trigger("request", model.request);
            callback(orgCollection, sendData);
          }
        },
        error: function (collection, response) {
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
    },

    toQueryString: function (attributes) {
      var data = this.attributes ? _.clone(this.attributes) : {};
      attributes = attributes ? _.clone(attributes) : {};
      _.extend(data, attributes);

      var model = this;

      var params = [];
      _.each(data, function(value, key) {
        var defaultValue = model.expectedParameters[key][3];
        var toString = model.expectedParameters[key][4];
        
        if (!_.has(model.expectedParameters, key)) {
          return;
        }
        if (value === null) {
          return;
        }
        if (!!toString) {
          value = toString(value);
        }
        params.push(encodeURIComponent(key) + "=" + encodeURIComponent(value));
      });

      return params.length ? params.join("&") : null;
    },

    attributesFromQueryString: function (query) {
      query = query || window.location.search;

      var model = this;

      var query = window.location.search;
      if (query.indexOf("?") !== 0) {
        return {};
      }
      query = query.substr(1);

      var params = query.split("&");

      var data = {};
      _.each(params, function(param) {
        var index = param.indexOf("=");
        if (index <= 0) {
          return;
        }
        var key = param.slice(0, index);
        if (!_.has(model.expectedParameters, key)) {
          return;
        }

        var value = decodeURIComponent(param.slice(index + 1));
        var constructor = model.expectedParameters[key][0];
        var multiConstructor = model.expectedParameters[key][1];
        
        if (!!multiConstructor) {
          data[key] = multiConstructor(value, data[key]);
        } else if (!!constructor) {
          data[key] = constructor(value);
        } else {
          data[key] = value;
        }
      });
      
      return data;
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

    setMapLocation: function (location) {
      if (!this.mapView.mapReady) {
        return;
      }

      location = location || ukGeobox;

      var mapGeobox = this.mapView.getGeobox();

      if (!m.compareGeobox(location, mapGeobox)) {
        return;
      }

      var scaled = new Geobox(location);
      scaled.scale(.75);
      this.mapView.setGeobox(scaled);

      // In case the map has already moved, but not updated.
      google.maps.event.trigger(this.mapView, "idle");
    },

    changeLocation: function () {
      var location = this.model.get("location");
      var locationVal = location ? location.toText() : "";
      var $input = this.$el.find("input[name='location']");

      if ($input.val() !== locationVal) {
        $input.val(locationVal);
      }

      this.setMapLocation(location);
    },

    initialize: function () {
      _.bindAll(
        this,
        "render",
        "changeLocation",
        "changeOffset",
        "changeVisibility",
        "onModelRequest",
        "popstate"
      );
      this.model.bind("change:location", this.changeLocation);
      this.model.bind("change:offset", this.changeOffset);
      this.model.bind("change:visibility", this.changeVisibility);
      this.model.bind("request", this.onModelRequest);

      this.$results = this.options.$results;
      this.$paging = this.options.$paging;
      this.mapView = this.options.mapView;

      var data = this.serializeForm(this.options.$form);
      this.model.set(data);

      this.activeSearches = 0;

      var view = this;

      this.mapView.addMapListener("idle", function () {

        if (!view.mapView.mapReady) {
          // Set map from object.
          view.mapView.mapReady = true;
          view.setMapLocation(view.model.get("location"));
          view.send();
          return;
        }

        var mapGeobox = view.mapView.getGeobox();
        var modelGeobox = new Geobox(view.model.get("location"));
        var target = view.mapView.target;
        view.mapView.target = null;

        if (mapGeobox && target && mapGeobox.matchesTarget(target)) {
          // Matches target. Do nothing.
          return;
        }

        // Set object from map.

        if (false && modelGeobox.hasCoords()) {
          view.mapView.addDot(modelGeobox.south, modelGeobox.west, "ddddff", "south west", null);
          view.mapView.addDot(modelGeobox.north, modelGeobox.east, "ddddff", "north east", null);
          var scaled = new Geobox(modelGeobox);
          scaled.scale(.75);
          view.mapView.addDot(scaled.south, scaled.west, "ddddff", "south west", null);
          view.mapView.addDot(scaled.north, scaled.east, "ddddff", "north east", null);
        }

        if (!m.compareGeobox(mapGeobox, modelGeobox)) {
          return;
        }
        var data = {
          location: mapGeobox
        };
        view.model.set(data);
        view.send();
      });

      this.render();
      
      this.orgtagCollection = new window.OrgtagCollection();
      var orgtagListRequest = this.fetchOrgtagList();
      if (orgtagListRequest) {
        orgtagListRequest.complete(this.render);
      }
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

    serializeForm: function ($el) {
      if ($el === undefined) {
        $el = this.$el;
      }
      var arr = $el.serializeArray();
      return _(arr).reduce(function (acc, field) {
        acc[field.name] = field.value;
        if (!field.value) {
          acc[field.name] = null;
        }
        return acc;
      }, {});
    },

    send: function (cache) {
      if (cache === undefined) {
        cache = true;
      }

      var orgSearchView = this;

      this.model.save(function (orgCollection) {
        if (!orgCollection) {
          return;
        }

        if (orgCollection.location) {
          var data = {
            location: new Geobox(orgCollection.location)
          }
          orgSearchView.model.set(data);
        }

        var orgCollectionView = new window.OrgCollectionView({
          collection: orgCollection,
          mapView: orgSearchView.mapView,
          offset: orgSearchView.model.get("offset"),
          limit: orgSearchView.limit
        });
        var rendered = orgCollectionView.render();
        orgSearchView.$results.replaceWith(rendered.el);

        orgSearchView.renderPages(orgCollection, orgCollectionView.many);
        orgSearchView.$results = rendered.$el;
        
        if (orgCollectionView.many) {
          var text = "Zoom in or refine search to see results in detail.";
          var $span = $("<p>").addClass("results-hint").text(text)
          orgSearchView.$results.append($span);
        }
      }, cache);
    },

    renderPages: function (orgCollection, many) {
      var orgSearchView = this;
      var length = orgCollection.addressLength();

      orgSearchView.$paging.empty();
      
      var $count = $("<span class='resultCount'>").text(length + " results");
      orgSearchView.$paging.append($count);

      if (many) {
        return;
      }
      
      if (length <= orgSearchView.limit) {
        return;
      }

      var $pages = $("<ul class='pageList'>");

      var pageClickHelper = function(page) {
        return function (e) {
          if (e.which !== 1 || e.metaKey || e.shiftKey) {
            return;
          }
          e.preventDefault();
          var data = {
            offset: page * orgSearchView.limit
          }
          orgSearchView.model.set(data);
          orgSearchView.send();
        };
      }

      for (var page = 0; page < length / orgSearchView.limit; page += 1) {
        var text = "page " + (page + 1);
        var currentPage = orgSearchView.model.get("offset") || 0;
        if (page * orgSearchView.limit == currentPage) {
          var $pageSpan = $("<span>").text(text);
          $pages.append($("<li>").append($pageSpan));
        } else {
          var query = orgSearchView.model.toQueryString({
            offset: page * orgSearchView.limit
          });
          var href = m.urlRoot + "organisation?" + query
          var $pageLink = $("<a>").attr("href", href).text(text);
          $pageLink.bind("click", pageClickHelper(page));
          $pages.append($("<li>").append($pageLink));
        }
      }
      orgSearchView.$paging.append($pages);
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
      var data = this.serializeForm();
      this.model.set(data);
      this.send();
    },

    popstate: function (event) {
      var data = this.model.attributesFromQueryString();
      this.model.set(data);
      this.send();
    }

  });

}(jQuery));

"use strict";

/*global window, jQuery, _, Backbone, m */

(function ($) {

  // Marker

  var Marker = Backbone.Model.extend();

  var MarkerViewDot = Backbone.View.extend({
    initialize: function () {
      this.mapView = this.options.mapView;
    },

    render: function () {
      var view = this;

      var onClick = function (event) {
        var href = m.urlRoot + view.model.get("url").substr(1);
        window.document.location.href=href;
      };

      view.mapView.addDot(
        this.model.get("latitude"),
        this.model.get("longitude"),
        "5577ff",
        this.model.get("name"),
        onClick
      );

      return this;
    }
  });

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
        this.model.get("longitude"),
        "5577ff"
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
        var href=view.model.collection.event.get("url");
        window.document.location.href=href;
      };

      view.mapView.addDot(
        this.model.get("latitude"),
        this.model.get("longitude"),
        undefined,
        this.model.collection.event.get("name"),
        onClick
      );

      return this;
    }
  });

  var AddressCollectionViewRows = Backbone.View.extend({
    tagName: "div",
    className: "event_address_list",

    initialize: function () {
      var view = this;

      view.mapView = this.options.mapView;
      view.limit = this.options.limit;

      this._modelViews = [];
      this.collection.each(function (model) {
        if (!!model.get("latitude") && !view.mapView.contains(
          model.get("latitude"),
          model.get("longitude")
        )) {
          view._modelViews.push(new AddressViewDot({
            model: model,
            mapView: view.mapView
          }));
          return;
        }
        if (view.limit.offset <= 0 && view.limit.offset > -view.limit.limit) {
          view._modelViews.push(new AddressViewRow({
            model: model,
            mapView: view.mapView,
          }));
          view.limit.offset -= 1;
          return;
        }
        view._modelViews.push(new AddressViewDot({
          model: model,
          mapView: view.mapView
        }));
        view.limit.offset -= 1;
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



  // Event

  window.Event = Backbone.Model.extend({
    urlRoot: m.urlRoot + "event",

    parse: function (resp, xhr) {
      this.addressCollection = new window.AddressCollection(
        resp.address_list,
        {
          event: this
        }
      );
      delete resp.address_list;
      return resp;
    }
  });

  window.EventViewBox = Backbone.View.extend({
    tagName: "div",
    className: "event-box",
    templateName: "event-box.html",

    initialize: function () {
      this.mapView = this.options.mapView;
      this.limit = this.options.limit;
    },

    render: function () {
      var view = this;

      var $this = m.$template(this.templateName, {
        event: this.model.toJSON(),
        m: m,
        parameters: m.parameters,
        note: false,
      });

      var insert = true;

      if (this.limit.offset < -this.limit.limit ) {
        insert = false;
      }

      var addressCollectionView = new AddressCollectionViewRows({
        collection: this.model.addressCollection,
        mapView: this.mapView,
        limit: this.limit
      });

      addressCollectionView.render();

      if (!this.model.addressCollection.length) {
        this.limit.offset -= 1;
      }

      if (this.limit.offset > 0 || this.limit.offset === 0) {
        insert = false;
      }

      if (!insert) {
        return;
      }

      $(this.el).empty().append($this);

      var $addressList = this.$el.find(".event_address_list");
      if ($addressList.length) {
        if (addressCollectionView.$el.find(".address-row").length) {
          this.$el.find(".event_address_list")
            .replaceWith(addressCollectionView.$el);
        }
      }

      return this;
    }
  });


  // EventCollection

  window.EventCollection = Backbone.Collection.extend({
    model: window.Event,
    url: m.urlRoot + "event",

    addressLength: function () {
      var sum = 0;
      this.each(function (model) {
        model.addressCollection.each(function (addressModel) {
          sum += 1;
        });
        if (!model.addressCollection.length) {
          sum += 1;
        }
      });
      if (this.markerList) {
        sum += this.markerList.length;
      }
      return sum;
    },

    parse: function (resp, xhr) {
      if (!resp) {
        return resp;
      }
      
      this.location = resp.location;
      this.markerList = resp.marker_list;
      return resp.event_list;
    }
  });

  window.EventCollectionView = Backbone.View.extend({
    tagName: "div",
    className: "column",

    initialize: function () {
      var view = this;

      view.mapView = this.options.mapView;
      view.offset = this.options.offset || 0;
      view.limit = this.options.limit || 0;

      this._modelViews = [];
      this._addressModelViews = [];
      view.many = null;
      if (this.collection.markerList) {
        view.many = true;
        _.each(this.collection.markerList, function (model) {
          view._modelViews.push(new MarkerViewDot({
            model: new Marker(model),
            mapView: view.mapView
          }));
        });
      } else if (this.collection.addressLength() > view.limit * 3) {
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
          offset: view.offset,
          limit: view.limit
        };
        this.collection.each(function (model) {
          view._modelViews.push(new window.EventViewBox({
            model: model,
            mapView: view.mapView,
            limit: limit
          }));
        });
      }
    },

    render: function (append) {
      var view = this;

      $(this.el).empty();

      if (!append) {
        view.mapView.clearMarkers();
      }

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


  // EventSearch

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

  window.EventSearch = Backbone.Model.extend({
    // constructor, multiConstructor, compare, default, toString
    expectedParameters: {
      "nameSearch": [null, false, m.compareLowercase, "", null],
      "location": [geoboxFactory, false, m.compareGeobox, m.ukGeobox, geoboxToString],
      "past": [m.argumentCheckbox, false, null, 0, m.checkboxToString],
      "offset": [parseInt, false, null, 0, null],
      "tag": [m.argumentMulti, m.argumentMulti, m.compareUnsortedList, [], m.multiToString],
      "tagAll": [m.argumentCheckbox, false, null, 0, m.checkboxToString],
      "visibility": [m.argumentVisibility, false, null, "public", null]
    },

    defaultParameters: function () {
      var defaults = {};
      _.each(this.expectedParameters, function(value, key) {
        defaults[key] = value[3];
      });
      return defaults;
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

      m.log.debug("s2", _.clone(attributes));

      _.each(attributes, function(value, key) {
        var c;
        if (model.get(key) === undefined) {
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

      m.log.debug("s1", _.clone(attributes));

      attributes = this.differentAttributes(attributes);
      
      m.log.debug("s3", _.clone(attributes));

      if (!_.isEmpty(attributes) &&
          !attributes.hasOwnProperty("offset") &&
          !!this.get("offset")
         ) {
        attributes["offset"] = null;
      }

      m.log.debug("s4", _.clone(this.attributes), "to", _.clone(attributes));

      return Backbone.Model.prototype.set.call(this, attributes, options);
    },

    testStateChange: function(modelData) {
      var queryString = this.toQueryString(modelData);
      queryString = queryString ? "?" + queryString : "";
      
      if (m.searchString() != queryString) {
        var url = m.urlRoot + "event";
        url += queryString;
        m.log.debug("pushState", queryString);
        if (window.History.enabled) {
          window.History.pushState(null, null, url);
        }
        m.updateVisibilityButtons(url);
      }
    },

    isBig: function (geobox) {
      geobox = geobox || this.get("location");
      return !!geobox && geobox.area() > 500000;  // Km
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

      if (this.isBig(sendData.location)) {
        sendData.location = null;  // Avoid large area searches.
      }

      _.each(sendData, function(value, key) {
        if (_.isNull(value)) {
          delete sendData[key];
        }
      });

      if (cache) {
        if (JSON.stringify(sendData) == JSON.stringify(model.lastRequest)) {
          model.testStateChange(modelData);
          callback(model.lastResult);
          return;
        }
      }

      model.lastRequest = _.clone(sendData);

      var eventCollection = new window.EventCollection();
      
      if (model.request) {
        model.request.abort();
      }
      model.request = eventCollection.fetch({
        data: sendData,
        success: function (collection, response) {
          // Only add successful page loads to history.
          model.testStateChange(modelData);

          if (!!callback) {
            model.lastResult = collection;
            model.request = null;
            model.trigger("request", model.request);
            callback(eventCollection, sendData);
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

      m.log.debug("toQueryString", _.clone(this.attributes), _.clone(attributes), data);

      var model = this;

      var params = [];
      _.each(data, function(value, key) {
        var defaultValue;
        var toString;
        
        if (!_.has(model.expectedParameters, key)) {
          return;
        }
        defaultValue = model.expectedParameters[key][3];
        toString = model.expectedParameters[key][4];
        if (value === null) {
          return;
        }
        if (!!toString) {
          value = toString(value);
        }
        if (value === null) {
          return;
        }
        params.push(encodeURIComponent(key) + "=" + encodeURIComponent(value));
      });

      return params.length ? params.join("&") : null;
    },

    attributesFromQueryString: function (query) {
      query = query || m.searchString();

      var model = this;

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

  window.EventSearchView = Backbone.View.extend({
    tagName: "form",
    id: "event-search",
    templateName: "event-search.html",
    events: {
      'submit': 'submit',
      'change input[name="visibility"]': 'formChange',
      'change input[name="nameSearch"]': 'formChange',
      'change input[name="location"]': 'formChange',
      'change input[name="past"]': 'formChange',
      'change label > input[name="tag"]': 'formChange',
      'change input[name="tagAll"]': 'formChange'
    },
    limit: 26,  // Number of letters in the alphabet for map markers.

    changeOffset: function () {
      var $input = this.$el.find("input[name='offset']");
      if ($input.val() != this.model.get("offset")) {
        $input.val(this.model.get("offset"));
      }
    },

    changeNameSearch: function () {
      var value = this.model.get("nameSearch");
      var text = value || "";
      var $input = this.$el.find("input[name='nameSearch']");

      if ($input.val() !== text) {
        $input.val(text);
      }
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

    changePast: function () {
      var past = this.model.get("past");
      var pastVal = !!past;
      var $input = this.$el.find("input[name='past']");

      if ($input.prop('checked') !== pastVal) {
        $input.prop('checked', pastVal);
      }
    },

    changeTag: function () {
      var value = this.model.get("tag");
      var text = value && value.toString() || "";
      var $input = this.$el.find("input[name='tag']");

      if (!this.tagReady) {
        return;
      }

      if ($input.val() !== text) {
        $input.val(text);
        var data = $.data($input[0]);
        data.tagit.removeAllQuiet();
        _.each(value, function(tagName) {
          data.tagit.createTag(tagName);
        });
      }

    },

    changeVisibility: function () {
      var visibility = this.model.get("visibility") || "public";
      m.setVisibility(visibility);
      this.fetchEventtagList();
    },

    changeTagAll: function () {
      var tagAll = this.model.get("tagAll");
      var tagAllVal = !!tagAll;
      var $input = this.$el.find("input[name='tagAll']");

      if ($input.prop('checked') !== tagAllVal) {
        $input.prop('checked', tagAllVal);
      }
    },

    setMapLocation: function (location) {
      if (!this.mapView.mapReady) {
        return;
      }

      location = location || m.ukGeobox;

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

    initialize: function () {
      _.bindAll(
        this,
        "render",
        "changeNameSearch",
        "changeLocation",
        "changePast",
        "changeTag",
        "changeTagAll",
        "changeOffset",
        "changeVisibility",
        "onModelRequest",
        "popstate"
      );
      this.model.bind("change:nameSearch", this.changeNameSearch);
      this.model.bind("change:location", this.changeLocation);
      this.model.bind("change:past", this.changePast);
      this.model.bind("change:tag", this.changeTag);
      this.model.bind("change:tagAll", this.changeTagAll);
      this.model.bind("change:offset", this.changeOffset);
      this.model.bind("change:visibility", this.changeVisibility);
      this.model.bind("request", this.onModelRequest);

      this.$results = this.options.$results;
      this.$paging = this.options.$paging;
      this.mapView = this.options.mapView;

      var data = this.serializeForm(this.options.$form);
      m.log.debug("set serializeForm", data);
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
          view.mapView.addDot(modelGeobox.south, modelGeobox.west,
                              "ddddff", "south west", null);
          view.mapView.addDot(modelGeobox.north, modelGeobox.east,
                              "ddddff", "north east", null);
          var scaled = new Geobox(modelGeobox);
          scaled.scale(.75);
          view.mapView.addDot(scaled.south, scaled.west,
                              "ddddff", "south west", null);
          view.mapView.addDot(scaled.north, scaled.east,
                              "ddddff", "north east", null);
        }

        if (!m.compareGeobox(mapGeobox, modelGeobox)) {
          return;
        }
        var data = {
          location: mapGeobox
        };
        m.log.debug("set mapIdle", data);
        view.model.set(data);
        view.send();
      });

      this.render();

      this.eventtagCollection = new window.EventtagCollection();
      var eventtagListRequest = this.fetchEventtagList();
      if (eventtagListRequest) {
        eventtagListRequest.complete(this.render);
      }
    },
    
    render: function () {
      $(this.el).html(m.template(this.templateName, {
        currentUser: m.currentUser,
        eventSearch: this.model.toJSON()
      }));
      this.setupTagInput();
      this.addThrobber();
      return this;
    },

    fetchEventtagList: function () {
      if (!this.eventtagCollection) {
        return;
      }

      var visibility = this.model.get("visibility") || null;

      if (visibility === 'private' || visibility === 'pending') {
        visibility = 'all';
      }
      if (visibility === this.lastVisibility) {
        return;
      }
      this.lastVisibility = visibility;
      return this.eventtagCollection.fetch({
        data: {
          visibility: visibility
        }
      });
    },

    setupTagInput: function () {
      if (!this.eventtagCollection) {
        return;
      }
      var view = this;

      var $input = view.$el.find("input[name='tag']");
      this.tagReady = false;
      $input.tagit({
        placeholderText: $input.attr("placeholder"),
        tagSource: function (search, showChoices) {
          var start = [];
          var middle = [];
          view.eventtagCollection.each(function(eventtag) {
            var index = eventtag.get("base_short").toLowerCase().indexOf(search.term);
            if (index === 0) {
              start.push(eventtag.toAutocomplete());
            } else if (index > 0) {
              middle.push(eventtag.toAutocomplete());
            }
          });
          showChoices(start.concat(middle));
        },
        onTagAddedAfter: function (event, tag) {
          if (!view.tagReady) {
            return;
          }
          $input.trigger("change");
        },
        onTagRemovedAfter: function (event, tag) {
          if (!view.tagReady) {
            return;
          }
          $input.trigger("change");
        },
      });
      this.tagReady = true;
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
      var data = _(arr).reduce(function (acc, field) {
        acc[field.name] = field.value;
        if (!field.value) {
          acc[field.name] = null;
        }
        return acc;
      }, {});
      if (!data.hasOwnProperty("past")) {
        data["past"] = false;
      }
      if (!data.hasOwnProperty("tagAll")) {
        data["tagAll"] = false;
      }
      return data;
    },

    send: function (cache) {
      if (cache === undefined) {
        cache = true;
      }

      var eventSearchView = this;

      this.model.save(function (eventCollection) {
        if (!eventCollection) {
          return;
        }

        if (eventCollection.location) {
          var data = {
            location: new Geobox(eventCollection.location)
          }
          m.log.debug("set receive", data);
          eventSearchView.model.set(data);
        }

        var eventCollectionView = new window.EventCollectionView({
          collection: eventCollection,
          mapView: eventSearchView.mapView,
          offset: eventSearchView.model.get("offset"),
          limit: eventSearchView.limit
        });
        var rendered = eventCollectionView.render();
        eventSearchView.$results.replaceWith(rendered.el);

        eventSearchView.renderPages(eventCollection, eventCollectionView.many);
        eventSearchView.$results = rendered.$el;
        
        if (eventCollectionView.many) {
          var text = "Zoom in or refine search to see results in detail.";
          var $span = $("<p>").addClass("results-hint").text(text)
          eventSearchView.$results.append($span);
        }
      }, cache);
    },

    renderPages: function (eventCollection, many) {
      var eventSearchView = this;
      var length = eventCollection.addressLength();

      eventSearchView.$paging.empty();
      
      var $count = $("<span class='resultCount'>").text(length + " results");
      eventSearchView.$paging.append($count);

      if (many) {
        return;
      }
      
      if (length <= eventSearchView.limit) {
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
            offset: page * eventSearchView.limit
          }
          m.log.debug("set pageclick", data);
          eventSearchView.model.set(data);
          eventSearchView.send();
        };
      }

      for (var page = 0; page < length / eventSearchView.limit; page += 1) {
        var text = "page " + (page + 1);
        var currentPage = eventSearchView.model.get("offset") || 0;
        if (page * eventSearchView.limit == currentPage) {
          var $pageSpan = $("<span>").text(text);
          $pages.append($("<li>").append($pageSpan));
        } else {
          var query = eventSearchView.model.toQueryString({
            offset: page * eventSearchView.limit
          });
          var href = m.urlRoot + "event?" + query
          var $pageLink = $("<a>").attr("href", href).text(text);
          $pageLink.bind("click", pageClickHelper(page));
          $pages.append($("<li>").append($pageLink));
        }
      }
      eventSearchView.$paging.append($pages);
    },

    onModelRequest: function (request) {
      if (this.$throbber) {
        this.$throbber.toggle(!!request);
      }
    },

    addThrobber: function () {
      var src = m.urlRoot + "static/image/throbber.gif"
      this.$throbber = $('<img class="throbber" width="16px" height="16px" alt="Loading." src="' + src + '" style="display: none;">');
      this.$el.find(".actions").prepend(this.$throbber);
      return this.$throbber;
    },

    formChange: function (event) {
      var data = this.serializeForm();
      m.log.debug("set formChange", data);
      this.model.set(data);
      this.send();
    },

    popstate: function () {
      var search = m.searchString();
      var data = {};
      data = _.extend(data, this.model.defaultParameters());
      data = _.extend(data, this.model.attributesFromQueryString(search));
      m.log.debug("set popstate", data);
      this.model.set(data);
      this.send();
    }

  });

}(jQuery));

/*global window, jQuery, Backbone, google, m */

(function ($) {
  "use strict";

  // Event

  window.Event = Backbone.Model.extend({
    urlRoot: m.urlRoot + "event",

    parse: function (resp, xhr) {
      this.addressCollection = new window.AddressCollection(
        resp.addressList,
        {
          event: this
        }
      );
      delete resp.addressList;
      return resp;
    }
  });

  window.EventViewBox = Backbone.View.extend({
    tagName: "div",
    className: "event-box",
    templateName: "event-box.html",

    initialize: function (options) {
      this.mapView = options.mapView;
      this.limit = options.limit;
    },

    render: function (callback) {
      var view = this;

      m.templator.renderSync(this.templateName, {
        event: this.model.toJSON(),
        m: m,
        parameters: m.parameters,
        note: false
      }, function (html) {
        var $el = $(html);

        if (view.model.get("description")) {
          $eventDescription = $el.find("div.event_description");
          m.markdownSafe(
            view.model.get("description"),
            false,
            function (html) {
              $eventDescription.html(html);
            }
          );
        }

        var insert = true;

        if (view.limit.offset < -view.limit.limit) {
          insert = false;
        }

        var addressCollectionView = new AddressCollectionViewRows({
          collection: view.model.addressCollection,
          mapView: view.mapView,
          limit: view.limit,
          color: "5577ff",
          entityName: "event"
        });

        addressCollectionView.render();

        if (!view.model.addressCollection.length) {
          view.limit.offset -= 1;
        }

        if (view.limit.offset > 0 || view.limit.offset === 0) {
          insert = false;
        }

        if (!insert) {
          return;
        }

        $(view.el).empty().append($el);

        var $addressList = view.$el.find(".event_address_list");
        if ($addressList.length) {
          if (addressCollectionView.$el.find(".address-row").length) {
            view.$el.find(".event_address_list")
              .replaceWith(addressCollectionView.$el);
          }
        }

        if (_.isFunction(callback)) {
          callback();
        }

      });

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
      this.markerList = resp.markerList;
      this.eventLength = resp.eventLength;
      return resp.eventList;
    }
  });

  window.EventCollectionView = Backbone.View.extend({
    tagName: "div",
    className: "column",

    initialize: function (options) {
      var view = this;
      var limit = {
        offset: null,  // Counter
        limit: null
      };

      view.mapView = options.mapView;
      view.offset = options.offset || 0;
      view.limit = options.limit || 0;

      this._modelViews = [];
      view.many = null;

      if (this.collection.markerList) {
        // ?
        view.many = true;
        limit.offset = 0;  // Server is handling offsets
        limit.limit = view.limitEvent;

        _.each(this.collection.markerList, function (model) {
          view._modelViews.push(new MarkerViewDot({
            model: new Marker(model),
            mapView: view.mapView
          }));
        });

        this.collection.each(function (model) {
          view._modelViews.push(new window.EventViewBox({
            model: model,
            mapView: view.mapView,
            limit: limit
          }));
        });

      } else if (this.collection.addressLength() > view.limit * 3) {
        // Just dots if there are more than 3 pages
        view.many = true;

        this.collection.each(function (model) {
          model.addressCollection.each(function (addressModel) {
            view._modelViews.push(new AddressViewDot({
              model: addressModel,
              mapView: view.mapView,
              entityName: "event"
            }));
          });
        });

      } else {
        // Markers for this page, dots for others
        view.many = false;
        limit.offset = view.offset;  // Browser is handling offsets
        limit.limit = view.limit;

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
        modelView.render(function () {
          $(view.el).append(modelView.$el);
        });
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
    // Parameter list is in the following order:
    // constructor, multiConstructor, compare, default, toString

    expectedParameters: {
      "nameSearch": [null, false, m.compareLowercase, "", null],
      "location": [geoboxFactory, false, m.compareGeobox, m.ukGeobox, geoboxToString],
      "past": [m.argumentCheckbox, false, null, 0, m.checkboxToString],
      "offset": [parseInt, false, null, 0, null],
      "tag": [m.argumentMulti, m.argumentMulti, m.compareUnsortedList, [], m.multiToString],
      "tagAll": [m.argumentCheckbox, false, null, 0, m.checkboxToString],
      "visibility": [m.argumentVisibility, false, m.compareVisibility, "public", null]
    },

    defaultParameters: function () {
      var defaults = {};
      _.each(this.expectedParameters, function (value, key) {
        defaults[key] = value[3];
      });
      return defaults;
    },

    initialize: function (attributes, options) {
      this.lastRequest = null;
      this.lastResult = null;
    },

    typedAttributes: function (attributes) {
      var model = this;

      attributes = attributes ? _.clone(attributes) : {};

      _.each(attributes, function (value, key) {
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

      _.each(attributes, function (value, key) {
        var c;  // Unused
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
        // We're changing state, so reset offset to 0 like a new page.
        attributes.offset = null;
      }

      m.log.debug("s4", _.clone(this.attributes), "to", _.clone(attributes));

      return Backbone.Model.prototype.set.call(this, attributes, options);
    },

    testStateChange: function (modelData) {
      var searchString = m.searchString();
      var queryString = this.toQueryString(modelData);

      if (searchString === queryString) {
        return;
      }

      var searchData = this.attributesFromQueryString(searchString);
      var queryData = this.attributesFromQueryString(queryString);
      searchString = this.toQueryString(
        _.extend(_.clone(this.defaultParameters()), searchData)
      );
      queryString = this.toQueryString(
        _.extend(_.clone(this.defaultParameters()), queryData)
      );

      if (searchString === queryString) {
        return;
      }

      var url = m.urlRoot + "event?" + queryString;
      m.log.debug("pushState", queryString);
      history.pushState(null, null, url);

      m.updateVisibilityButtons(url);
      this.updatePageTitle(modelData);
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
        pageView: "map",
        json: true  // Prevent browser caching result in HTML page history.
      });

      if (this.isBig(sendData.location)) {
        sendData.location = null;  // Avoid large area searches.
      }

      if (model.lastResult && model.lastResult.markerList === undefined) {
        sendData.offset = null;  // Browser handles paging for < 3 pages
      }

      _.each(sendData, function (value, key) {
        if (_.isNull(value)) {
          delete sendData[key];
        }
      });

      if (cache) {
        if (JSON.stringify(sendData) === JSON.stringify(model.lastRequest)) {
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
            console.error("error", collection, response);
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

    updatePageTitle: function (attributes) {
      var data = this.attributes ? _.clone(this.attributes) : {};
      attributes = attributes ? _.clone(attributes) : {};
      _.extend(data, attributes);

      var searchTerms = [
        "Events",
        data.nameSearch,
        data.location && data.location.toText() || null,
        data.tag && data.tag.join(", ") || null,
        data.tagAll && "all tags" || null,
        data.past && "past" || null,
        data.visibility || null
      ];
      var title = _.filter(searchTerms, function (term) {
        return term !== null;
      }).join(" | ");

      document.title = title + " | CAAT Mapping Application";
    },

    toQueryString: function (attributes) {
      var data = this.attributes ? _.clone(this.attributes) : {};
      attributes = attributes ? _.clone(attributes) : {};
      _.extend(data, attributes);

      m.log.debug("toQueryString", _.clone(this.attributes), _.clone(attributes), data);

      var model = this;

      var params = [];
      _.each(data, function (value, key) {
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

      var params = query.split("&");

      var data = {};
      _.each(params, function (param) {
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
      "submit": "submit",
      "change input[name='visibility']": "formChange",
      "change input[name='nameSearch']": "formChange",
      "change input[name='location']": "formChange",
      "change input[name='past']": "formChange",
      "change label > input[name='tag']": "formChange",
      "change input[name='tagAll']": "formChange"
    },
    limit: 26,  // Number of letters in the alphabet for map markers.
    limitEvent: 20,

    changeOffset: function () {
      var $input = this.$el.find("input[name='offset']");
      if ($input.val() !== this.model.get("offset")) {
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

      if ($input.prop("checked") !== pastVal) {
        $input.prop("checked", pastVal);
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
        _.each(value, function (tagName) {
          data.tagit.createTag(tagName);
        });
      }

    },

    changeTagAll: function () {
      var tagAll = this.model.get("tagAll");
      var tagAllVal = !!tagAll;
      var $input = this.$el.find("input[name='tagAll']");

      if ($input.prop("checked") !== tagAllVal) {
        $input.prop("checked", tagAllVal);
      }
    },

    changeVisibility: function () {
      var visibility = this.model.get("visibility") || "public";
      m.setVisibility(visibility);
      this.fetchEventtagList();
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

      this.mapView.encompass(location, 0.75);

      // In case the map has already moved, but not updated.
      google.maps.event.trigger(this.mapView, "idle");
    },

    initialize: function (options) {
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

      this.$results = options.$results;
      this.$paging = options.$paging;
      this.mapView = options.mapView;

      this.formAction = null;

      var data = this.serializeForm(options.$form);
      m.log.debug("set serializeForm", data);
      this.model.set(data);

      this.activeSearches = 0;

      var view = this;

      this.mapView.addMapListener("idle", function () {

        if (!view.mapView.mapReady) {
          // Set map from object.
          m.log.debug("set mapReady", data);
          view.mapView.mapReady = true;
          view.setMapLocation(view.model.get("location"));
          m.log.debug("Send map ready");
          view.send();
          return;
        }

        var mapGeobox = view.mapView.getGeobox();
        var modelGeobox = new window.Geobox(view.model.get("location"));
        var targetGeobox = view.mapView.targetGeobox;
        var resultGeobox = view.mapView.resultGeobox;
        view.mapView.targetGeobox = null;
        view.mapView.resultGeobox = null;

        if (mapGeobox && targetGeobox && mapGeobox.coordsDifference(resultGeobox) < 0.05) {
          // Map bounds match target map bounds. Do nothing.
          return;
        }

        if (!m.compareGeobox(mapGeobox, modelGeobox)) {
          // Coords are very close, name may have gone = small map drag.
          return;
        }

        data = {
          location: mapGeobox
        };
        m.log.debug("set mapIdle", data);
        view.model.set(data);
        m.log.debug("Send map idle");
        view.send();
      });

      this.render();

      this.eventtagCollection = new window.EventtagCollection();
      var eventtagListRequest = this.fetchEventtagList();
      if (eventtagListRequest) {
        eventtagListRequest.allways(this.render);
      }
    },

    render: function () {
      var view = this;

      m.templator.load([
        view.templateName,
        "visibility-search-input.html",
        "visibility-bar.html"
      ], function () {

        var html = m.templator.render(view.templateName, {
          currentUser: m.currentUser,
          eventSearch: view.model.toJSON()
        });

        var $el = $(html);
        $(view.$el).empty().append($el);

        view.setupTagInput();

        view.addThrobber();

      });

      return this;
    },

    fetchEventtagList: function () {
      if (!this.eventtagCollection) {
        return;
      }

      var visibility = this.model.get("visibility") || null;

      if (visibility === "private" || visibility === "pending") {
        visibility = "all";
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
      var limit = 20;

      var $input = view.$el.find("input[name='tag']");
      this.tagReady = false;
      $input.tagit({
        placeholderText: $input.attr("placeholder"),
        tagSource: function (search, showChoices) {
          showChoices(window.tagCollectionSearch(
            view.eventtagCollection, search, limit));
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
        }
      });
      this.tagReady = true;
    },

    submit: function (event) {
      event.preventDefault();
      var view = this;
      view.formAction = "submit";
      var timeout = setTimeout(function () {
        view.formAction = null;
      }, 25);
      m.log.debug("Send submit");
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
        data.past = false;
      }
      if (!data.hasOwnProperty("tagAll")) {
        data.tagAll = false;
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
            location: new window.Geobox(eventCollection.location)
          };
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
          var $span = $("<p>").addClass("results-hint").text(text);
          eventSearchView.$results.prepend($span);
        }
      }, cache);
    },

    renderPages: function (eventCollection, many) {
      var eventSearchView = this;
      var length = eventCollection.addressLength();
      var href = null;
      var query = null;
      var $pageLink = null;
      var $pageSpan = null;
      var pageClickHelper = null;
      var page;

      eventSearchView.$paging.empty();

      var countText = "addresses: " + length;
      if (eventCollection.eventLength) {
        countText = "events: " + eventCollection.eventLength + ", " + countText;
      }
      var $count = $("<span class='resultCount'>").text(countText);
      eventSearchView.$paging.prepend($count);

      var $pages = $("<ul class='pageList'>");

      if (many) {
        var in_ = 0;
        var out = eventCollection.eventLength;
        var showIn = eventSearchView.model.get("offset") || 0;
        var showOut = showIn + eventCollection.length;
        var limit = eventSearchView.limitEvent;
        var prev = null;
        var curr = null;
        var next = null;

        pageClickHelper = function (offset) {
          return function (e) {
            if (e.which !== 1 || e.metaKey || e.shiftKey) {
              return;
            }
            e.preventDefault();
            var data = {
              offset: offset
            };
            m.log.debug("set pageclick 1", data);
            eventSearchView.model.set(data);
            m.log.debug("Send pageclick 1");
            eventSearchView.send();
          };
        };

        if (showIn > in_) {
          prev = Math.max(in_, showIn - limit);
          query = eventSearchView.model.toQueryString({
            offset: prev
          });
          href = m.urlRoot + "event?" + query;
          $pageLink = $("<a>").attr("href", href).text("Previous");
          $pageLink.bind("click", pageClickHelper(prev));
          $pages.append($("<li>").append($pageLink));
        }
        curr = (showIn + 1) + "-" + (showOut);
        $pageSpan = $("<span>").text(curr);
        $pages.append($("<li>").append($pageSpan));
        if (showOut < out) {
          next = showIn + limit;
          query = eventSearchView.model.toQueryString({
            offset: next
          });
          href = m.urlRoot + "event?" + query;
          $pageLink = $("<a>").attr("href", href).text("Next");
          $pageLink.bind("click", pageClickHelper(next));
          $pages.append($("<li>").append($pageLink));
        }
        if (prev === null && next === null) {
          return;
        }
      } else {
        if (length <= eventSearchView.limit) {
          return;
        }

        pageClickHelper = function (page) {
          return function (e) {
            if (e.which !== 1 || e.metaKey || e.shiftKey) {
              return;
            }
            e.preventDefault();
            var data = {
              offset: page * eventSearchView.limit
            };
            m.log.debug("set pageclick 2", data);
            eventSearchView.model.set(data);
            m.log.debug("Send pageclick 2");
            eventSearchView.send();
          };
        };

        var text;
        var currentPage;
        for (page = 0; page < length / eventSearchView.limit; page += 1) {
          text = "page " + (page + 1);
          currentPage = eventSearchView.model.get("offset") || 0;
          if (page * eventSearchView.limit === currentPage) {
            $pageSpan = $("<span>").text(text);
            $pages.append($("<li>").append($pageSpan));
          } else {
            query = eventSearchView.model.toQueryString({
              offset: page * eventSearchView.limit
            });
            href = m.urlRoot + "event?" + query;
            $pageLink = $("<a>").attr("href", href).text(text);
            $pageLink.bind("click", pageClickHelper(page));
            $pages.append($("<li>").append($pageLink));
          }
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
      var src = m.urlRoot + "static/image/throbber.gif";
      this.$throbber = $('<img class="throbber" width="16px" height="16px" alt="Loading." src="' + src + '" style="display: none;">');
      this.$el.find(".actions").prepend(this.$throbber);
      return this.$throbber;
    },

    formChange: function (event) {
      var data = this.serializeForm();
      var view = this;
      m.log.debug("set formChange", data);
      this.model.set(data);
      var timeout = setTimeout(function () {
        if (view.formAction !== "submit") {
          m.log.debug("Send form change");
          view.send();
        }
      }, 25);
    },

    popstate: function () {
      var search = m.searchString();
      var data = {};
      data = _.extend(data, this.model.defaultParameters());
      data = _.extend(data, this.model.attributesFromQueryString(search));
      m.log.debug("set popstate", data);
      this.model.set(data);

      m.log.debug("Send popstate");
      this.send();
    }

  });

}(jQuery));

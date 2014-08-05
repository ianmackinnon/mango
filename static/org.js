"use strict";

/*global window, jQuery, _, Backbone, google, m */

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
        var href = m.urlRewrite(view.model.get("url"), m.parameters);
        window.document.location.href = href;
      };

      view.mapView.addDot(
        this.model.get("latitude"),
        this.model.get("longitude"),
        undefined,
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
        parameters: m.parameters
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
        var href = view.model.collection.org.get("url");
        window.document.location.href = href;
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
            mapView: view.mapView
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

      var $this = m.$template(this.templateName, {
        org: this.model.toJSON(),
        m: m,
        parameters: m.parameters,
        note: false
      });

      var insert = true;

      if (this.limit.offset < -this.limit.limit) {
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

      var $addressList = this.$el.find(".org_address_list");
      if ($addressList.length) {
        if (addressCollectionView.$el.find(".address-row").length) {
          this.$el.find(".org_address_list")
            .replaceWith(addressCollectionView.$el);
        }
      }

      return this;
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
      this.orgLength = resp.org_length;
      this.hint = resp.hint;
      return resp.org_list;
    }
  });

  window.OrgCollectionView = Backbone.View.extend({
    tagName: "div",
    className: "column",

    initialize: function () {
      var view = this;
      var limit = null;

      view.mapView = this.options.mapView;
      view.offset = this.options.offset;
      view.limit = this.options.limit;

      this._modelViews = [];
      this._addressModelViews = [];
      view.many = null;
      this.mapView.cluster(this.collection.markerList && this.collection.markerList.length > 1000 && m.parameters.visibility == "all");
      if (this.collection.markerList) {
        view.many = true;
        _.each(this.collection.markerList, function (model) {
          view._modelViews.push(new MarkerViewDot({
            model: new Marker(model),
            mapView: view.mapView
          }));
        });
        limit = {
          offset: 0,  // Server is handling offsets
          limit: view.limitOrg
        };
        this.collection.each(function (model) {
          view._modelViews.push(new window.OrgViewBox({
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
              mapView: view.mapView
            }));
          });
        });
      } else {
        view.many = false;
        limit = {
          offset: view.offset,  // Browser is handling offsets
          limit: view.limit
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

  window.OrgSearch = Backbone.Model.extend({
    // constructor, multiConstructor, compare, default, toString
    expectedParameters: {
      "nameSearch": [null, false, m.compareLowercase, "", null],
      "location": [geoboxFactory, false, m.compareGeobox, m.ukGeobox, geoboxToString],
      "offset": [parseInt, false, null, 0, null],
      "tag": [m.argumentMulti, m.argumentMulti, m.compareUnsortedList, [], m.multiToString],
      "tagAll": [m.argumentCheckbox, false, null, 0, m.checkboxToString],
      "visibility": [m.argumentVisibility, false, null, "public", null]
    },

    defaultParameters: function () {
      var defaults = {};
      _.each(this.expectedParameters, function (value, key) {
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

      var url = m.urlRoot + "organisation?" + queryString;
      m.log.debug("pushState", queryString);
      if (window.History.enabled) {
        window.History.pushState(null, null, url);
      }
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

      var orgCollection = new window.OrgCollection();

      if (model.request) {
        model.request.abort();
      }
      model.request = orgCollection.fetch({
        data: sendData,
        success: function (collection, response) {
          // Only add successful page loads to history.
          model.testStateChange(modelData);

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

    updatePageTitle: function (attributes) {
      var data = this.attributes ? _.clone(this.attributes) : {};
      attributes = attributes ? _.clone(attributes) : {};
      _.extend(data, attributes);

      var searchTerms = [
        "Companies",
        data.nameSearch,
        data.location && data.location.toText() || null,
        data.tag && data.tag.join(", ") || null,
        data.tagAll && "all tags" || null,
        data.visibility || null
      ];
      var title = _.filter(searchTerms, function (term) {
        return term !== null;
      }).join(" | ");

      document.title = title + " | CAAT Mapping Application"
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

  window.OrgSearchView = Backbone.View.extend({
    tagName: "form",
    id: "org-search",
    templateName: "org-search.html",
    events: {
      'submit': 'submit',
      'change input[name="visibility"]': 'formChange',
      'change input[name="nameSearch"]': 'formChange',
      'change input[name="location"]': 'formChange',
      'change label > input[name="tag"]': 'formChange',
      'change input[name="tagAll"]': 'formChange'
    },
    limit: 26,  // Number of letters in the alphabet for map markers.
    limitOrg: 20,

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

      if ($input.prop('checked') !== tagAllVal) {
        $input.prop('checked', tagAllVal);
      }
    },

    changeVisibility: function () {
      var visibility = this.model.get("visibility") || "public";
      m.setVisibility(visibility);
      this.fetchOrgtagList();
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

    initialize: function () {
      _.bindAll(
        this,
        "render",
        "changeNameSearch",
        "changeLocation",
        "changeTag",
        "changeTagAll",
        "changeOffset",
        "changeVisibility",
        "onModelRequest",
        "popstate"
      );
      this.model.bind("change:nameSearch", this.changeNameSearch);
      this.model.bind("change:location", this.changeLocation);
      this.model.bind("change:tag", this.changeTag);
      this.model.bind("change:tagAll", this.changeTagAll);
      this.model.bind("change:offset", this.changeOffset);
      this.model.bind("change:visibility", this.changeVisibility);
      this.model.bind("request", this.onModelRequest);

      this.$results = this.options.$results;
      this.$paging = this.options.$paging;
      this.$social = this.options.$social;
      this.mapView = this.options.mapView;

      this.formAction = null;

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

        var data = {
          location: mapGeobox
        };
        m.log.debug("set mapIdle", data);
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
      var hint = null;
      if (this.model.lastResult && this.model.lastResult.hint) {
        hint = this.model.lastResult.hint
      }
      $(this.el).html(m.template(this.templateName, {
        currentUser: m.currentUser,
        orgSearch: this.model.toJSON(),
        hint: hint
      }));
      this.setupTagInput();

      var $inputTag = $("input[name='tag']");
      $inputTag = $inputTag.next().find("input")
      $inputTag.width(400);

      this.addThrobber();
      return this;
    },

    fetchOrgtagList: function () {
      if (!this.orgtagCollection) {
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
      var limit = 20;

      var $input = view.$el.find("input[name='tag']");
      this.tagReady = false;
      $input.tagit({
        placeholderText: $input.attr("placeholder"),
        tagSource: function (search, showChoices) {
          showChoices(window.tagCollectionSearch(
            view.orgtagCollection, search, limit));
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
      if (!data.hasOwnProperty("tagAll")) {
        data.tagAll = false;
      }
      return data;
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
            location: new window.Geobox(orgCollection.location)
          };
          m.log.debug("set receive", data);
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
        orgSearchView.renderSocial(orgCollection);
        orgSearchView.renderHints(orgCollection);
        orgSearchView.$results = rendered.$el;

        if (orgCollectionView.many) {
          var text = "Zoom in or refine search to see results in detail.";
          var $span = $("<p>").addClass("results-hint").text(text);
          orgSearchView.$results.prepend($span);
        }
      }, cache);
    },

    renderSocial: function (orgCollection) {
      var socialTags = {
        "farnborough-2014": {
          role: "Farnborough arms exhibitor",  // 's' appended for plurals
          hashtags: ["FIA2014"]
        }
      };

      var orgSearchView = this;
      var $paragraph = orgSearchView.$social.find("p");
      var $anchor = orgSearchView.$social.find("a");
      orgSearchView.$social.hide();
      $paragraph.empty();

      var tags = orgSearchView.model.get("tag");
      if (!tags) {
        return;
      }

      var number = Math.max(orgCollection.length, orgCollection.orgLength);
      if (!number) {
        return;
      }

      var socialTag = _.first(_.intersection(_.keys(socialTags), tags));
      if (!socialTag) {
        return;
      }
      socialTag = socialTags[socialTag];

      var country = false;
      if (orgSearchView.model.get("tagAll")) {
        _.each(tags, function (tag) {
          var match = tag.match(/^military-export-applicant-to-([\w\-]*)$/);
          if (match) {
            country = match[1];
          }
        });
      }
      var location = false;
      var locationType = orgCollection.location && orgCollection.location.type;
      if (locationType) {
        if (locationType === "postal_code") {
          location = "in my area";
        }
        if (locationType === "political") {
          location = "near " + orgCollection.location.longName;
        }
      }
      if (!!location + !!country !== 1) {
        // Either location or country, but not both.
        return;
      }
      var text = "";
      if (country) { 
        if (number === 1) {
          text = number + " " + socialTag.role + " applied to export military items to " + country + ".";
        } else {
          text = number + " " + socialTag.role + "s applied to export military items to " + country + ".";
        }
      } else {
        if (number === 1) {
          text = number + " " + socialTag.role + " has an address " + location + ".";
        } else {
          text = number + " " + socialTag.role + "s have addresses " + location + ".";
        }
      }
      var tweetData = {
        url: window.location.href,
        hashtags: socialTag.hashtags,
        text: text
      };
      var twitterUrl = "https://twitter.com/intent/tweet?" + $.param(tweetData);
      $anchor.attr({
        href: twitterUrl,
        target: "_blank"
      });
      $paragraph.append($("<a>").append('"' + text + '"'));
      orgSearchView.$social.show();
    },

    renderHints: function (orgCollection) {

      if (orgCollection.hint) {
        if (orgCollection.hint.name) {
          var $inputName = $("input[name='nameSearch']");
          $inputName.attr("placeholder", "Eg. " + orgCollection.hint.name.join(", "));
        }
        if (orgCollection.hint.tag) {
          var $inputTag = $("input[name='tag']");
          $inputTag.attr("placeholder", "Eg. " + orgCollection.hint.tag.join(", "));
          $inputTag = $inputTag.next().find("input")
          $inputTag.attr("placeholder", "Eg. " + orgCollection.hint.tag.join(", "));
          $inputTag.width(400);
        }
      }
    },


    renderPages: function (orgCollection, many) {
      var orgSearchView = this;
      var length = orgCollection.addressLength();
      var href = null;
      var query = null;
      var $pageLink = null;
      var $pageSpan = null;
      var pageClickHelper = null;
      var page;

      orgSearchView.$paging.empty();

      var countText = "addresses: " + length;
      if (orgCollection.orgLength) {
        countText = "companies: " + orgCollection.orgLength + ", " + countText;
      }
      var $count = $("<span class='resultCount'>").text(countText);
      orgSearchView.$paging.prepend($count);

      var $pages = $("<ul class='pageList'>");

      if (many) {
        var in_ = 0;
        var out = orgCollection.orgLength;
        var showIn = orgSearchView.model.get("offset") || 0;
        var showOut = showIn + orgCollection.length;
        var limit = orgSearchView.limitOrg;
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
            m.log.debug("set pageclick", data);
            orgSearchView.model.set(data);
            orgSearchView.send();
          };
        };

        if (showIn > in_) {
          prev = Math.max(in_, showIn - limit);
          query = orgSearchView.model.toQueryString({
            offset: prev
          });
          href = m.urlRoot + "organisation?" + query;
          $pageLink = $("<a>").attr("href", href).text("Previous");
          $pageLink.bind("click", pageClickHelper(prev));
          $pages.append($("<li>").append($pageLink));
        }
        curr = (showIn + 1) + "-" + (showOut);
        $pageSpan = $("<span>").text(curr);
        $pages.append($("<li>").append($pageSpan));
        if (showOut < out) {
          next = showIn + limit;
          query = orgSearchView.model.toQueryString({
            offset: next
          });
          href = m.urlRoot + "organisation?" + query;
          $pageLink = $("<a>").attr("href", href).text("Next");
          $pageLink.bind("click", pageClickHelper(next));
          $pages.append($("<li>").append($pageLink));
        }
        if (prev === null && next === null) {
          return;
        }
      } else {
        if (length <= orgSearchView.limit) {
          return;
        }

        pageClickHelper = function (page) {
          return function (e) {
            if (e.which !== 1 || e.metaKey || e.shiftKey) {
              return;
            }
            e.preventDefault();
            var data = {
              offset: page * orgSearchView.limit
            };
            m.log.debug("set pageclick", data);
            orgSearchView.model.set(data);
            orgSearchView.send();
          };
        };

        for (page = 0; page < length / orgSearchView.limit; page += 1) {
          var text = "page " + (page + 1);
          var currentPage = orgSearchView.model.get("offset") || 0;
          if (page * orgSearchView.limit === currentPage) {
            $pageSpan = $("<span>").text(text);
            $pages.append($("<li>").append($pageSpan));
          } else {
            query = orgSearchView.model.toQueryString({
              offset: page * orgSearchView.limit
            });
            href = m.urlRoot + "organisation?" + query;
            $pageLink = $("<a>").attr("href", href).text(text);
            $pageLink.bind("click", pageClickHelper(page));
            $pages.append($("<li>").append($pageLink));
          }
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
          view.send();
        };
      }, 25);
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

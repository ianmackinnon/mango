"use strict";

/*global window, $, _, Backbone, markdown, google */

var m = {

  parameters: null,

  debug: false,

  log: {
    debug: function () {
      if (!m.debug) {
        return;
      }
      // Translation for Internet Explorer of
      //   console.log.apply(console, arguments);
      Function.prototype.apply.call(console.log, console, arguments);
    }
  },

  ukGeobox: new window.Geobox({
    "south":49.829,
    "north":58.988,
    "west":-12.304,
    "east":3.912
  }),

  searchString: function () {
    var State = History.getState();
    var search = "";
    var index = State.url.indexOf("?");
    if (index >= 0) {
      search = State.url.substr(index);
    }
    return search;
  },

  _templateCache: {},

  template: function (name, data) {
    var url = m.urlRoot + "static/template/" + name;

    if (!(m._templateCache.hasOwnProperty(name))) {
      m._templateCache[name] = false;
    }
    if (m._templateCache[name] === false) {
      m._templateCache[name] = true;
      $.ajax({
        url: url,
        async: false,
        success: function (response) {
          m._templateCache[name] = response;
        },
        error: function (jqXHR, textStatus, errorThrown) {
          m.ajaxError(jqXHR, textStatus, errorThrown);
          m._templateCache[name] = null;
        }
      });
    }
    if (m._templateCache[name] === true) {
      var interval = setInterval(function () {
        if (m._templateCache[name] !== true) {
          clearInterval(interval);
        }
      }, 100);
    }
    return _.template(m._templateCache[name], data);
  },

  $template: function (name, data) {
    var html = m.template(name, data);
    html = html.replace(/[\r\n]+/gm,"")
    var $el = $("<div>").html(html);
    return $el;
  },

  currentUser: null,

  "filter": {
    "h": function (text) {
      return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&apos;');
    },

    "newline": function (text) {
      return String(text)
        .replace(/\n/g, '<br />');
    },

    "newline_comma": function (text) {
      return String(text)
        .replace(/\n/g, ', ');
    },

    "nbsp": function (text) {
      return String(text)
        .replace(/[\s]+/g, '&nbsp;')
        .replace(/-/g, '&#8209;');
    },

    "markdown": function (text) {
      return !!text ? markdown.toHTML(text) : '';
    },

    "markdownPlain": function (text) {
      return $(m.filter.markdown(text)).text();
    },

    pageTime: function (time) {
      return time;
    },
    pageDate: function (date) {
      return $.datepicker.formatDate('D dd M yy', new Date(date));
    },

  },

  "filter_object_true": function (arr) {
    var arr2 = {};
    $.each(arr, function (key, value) {
      if (!!value) {
        arr2[key] = value;
      }
    });
    return arr2;
  },

  "process": {
    tagPacket: function (tagListId, tagPacket, tagListName, lengthName, urlName, options) {
      var showEntity = options && options.showEntity;
      var showNotes = options && options.showNotes;
      var showPath = options && options.showPath;
      var excludeTagId = options && options.excludeTagId;

      var tagList = $(tagListId);

      if (_.isNull(showPath) || _.isUndefined(showPath)) {
        var showPath = tagPacket.path;
      }

      tagList.empty();

      $.each(tagPacket[tagListName], function(index, value) {
        if (value.id == excludeTagId) {
          return;
        }
	var $tagLi = m.$template("tag-li.html", {
	  tag: value,
	  entity: showEntity,
	  note: showNotes,
          path: showPath,
          parameters: m.parameters,
          entity_len: lengthName, 
          entity_list_url: urlName
	});
	tagList.append($tagLi);
	tagList.append(" ");
      });
    },

    "orgtag_packet": function(tag_list_id, orgtag_packet, options) {
      return m.process.tagPacket(tag_list_id, orgtag_packet, "orgtag_list", "org_len", "org_list_url", options);
    },

    "eventtag_packet": function(tag_list_id, eventtag_packet, options) {
      return m.process.tagPacket(tag_list_id, eventtag_packet, "eventtag_list", "event_len", "event_list_url", options);
    }
  },

  "geo": {
    "in_": function (latitude, longitude, geobox) {
      if (geobox === null) {
        return true;
      }
      if (latitude > geobox.latmax || latitude < geobox.latmin) {
        return false;
      }
      if (longitude > geobox.lonmax || longitude < geobox.lonmin) {
        return false;
      }
      return true;
    }
  },

  "timers": {},
  "last_values": {},

  "on_change": function (input, name, callback, ms) {
    m.last_values[name] = m.values(input);
    m.timers[name] = null;
    var change = function () {
      var value = m.values(input);
      if (value === m.last_values[name]) {
        return;
      }
      m.last_values[name] = value;
      callback(value);
    };
    var delay = function () {
      clearTimeout(m.timers[name]);
      m.timers[name] = setTimeout(change, ms);
    };

    input.keyup(delay);
    input.click(delay);
    input.change(delay);
    change();
  },

  "url_rewrite": function (path, parameters) {
    if (!path) {
      console.log("No path supplied to url_rewrite!");
    }
    var url = path;
    if (url.indexOf("/") === 0) {
      url = m.urlRoot + url.substring(1);
    }
    var query = null;
    $.each(parameters, function (key, value) {
      if (!value) {
        return;
      }
      if (query === null) {
        query = "";
      } else {
        query += "&";
      }
      query += encodeURIComponent(key) + "=" + encodeURIComponent(value);
    });
    if (!!query) {
      url += "?" + query;
    }
    return url;
  },

  "values": function (input) {
    if (input.filter("[type='checkbox']").length) {
      var multi = input.filter(":checked");
      if (multi.length) {
        var values = [];
        multi.each(function (index, value) {
          values.push($(value).val());
        });
        return values;
      }
      return null;
    }
    return input.val() || null;
  },

  initMap: function () {
    var mapView = new window.MapView();
    $("#mango-map-box").replaceWith(mapView.$el);
    return mapView;
  },

  initHome: function (mapView) {
    $("#mango-map-box").append(m.template("home-map-legend.html"));

    // Z-index fails on Google Maps markers, event with optimization
    // disabled. Rendering orgs after events seems to make them render
    // below.

    var eventCollection = new window.EventCollection();
    var eventCollectionView = new window.EventCollectionView({
      collection: eventCollection,
      mapView: mapView
    });
    eventCollection.fetch({
      data: {
        view: "marker"
      },
      success: function(collection, response) {
        eventCollectionView.initialize();
        eventCollectionView.render(true);
        var orgCollection = new window.OrgCollection();
        var orgCollectionView = new window.OrgCollectionView({
          collection: orgCollection,
          mapView: mapView
        });
        orgCollection.fetch({
          data: {
            view: "marker"
          },
          success: function(collection, response) {
            orgCollectionView.initialize();
            orgCollectionView.render(true);
          },
          error: function (collection, response) {
            if (response.statusText !== "abort") {
              console.log("error", collection, response);
            }
          }
        });
      },
      error: function (collection, response) {
        if (response.statusText !== "abort") {
          console.log("error", collection, response);
        }
      }
    });
  },

  initOrg: function (mapView) {
    $("div.address-row div.pin").each(function(i) {
      var $pin = $(this);
      var $circle = mapView.addMarker(
        $pin.attr("latitude"),
        $pin.attr("longitude")
      );
      $pin.append($circle);
    });
    mapView.fit();
  },

  initOrgSearch: function (mapView) {
    var orgSearch = new window.OrgSearch();
    var orgSearchView = new window.OrgSearchView({
      model: orgSearch,
      $form: $("#org-search"),
      $results: $("#org_list").find(".column"),
      $paging: $("#org_list").find(".counts"),
      mapView: mapView
    });
    $("#org-search").replaceWith(orgSearchView.$el);
    orgSearchView.send();
    
    if (window.History.enabled) {
      History.Adapter.bind(window, "statechange", orgSearchView.popstate);
    }
    
    window.orgSearch = orgSearch;

    return orgSearch;
  },

  initEvent: function (mapView) {
    $("div.address-row div.pin").each(function(i) {
      var $pin = $(this);
      var $circle = mapView.addMarker(
        $pin.attr("latitude"),
        $pin.attr("longitude")
      );
      $pin.append($circle);
    });
    mapView.fit();

    $("input[name='start_date']").datepicker({
      dateFormat: "yy-mm-dd",
      numberOfMonths: 2
    });
    $("input[name='end_date']").datepicker({
      dateFormat: "yy-mm-dd",
      numberOfMonths: 2
    });
    $("input[name='start_time']").timepicker({
      defaultTime: ""
    });
    $("input[name='end_time']").timepicker({
      defaultTime: ""
    });

    var title = $("<h3>").text("Description Preview");
    var preview = $("<div>").addClass("description markdown-preview");
    $("#mango-map-box").append(title);
    $("#mango-map-box").append(preview);
    
    m.event_markdown();

  },

  initEventSearch: function (mapView) {
    var eventSearch = new window.EventSearch();
    var eventSearchView = new window.EventSearchView({
      model: eventSearch,
      $form: $("#event-search"),
      $results: $("#event_list").find(".column"),
      $paging: $("#event_list").find(".counts"),
      mapView: mapView
    });
    $("#event-search").replaceWith(eventSearchView.$el);
    eventSearchView.send();
    
    if (window.History.enabled) {
      History.Adapter.bind(window, "statechange", eventSearchView.popstate);
    }
    
    window.eventSearch = eventSearch;

    return eventSearch;
  },

  ajaxError: function (jqXHR, textStatus, errorThrown) {
    if (textStatus === "abort") {
      return;
    }
    console.log("error", jqXHR, textStatus, errorThrown);
  },

  initOrgtagSearch: function (id, field, options) {
    var form = $("#" + id);
    var search = m.get_field(form, field);
    var $path = form.find("input[name='path']");
    var pathValue = function () {
      return $path.is(":checked") && 1 || null;
    };
    var visibility = form.find("input[name='visibility']");
    var throbber = $("<img>").attr({
      "src": m.urlRoot + "static/image/throbber.gif",
      "class": "throbber"
    }).hide();
    form.find("input[type='submit']").before(throbber);
    var xhr = null;

    var change = function (value) {
      if (xhr && xhr.readyState !== 4) {
        xhr.abort();
      }
      var data = {
        search: search.input.val(),
        path: pathValue()
      };
      if (visibility.length) {
        data.visibility = visibility.val();
      }
      xhr = $.ajax(m.urlRoot + "organisation-tag", {
        "dataType": "json",
        "data": data,
        "success": function (data, textStatus, jqXHR) {
          m.process.orgtag_packet("#tag_list", data, options);
        },
        "error": m.ajaxError,
        "complete": function (jqXHR, textStatus) {
        throbber.hide();
        }
      });
      throbber.show();
    };

    m.on_change(search.input, id + "_" + field, change, 500);
    $path.change(change);
    visibility.change(change);
  },

  "init_eventtag_search": function (id, field, options) {
    var form = $("#" + id);
    var search = m.get_field(form, field);
    var $path = form.find("input[name='path']");
    var pathValue = function () {
      return $path.is(":checked") && 1 || null;
    };
    var visibility = form.find("input[name='visibility']");
    var throbber = $("<img>").attr({
      "src": m.urlRoot + "static/image/throbber.gif",
      "class": "throbber"
    }).hide();
    form.find("input[type='submit']").before(throbber);
    var xhr = null;

    var change = function (value) {

      if (xhr && xhr.readyState !== 4) {
        xhr.abort();
      }
      var data = {
        search: search.input.val(),
        path: pathValue()
      };
      if (visibility.length) {
        data.visibility = visibility.val();
      }
      xhr = $.ajax(m.urlRoot + "event-tag", {
        "dataType": "json",
        "data": data,
        "success": function (data, textStatus, jqXHR) {
          m.process.eventtag_packet("#tag_list", data, options);
        },
        "error": m.ajaxError,
        "complete": function (jqXHR, textStatus) {
          throbber.hide();
        }
      });
      throbber.show();
    };

    m.on_change(search.input, id + "_" + field, change, 500);
    $path.change(change);
    visibility.change(change);
  },

  "get_field": function (form, name) {
    var label = form.find("label[name='" + name + "']");
    var input = label.find("input, textarea").filter("[name='" + name + "']");
    if ((!label.length) || (!input.length)) {
      return null;
    }
    return {
      "label": label,
      "input": input
    };
  },

  initAddressForm: function (mapView) {
    var form = $("#address-form").find("form");
    if (!form.length) {
      var $span = $("span[latitude]");
      if (!$span.length) {
        return;
      }
      mapView.addMarker(
        $span.attr("latitude"),
        $span.attr("longitude")
      );
      return;
    }

    var search = $("<input>").attr({
      "type": "button",
      "value": "Find address on map"
    });
    var submit = form.find("input[type='submit']");
    form.find("label[name='source']").before(search);
    var postal = m.get_field(form, "postal");
    var lookup = m.get_field(form, "lookup");
    var source = m.get_field(form, "source");

    var manual_latitude = form.find("[name='manual_latitude']");
    var manual_longitude = form.find("[name='manual_longitude']");
    var latitude = form.find("[name='latitude']");
    var longitude = form.find("[name='longitude']");

    var validate = function () {
      var x = form.find("[status='bad']");
      if (x.length) {
        submit.attr('disabled', 'disabled');
      } else {
        submit.removeAttr('disabled');
      }

      if (postal.input.val().length || lookup.input.val().length) {
        search.removeAttr('disabled');
      } else {
        search.attr('disabled', 'disabled');
      }
    };

    var manual_control = $("<div class='caption'>");
    var manual_control_hint = $("<span>").text("The address could not be found automatically. You may wish to check the address for accuracy, consider adding a machine-friendly 'Lookup' address, or click the map to set the position manually.").hide();
    var manual_control_span1 = $("<span>").text("Click on the map or drag a marker to set position manually.").hide();
    var manual_control_span2 = $("<span>").text("Map position has been set manually.").hide();
    var manual_control_button = $("<input type='button' id='manual_position_clear' value='Remove'>").hide();
    var manual_control_span3 = $("<p>").text("Map position has not yet been saved.").hide();
    $("#mango-map-box").append(manual_control);
    manual_control.append(manual_control_hint);
    manual_control.append(manual_control_span1);
    manual_control.append(manual_control_span2);
    manual_control.append(manual_control_button);
    manual_control.append(manual_control_span3);

    var set_manual_position = function (lat, lng) {
      manual_latitude.val(lat);
      manual_longitude.val(lng);
      manual_control_hint.hide();
      manual_control_span1.hide();
      manual_control_span2.show();
      manual_control_button.show();
      manual_control_span3.show();
    };

    var clear_manual_position = function () {
      manual_latitude.val(null);
      manual_longitude.val(null);
      manual_control_hint.hide();
      manual_control_span1.show();
      manual_control_span2.hide();
      manual_control_button.hide();
      manual_control_span3.hide();
    };

    manual_control_button.click(function () {
      updateMarker();
      clear_manual_position();
      address_search();
    });

    var updateMarker = mapView.clickDraggableMarker(set_manual_position);

    var address_search = function () {
      $.ajax(m.urlRoot + "address/lookup", {
        "dataType": "json",
        "data": {
          "postal": postal.input.val(),
          "lookup": lookup.input.val(),
        },
        "success": function (data, textStatus, jqXHR) {
          if (!data.latitude) {
            clear_manual_position();
            manual_control_hint.show();
            manual_control_span1.hide();
            return;
          }
          updateMarker(data.latitude, data.longitude);
          clear_manual_position();
          mapView.fit();
        },
        "error": m.ajaxError
      });
    };

    search.click(address_search);

    var id = "address-form";
    m.on_change(postal.input, id + "_postal", function (value) {
      postal.label.attr("status", !!value ? "good" : "bad");
      validate();
    }, 500);
    m.on_change(source.input, id + "_source", function (value) {
      source.label.attr("status", !!value ? "good" : "bad");
      validate();
    }, 500);
    m.on_change(lookup.input, id + "_lookup", function (value) {
      lookup.label.attr("status", !!value ? "good" : null);
      validate();
    }, 500);

    validate();

    if (latitude.length) {
      if (latitude.val().length && longitude.val().length) {
        updateMarker(latitude.val(), longitude.val());
        mapView.fit();
      }
    }
    if (manual_latitude.val().length && manual_longitude.val().length) {
      manual_control_hint.hide();
      manual_control_span1.hide();
      manual_control_span2.show();
      manual_control_button.show();
      manual_control_span3.hide();
    }

    $("#address-form textarea[name='postal']").focus();
  },

  initTagForm: function () {
    var form = $("#tag-form");
    var inputName = form.find("input[name='name']");
    var inputPath = form.find("select[name='path']");
    inputName.focus().val(inputName.val());  // Move cursor to end.
    inputPath.after($("<span>").text("Select to prepend path to name."));
    inputPath.change(function() {
      if (!inputPath.val()) {
        return;
      }
      inputName.focus().val(inputPath.val() + " | " + inputName.val());
      inputPath.val(null);
    });
  },

  "text_children": function (el) {
    // http://stackoverflow.com/a/4399718/201665
    return $(el).find(":not(iframe)").andSelf().contents().filter(function () {
      return this.nodeType === 3;
    });
  },

  "has_link_parent": function (node) {
    if (!$(node).parent().length) {
      return false;
    }
    if (!$(node).parent()[0].tagName) {
      return false;
    }
    if ($(node).parent()[0].tagName.toLowerCase() === "a") {
      return true;
    }
    return m.has_link_parent($(node).parent()[0]);
  },

  "convert_inline_links": function (el) {
    m.text_children(el).replaceWith(function () {
      if (m.has_link_parent(this)) {
        return $("<span>" + this.textContent + "</span>");
      }
      var html = this.textContent.replace(
        /(?:(https?:\/\/)|(www\.))([\S]+\.[^\s<>\"\']+)/g,
        "<a href='http://$2$3'>$1$2$3</a>"
      );
      html = "<span>" + html + "</span>";
      var node = $(html);
      return node;
    });

  },

  "note_markdown": function () {
    var form = $("#note-form");
    var text = m.get_field(form, "text");
    var source = m.get_field(form, "source");
    m.on_change(text.input, "note-form" + "_" + "text", function (value) {
      text.label.attr("status", !!value ? "good" : "bad");
      $("#note-preview .note-text").html(m.filter.markdown(value));
      m.convert_inline_links($("#note-preview .note-text"));
    }, 500);
    m.on_change(source.input, "note-form" + "_" + "source", function (value) {
      source.label.attr("status", !!value ? "good" : "bad");
      $("#note-preview .note-source").html(m.filter.markdown(value));
      m.convert_inline_links($("#note-preview .note-source"));
    }, 500);
  },

  "event_markdown": function () {
    var form = $("#event-form");
    var text = m.get_field(form, "description");
    var preview = $(".description.markdown-preview");
    var on_change = function (value) {
      preview.html(m.filter.markdown(value));
      m.convert_inline_links($(".description.markdown-preview"));
    };
    m.on_change(text.input, "event-form" + "_" + "text", on_change, 500);
    on_change(text.input.val());
  },

  argumentCheckbox: function(value) {
    if (value === true || value === false) {
      return value;
    }
    return !!parseInt(value);
  },

  checkboxToString: function(value) {
    value = m.argumentCheckbox(value);
    return value && "1" || null;
  },

  argumentMulti: function(valueNew, valueOld) {
    var collection = valueOld ? _.clone(valueOld) : [];
    if (!valueNew) {
      return collection;
    }
    var values;
    if (_.isArray(valueNew)) {
      values = valueNew;
    } else {
      values = [];
      _.each(valueNew.split(","), function (value) {
        values.push(value.replace(/^\s+|\s+$/g, ""));
      });
    }
    return _.union(collection, values);
  },

  argumentVisibility: function(value) {
    if (_.contains(["public", "private", "pending", "all"], value)) {
      return value;
    }
    return null
  },

  compareUnsortedList: function(a, b) {
    if (!a && !b) {
      return false;
    }
    if (!a || !b) {
      return true;
    }
    var difference = _.union(_.difference(a, b), _.difference(b, a));
    return difference.length > 0;
  },

  compareLowercase: function(a, b) {
    if (!a && !b) {
      return false;
    }
    if (!a || !b) {
      return true;
    }
    return a.toLowerCase() != b.toLowerCase();
  },

  compareGeobox: function(a, b) {
    // a = old, b = new
    if (!a && !b) {
      return false;
    }
    if (!a || !b) {
      return true;
    }
    // if new has the same name but lacks coords don't remove the coords
    if (!!a.name && a.name === b.name && a.hasCoords() && !b.hasCoords()) {
      return false;
    }
    var difference = a.difference(b);
    if (difference === true || difference === false) {
      return difference;
    }
    return difference > 0.05;
  },

  multiToString: function(multi) {
    return multi.join(", ");
  },

  "set_visibility": function (value) {
    $("a").each(function () {
      var $el = $(this);
      if ($el.hasClass("visibility-button")) {
        return;
      }
      if (!$el.attr("href")) {
        return;
      }
      if ($el.attr("href").indexOf(m.urlRoot) !== 0) {
        return;
      }
      var href = $el.attr("href");
      var visibility = "visibility=" + value;
      if ($el.attr("href").toLowerCase().indexOf("visibility=") >= 0) {
        href = href.replace(/visibility=[\w\-]*/gi, visibility);
      } else {
        if ($el.attr("href").indexOf("?") >= 0) {
          href = href + "&" + visibility;
        } else {
          href = href + "?" + visibility;
        }
      }
      $el.attr("href", href);
    });
    $("input[name='visibility']").val(value);
    $("input[name='visibility']").change();
    $("#visibility-public").removeClass("selected");
    $("#visibility-private").removeClass("selected");
    $("#visibility-pending").removeClass("selected");
    $("#visibility-all").removeClass("selected");
    $("#visibility-" + value).addClass("selected");
    m.parameters.visibility = value;
  },

  visibility: function () {
    $("#visibility-public").click(function (e) {
      if (e.which !== 1 || e.metaKey || e.shiftKey) {
        return;
      }
      e.preventDefault();
      m.set_visibility("public");
    });
    $("#visibility-private").click(function (e) {
      if (e.which !== 1 || e.metaKey || e.shiftKey) {
        return;
      }
      e.preventDefault();
      m.set_visibility("private");
    });
    $("#visibility-pending").click(function (e) {
      if (e.which !== 1 || e.metaKey || e.shiftKey) {
        return;
      }
      e.preventDefault();
      m.set_visibility("pending");
    });
    $("#visibility-all").click(function (e) {
      if (e.which !== 1 || e.metaKey || e.shiftKey) {
        return;
      }
      e.preventDefault();
      m.set_visibility("all");
    });
  },

  "route": [
    [/^\/$/, function () {
      var mapView = m.initMap();
      m.initHome(mapView);
      m.visibility();
    }],

    [/^\/note\/new$/, function () {
      m.note_markdown();
    }],
    [/^\/note\/([1-9][0-9]*)$/, function (noteIdString) {
      m.note_markdown();
    }],

    [/^\/organisation$/, function () {
      var mapView = m.initMap();
      m.initOrgSearch(mapView);
      m.visibility();
    }],
    [/^\/event$/, function () {
      var mapView = m.initMap();
      m.initEventSearch(mapView);
      m.visibility();
    }],
    [/^\/task\/address$/, function () {
      var mapView = m.initMap();
      m.initOrgSearch(mapView);
      m.visibility();
    }],

    [/^\/organisation\/([1-9][0-9]*)$/, function (orgIdString) {
      var mapView = m.initMap();
      m.initOrg(mapView);
    }],
    [/^\/organisation\/new$/, function () {
      var mapView = m.initMap();
      m.initOrg(mapView);
    }],
    [/^\/organisation\/([1-9][0-9]*)\/address$/, function (orgIdString) {
      var mapView = m.initMap();
      m.initAddressForm(mapView);
    }],
    [/^\/organisation\/([1-9][0-9]*)\/note$/, function (orgIdString) {
      m.note_markdown();
    }],
    [/^\/organisation\/([1-9][0-9]*)\/tag$/, function (orgIdString) {
      m.visibility();
    }],
    [/^\/event\/([1-9][0-9]*)$/, function (eventIdString) {
      var mapView = m.initMap();
      m.initEvent(mapView);
    }],
    [/^\/event\/new$/, function () {
      var mapView = m.initMap();
      m.initEvent(mapView);
    }],
    [/^\/event\/([1-9][0-9]*)\/address$/, function (eventIdString) {
      var mapView = m.initMap();
      m.initAddressForm(mapView);
    }],
    [/^\/event\/([1-9][0-9]*)\/note$/, function (eventIdString) {
      m.note_markdown();
    }],

    [/^\/address\/([1-9][0-9]*)$/, function (addressIdString) {
      var mapView = m.initMap();
      m.initAddressForm(mapView);
    }],
    [/^\/address\/([1-9][0-9]*)\/note$/, function (addressIdString) {
      m.note_markdown();
    }],

    [/^\/organisation-tag$/, function () {
      m.initOrgtagSearch("tag-search", "search", {
        showEntity: true,
        showNotes: true
      });
      $("#orgtag-search input[name='search']").focus();
      m.visibility();
    }],
    [/^\/organisation-tag\/([1-9][0-9]*)$/, function (orgtagIdString) {
      m.initTagForm();
      m.initOrgtagSearch("tag-form", "name", {
        showPath: true,
        excludeTagId: parseInt(orgtagIdString)
      });
    }],
    [/^\/organisation-tag\/new$/, function () {
      m.initTagForm();
      m.initOrgtagSearch("tag-form", "name", {
        showPath: true
      });
    }],
    [/^\/organisation-tag\/([1-9][0-9]*)\/note$/, function (orgtagIdString) {
      m.note_markdown();
    }],

    [/^\/event-tag$/, function () {
      m.init_eventtag_search("tag-search", "search", {
        showEntity: true,
        showNotes: true
      });
      $("#eventtag-search input[name='search']").focus();
      m.visibility();
    }],
    [/^\/event-tag\/([1-9][0-9]*)$/, function (eventtagIdString) {
      m.initTagForm();
      m.init_eventtag_search("tag-form", "name", {
        showPath: true,
        excludeTagId: parseInt(eventtagIdString)
      });
    }],
    [/^\/event-tag\/new$/, function () {
      m.initTagForm();
      m.init_eventtag_search("tag-form", "name", {
        showPath: true
      });
    }],
    [/^\/event-tag\/([1-9][0-9]*)\/note$/, function (eventtagIdString) {
      m.note_markdown();
    }],
  ],

  "handle": function () {
    var path = window.location.pathname;
    if (path.indexOf(m.urlRoot) !== 0) {
      console.log("Path does not match url root", path, m.urlRoot);
    }
    path = "/" + path.substring(m.urlRoot.length);
    $.each(m.route, function (index, value) {
      var regex = value[0];
      var func = value[1];
      var match = path.match(regex);
      window.match = match;
      if (match) {
        func.apply(null, match.slice(1));
        return false;
      }
    });
  }
};



$(window.document).ready(function () {
  window.document.cookie = 'j=1';
  $.ajaxSetup({ "traditional": true });
  m.currentUser = $("#account").find("a").length === 2;
  m.handle();
});





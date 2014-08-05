"use strict";

/*global window, $, _, Backbone, markdown, google, History */




function urlRewriteStatic (uri, root, options, parameters, next) {

  if (!options) {
    options = {};
  }

  if (!parameters) {
    parameters = {};
  }

  if (!root) {
    root = "/";
  }

  var a = document.createElement('a');
  a.href = uri;
  
  var scheme = a.protocol;
  var schemeIndex = null;
  if (!!scheme) {
    schemeIndex = uri.indexOf(scheme);
    if (schemeIndex != 0) {
      scheme = null;
      schemeIndex = null
    }
  }
  var netloc = a.hostname || "localhost";
  if (a.port.length) {
    netloc += ":" + a.port;
  }
  if (!!netloc) {
    if (_.isNull(schemeIndex)) {
      netloc = null;
    }
  }
  var length = uri.indexOf("?");
  var path = a.pathname;
  if (length !== -1) {
    path = path.substr(path.length - length);
  } else {
    path = path.substr(path.length - uri.length);
  }
  var query = a.search;
  if (query.length) {
    query = query.substr(1);
  }
  var fragment = a.hash;
  if (fragment.length) {
    fragment = fragment.substr(1);
  }

  if (path.indexOf("/") === 0 && path.indexOf(root) !== 0) {
    path = root + path.substr(1);
  }

  var arguments_ = _.clone(parameters);

  var queryValues = {};
  if (query.length) {
    _.each(query.split("&"), function (segment, i) {
      var index = segment.indexOf("=");
      if (index === -1) {
        var key = segment;
        var value = "";
      } else {
        var key = segment.substr(0, index);
        var value = segment.substr(index + 1);
      }

      key = decodeURIComponent(key);
      value = decodeURIComponent(value);
      
      if (_.has(queryValues, key)) {
        if (!_.isArray(queryValues[key])) {
          queryValues[key] = [queryValues[key]];
        }
        queryValues[key].push(value);
      } else {
        queryValues[key] = value;
      }
    });
  }

  _.each(queryValues, function (value, key) {
    if (_.isNull(value) || _.isUndefined(value) || value.length === 0) {
      delete arguments_[key];
    } else {
      arguments_[key] = value;
    }
  });

  _.each(options, function (value, key) {
    if (_.isNull(value) || _.isUndefined(value) || value.length === 0) {
      delete arguments_[key];
    } else {
      arguments_[key] = value;
    }
  });
  
  if (!!next) {
    arguments_["next"] = urlRewriteStatic(next, root);
  }

  queryValues = [];
  _.each(arguments_, function (value, key) {
    if (!_.isArray(value)) {
      value = [value];
    }
    _.each(value, function (v, i) {
      queryValues.push(encodeURIComponent(key) + "=" + encodeURIComponent(v));
    });
  });

  queryValues.sort();
         
  query = queryValues.join("&");

  var uri = "";
  if (scheme) {
    uri += scheme + "//";
  }
  if (netloc) {
    uri += netloc;
  }
  if (path) {
    uri += path;
  }
  if (query) {
    uri += "?" + query;
  }
  if (fragment) {
    uri += "#" + fragment;
  }

  return uri
}



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
    "south": 49.829,
    "north": 58.988,
    "west": -12.304,
    "east": 3.912
  }),

  searchString: function () {
    var url = window.History.getState()["hash"];

    var index = url.indexOf("?");
    if (index === -1) {
      return "";
    }
    return url.substr(index + 1);
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
    html = html.replace(/>\s+/gm, ">");
    html = html.replace(/\s+</gm, "<");
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
    }

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

  process: {
    tagPacket: function (tagListId, tagPacket, tagListName, options) {
      var showEntity = options && options.showEntity;
      var showNotes = options && options.showNotes;
      var showPath = options && options.showPath;
      var showLink = options && options.showLink;
      var entityUrl = options && options.entityUrl;
      var excludeTagIdList = options && options.excludeTagIdList;

      var $tagList = $(tagListId);

      $tagList.empty();
      
      $.each(tagPacket, function (index, value) {
        if (_.contains(excludeTagIdList, value.id)) {
          return;
        }
        var templateParameters = {
	  tag: value,
	  entity: showEntity,
	  note: showNotes,
          path: showPath,
          link: showLink,
          unlink: false,
          next: window.location.href,
          parameters: m.parameters
	};
        if (showLink) {
          templateParameters.linkUrl = entityUrl + "/tag/" + value.id;
        }
	var $tagLi = m.$template("tag-li.html", templateParameters);
	$tagList.append($tagLi);
	$tagList.append(" ");
      });
    },

    orgtagPacket: function (tag_list_id, orgtagPacket, options) {
      return m.process.tagPacket(tag_list_id, orgtagPacket, "orgtag_list", options);
    },

    eventtagPacket: function (tag_list_id, eventtagPacket, options) {
      return m.process.tagPacket(tag_list_id, eventtagPacket, "eventtag_list", options);
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

  urlRewrite: function (path, parameters) {
    return urlRewriteStatic(path, m.urlRoot, parameters, null, null);
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

  initMap: function (callback) {
    var mapView = new window.MapView();
    window.mapView = mapView;
    $("#mango-map-canvas").replaceWith(mapView.$el);
    callback(mapView);
  },



  initHomeMap: function (mapView, tag) {
    var orgCollection = new window.OrgCollection();
    var orgCollectionView = new window.OrgCollectionView({
      collection: orgCollection,
      mapView: mapView
    });
    var eventCollection = new window.EventCollection();
    var eventCollectionView = new window.EventCollectionView({
      collection: eventCollection,
      mapView: mapView
    });

    var data = {
      pageView: "marker",
    }
    if (tag) {
      data.tag = tag
    }

    orgCollection.fetch({
      data: data,
      success: function (collection, response) {
        eventCollection.fetch({
          data: data,
          success: function (collection, response) {
            eventCollectionView.initialize();
            eventCollectionView.render(true);
          },
          error: function (collection, response) {
            if (response.statusText !== "abort") {
              console.log("error", collection, response);
            }
          }
        });

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

  initHome: function (tagUrl, orgUrl) {
    (function () {
      var $form = $("#mango-dsei-form-country");
      $form.submit(false);
      var $inputDisplay = $("#mango-dsei-input-country-display");
      var $inputValue = $("#mango-dsei-input-country-value");
      var url = m.urlRoot + tagUrl;
      $.getJSON(url, function (data) {
        var tagName = data.tagName;
        var countries = data.countries;
        var data = [];
        _.each(countries, function (el) {
          data.push({
            "value": el[1],
            "label": el[0],
            "count": el[2],
          });
        });
        var autocomplete = $inputDisplay.autocomplete({
          source: data,
          minLength: 0,
          focus: function (event, ui) {
            return false;
          },
          select: function (event, ui) {
            //$inputDisplay.val(ui.item.label);
            $inputValue.val(ui.item.value);
            $form.unbind("submit", false);
            $form.submit();
            return false;
          }
        }).data("ui-autocomplete")._renderItem = function (ul, item) {
          return $("<li>")
            .append("<a>" + item.label + " (" + item.count + ")</a>")
            .appendTo(ul);
        };
        $inputDisplay.focus(function () {
          $(this).autocomplete("search", $(this).val());
        });
      });
    }());

    (function () {
      var $form = $("#mango-dsei-form-org");
      $form.submit(false);
      var $inputDisplay = $("#mango-dsei-input-org-display");
      var url = m.urlRoot + orgUrl;
      $.getJSON(url, function (data) {
        var autocomplete = $inputDisplay.autocomplete({
          source: data,
          minLength: 0,
          focus: function (event, ui) {
            return false;
          },
          select: function (event, ui) {
            //$inputDisplay.val(ui.item.label);
            window.location.href = m.urlRoot + ui.item.value.substring(1);
            return false;
          }
        }).data("ui-autocomplete")._renderItem = function (ul, item) {
          return $("<li>")
            .append("<a>" + item.label + "</a>")
            .appendTo(ul);
        };
        $inputDisplay.focus(function () {
          $(this).autocomplete("search", $(this).val());
        });
      });
    }());
  },

  initOrg: function (mapView) {
    $("div.address-row div.pin").each(function (i) {
      var $pin = $(this);
      var $circle = mapView.addMarker(
        parseFloat($pin.attr("latitude")),
        parseFloat($pin.attr("longitude"))
      );
      $pin.html($circle);
    });
    mapView.fit();

    $("input[name='end_date']").datepicker({
      dateFormat: "yy-mm-dd",
      numberOfMonths: 1,
      changeMonth: true,
      changeYear: true
    });

    m.orgMarkdown();
    m.orgSearch();
  },

  initOrgSearch: function (mapView) {
    var orgSearch = new window.OrgSearch();
    var orgSearchView = new window.OrgSearchView({
      model: orgSearch,
      $form: $("#org-search"),
      $results: $("#org_list").find(".column"),
      $paging: $("#org_list").find(".counts"),
      $social: $("#org_list").find(".mango-social-bar"),
      mapView: mapView
    });
    $("#org-search").replaceWith(orgSearchView.$el);

    if (window.location.href.indexOf("#") === -1) {
      orgSearchView.send();
    } else {
      orgSearchView.popstate();
    }

    if (window.History.enabled) {
      History.Adapter.bind(window, "statechange", orgSearchView.popstate);
    }

    window.orgSearch = orgSearch;

    return orgSearch;
  },

  initEvent: function (mapView) {
    $("div.address-row div.pin").each(function (i) {
      var $pin = $(this);
      var $circle = mapView.addMarker(
        $pin.attr("latitude"),
        $pin.attr("longitude")
      );
      $pin.html($circle);
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

    m.eventMarkdown();
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

  initTagSearch: function (id, field, url, callback, options) {
    var form = $("#" + id);
    var search = m.get_field(form, field);
    var showPath = options.showPath;

    var $path = form.find("input[name='path']");
    var pathValue = function () {
      return $path.is(":checked") && 1 || null;
    };
    var $sort = form.find("select[name='sort']");
    var sortValue = function () {
      return $sort.val() || null;
    };
    var visibility = form.find("input[name='visibility']");
    var throbber = $("<img>").attr({
      "src": m.urlRoot + "static/image/throbber.gif",
      "class": "throbber"
    }).hide();
    form.find("input[type='submit']").before(throbber);
    var xhr = null;

    if (typeof currentTagList != "undefined") {
      // Defined in entity_tag.html script tag.
      options.excludeTagIdList = currentTagList;
    }

    var change = function (value) {
      if (xhr && xhr.readyState !== 4) {
        xhr.abort();
      }
      var data = {
        search: search.input.val(),
        path: pathValue(),
        sort: sortValue()
      };
      if (visibility.length) {
        data.visibility = visibility.val();
      }
      xhr = $.ajax(url, {
        "dataType": "json",
        "data": data,
        "success": function (data, textStatus, jqXHR) {
          if (_.isNull(showPath) || _.isUndefined(showPath)) {
            options.showPath = pathValue();
          }
          callback("#tag_list", data, options);
        },
        "error": m.ajaxError,
        "complete": function (jqXHR, textStatus) {
          throbber.hide();
        }
      });
      throbber.show();
    };

    if (search) {
      m.on_change(search.input, id + "_" + field, change, 500);
    }
    $path.change(change);
    $sort.change(change);
    visibility.change(change);
  },

  initOrgtagSearch: function (id, field, options) {
    m.initTagSearch(id, field, m.urlRoot + "organisation-tag", m.process.orgtagPacket, options);
  },

  initEventtagSearch: function (id, field, options) {
    m.initTagSearch(id, field, m.urlRoot + "event-tag", m.process.eventtagPacket, options);
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

  initAddress: function (mapView) {
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
      mapView.fit();
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

    var updateMarker = mapView.clickDraggableMarker(set_manual_position);

    var address_search = function () {
      $.ajax(m.urlRoot + "address/lookup", {
        "dataType": "json",
        "data": {
          "postal": postal.input.val(),
          "lookup": lookup.input.val()
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

    manual_control_button.click(function () {
      updateMarker();
      clear_manual_position();
      address_search();
    });

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
    inputPath.change(function () {
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

  noteMarkdown: function () {
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

  orgMarkdown: function () {
    var form = $("#org-form");
    var text = m.get_field(form, "description");
    var preview = $(".description.markdown-preview");
    var on_change = function (value) {
      preview.html(m.filter.markdown(value));
      m.convert_inline_links($(".description.markdown-preview"));
    };
    if (text) {
      m.on_change(text.input, "org-form" + "_" + "text", on_change, 500);
      on_change(text.input.val());
    }
  },

  orgSearch: function () {
    var form = $("#org-form");
    var text = m.get_field(form, "name");
    var $list = $("#mango-similar-org-list");
    var url = m.urlRoot + "organisation/search";
    var on_change = function (value) {
      $list.empty();
      if (!value) {
        return;
      }
      $.getJSON(url, {name: value}, function (data, textStatus, jqXHR) {
        _.each(data, function(org) {
          org.url = "/organisation/" + org.org_id;
          $list.append($("<div>").html(m.template("org-box.html", {
            org: org,
            m: m,
            parameters: m.parameters,
            note: false
          })));
        });
      });
    };
    if (text && $list) {
      m.on_change(text.input, "org-form" + "_" + "name", on_change, 500);
      on_change(text.input.val());
    }
  },

  eventMarkdown: function () {
    var form = $("#event-form");
    var text = m.get_field(form, "description");
    var preview = $(".description.markdown-preview");
    var on_change = function (value) {
      preview.html(m.filter.markdown(value));
      m.convert_inline_links($(".description.markdown-preview"));
    };
    if (text) {
      m.on_change(text.input, "event-form" + "_" + "text", on_change, 500);
      on_change(text.input.val());
    }
  },

  argumentCheckbox: function (value) {
    if (value === true || value === false) {
      return value;
    }
    return !!parseInt(value, 10);
  },

  checkboxToString: function (value) {
    value = m.argumentCheckbox(value);
    return value && "1" || null;
  },

  argumentMulti: function (valueNew, valueOld) {
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

  argumentVisibility: function (value) {
    if (_.contains(["public", "private", "pending", "all"], value)) {
      return value;
    }
    return null;
  },

  compareUnsortedList: function (a, b) {
    if (!a && !b) {
      return false;
    }
    if (!a || !b) {
      return true;
    }
    var difference = _.union(_.difference(a, b), _.difference(b, a));
    return difference.length > 0;
  },

  compareLowercase: function (a, b) {
    if (!a && !b) {
      return false;
    }
    if (!a || !b) {
      return true;
    }
    return a.toLowerCase() !== b.toLowerCase();
  },

  compareGeobox: function (a, b) {
    // a = old, b = new
    // return true if they differ, false otherwise.
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

  multiToString: function (multi) {
    return multi.join(", ");
  },

  setParameters: function () {
    if (m.currentUser && !m.parameters.visibility) {
      m.setVisibility("public");
    }
  },

  setVisibility: function (value) {
    $("a").each(function () {
      var $el = $(this);
      if ($el.hasClass("visibility-button")) {
        return;
      }
      if ($el.hasClass("change-visibility")) {
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

  updateVisibilityButtons: function (url) {
    if (url.toLowerCase().indexOf("visibility=") >= 0) {
      url = url.replace(/visibility=[\w\-]*/gi, "");
    }
    $(".visibility-button").each(function () {
      var $el = $(this);
      var href;
      var value = $el.attr("id").substring(11);
      var visibility = "visibility=" + value;
      if (url.indexOf("?") >= 0) {
        href = url + "&" + visibility;
      } else {
        href = url + "?" + visibility;
      }
      $el.attr("href", href);
    });
  },

  convertUtcToLocal: function () {
    var tz = null;
    $(".date-utc").each(function(el) {
      var $el=$(this);
      var date = new Date($el.text());
      var dateString = $.datepicker.formatDate('yy-mm-dd', new Date(date));
      var timeString = ('0'+date.getHours()).slice(-2) + ":" + ('0'+date.getMinutes()).slice(-2) + ":" + ('0'+date.getSeconds()).slice(-2);
      $el.text(dateString + " " + timeString);
      var i1 = date.toString().indexOf("(") + 1;
      var i2 = date.toString().indexOf(")");
      tz = date.toString().substr(i1, i2 - i1);
    });
    if (!_.isNull(tz)) {
      $(".tz-utc").text(tz);
    }
  },

  addDeleteConfirm: function () {
    var $deleteForm = $("input[name='_method'][value='delete']").parent()
    $deleteForm.on("submit", function (e) {
      return confirm("Really delete?");
    });
  },

  visibility: function () {
    if (!m.currentUser) {
      return;
    }
    $("#visibility-public").click(function (e) {
      if (e.which !== 1 || e.metaKey || e.shiftKey) {
        return;
      }
      e.preventDefault();
      m.setVisibility("public");
    });
    $("#visibility-private").click(function (e) {
      if (e.which !== 1 || e.metaKey || e.shiftKey) {
        return;
      }
      e.preventDefault();
      m.setVisibility("private");
    });
    $("#visibility-pending").click(function (e) {
      if (e.which !== 1 || e.metaKey || e.shiftKey) {
        return;
      }
      e.preventDefault();
      m.setVisibility("pending");
    });
    $("#visibility-all").click(function (e) {
      if (e.which !== 1 || e.metaKey || e.shiftKey) {
        return;
      }
      e.preventDefault();
      m.setVisibility("all");
    });
  },

  route: [
    [/^\/$/, function () {
      m.initHome("home-target", "home-org");
      m.initMap(function (mapView) {
        m.initHomeMap(mapView, null);
      });
    }],

    [/^\/dsei$/, function () {
      m.initHome("dsei-target", "dsei-org");
      m.initMap(function (mapView) {
        m.initHomeMap(mapView, "dsei-2013");
      });
    }],

    [/^\/farnborough$/, function () {
      m.initHome("farnborough-target", "farnborough-org");
      m.initMap(function (mapView) {
        m.initHomeMap(mapView, "farnborough-2014");
      });
    }],

    [/^\/note\/new$/, function () {
      m.noteMarkdown();
    }],
    [/^\/note\/([1-9][0-9]*)$/, function (noteIdString) {
      m.noteMarkdown();
    }],

    [/^\/organisation$/, function () {
      m.initMap(function (mapView) {
        m.initOrgSearch(mapView);
        m.visibility();
      });
    }],
    [/^\/event$/, function () {
      m.initMap(function (mapView) {
        m.initEventSearch(mapView);
        m.visibility();
      });
    }],
    [/^\/task\/address$/, function () {
      m.initMap(function (mapView) {
        m.initOrgSearch(mapView);
        m.visibility();
      });
    }],

    [/^\/organisation\/([1-9][0-9]*)$/, function (orgIdString) {
      m.addDeleteConfirm();
      m.initMap(function (mapView) {
        m.initOrg(mapView);
      });
    }],
    [/^\/organisation\/new$/, function () {
      m.initMap(function (mapView) {
        m.initOrg(mapView);
      });
    }],
    [/^\/organisation\/([1-9][0-9]*)\/address$/, function (orgIdString) {
      m.initMap(function (mapView) {
        m.initAddress(mapView);
      });
    }],
    [/^\/organisation\/([1-9][0-9]*)\/note$/, function (orgIdString) {
      m.noteMarkdown();
    }],
    [/^\/organisation\/([1-9][0-9]*)\/tag$/, function (orgIdString) {
      m.initOrgtagSearch("tag-search", "search", {
        showEntity: true,
        showNotes: true,
        showLink: true,
        entityUrl: "/organisation/" + orgIdString
      });
      $("#tag-search input[name='search']").focus();
      m.visibility();
    }],
    [/^\/event\/([1-9][0-9]*)$/, function (eventIdString) {
      m.addDeleteConfirm();
      m.initMap(function (mapView) {
        m.initEvent(mapView);
      });
    }],
    [/^\/event\/new$/, function () {
      m.initMap(function (mapView) {
        m.initEvent(mapView);
      });
    }],
    [/^\/event\/([1-9][0-9]*)\/address$/, function (eventIdString) {
      m.initMap(function (mapView) {
        m.initAddress(mapView);
      });
    }],
    [/^\/event\/([1-9][0-9]*)\/note$/, function (eventIdString) {
      m.noteMarkdown();
    }],

    [/^\/event\/([1-9][0-9]*)\/tag$/, function (eventIdString) {
      m.initEventtagSearch("tag-search", "search", {
        showEntity: true,
        showNotes: true,
        showLink: true,
        entityUrl: "/event/" + eventIdString
      });
      $("#tag-search input[name='search']").focus();
      m.visibility();
    }],
    [/^\/address\/([1-9][0-9]*)$/, function (addressIdString) {
      m.initMap(function (mapView) {
        m.initAddress(mapView);
      });
    }],
    [/^\/address\/([1-9][0-9]*)\/note$/, function (addressIdString) {
      m.noteMarkdown();
    }],

    [/^\/organisation-tag$/, function () {
      m.initOrgtagSearch("tag-search", "search", {
        showEntity: true,
        showNotes: true
      });
      $("#tag-search input[name='search']").focus();
      m.visibility();
    }],
    [/^\/organisation-tag\/([1-9][0-9]*)$/, function (orgtagIdString) {
      m.initTagForm();
      m.initOrgtagSearch("tag-form", "name", {
        showPath: true,
        excludeTagIdList: [parseInt(orgtagIdString, 10)]
      });
    }],
    [/^\/organisation-tag\/new$/, function () {
      m.initTagForm();
      m.initOrgtagSearch("tag-form", "name", {
        showPath: true
      });
    }],
    [/^\/organisation-tag\/([1-9][0-9]*)\/note$/, function (orgtagIdString) {
      m.noteMarkdown();
    }],

    [/^\/event-tag$/, function () {
      m.initEventtagSearch("tag-search", "search", {
        showEntity: true,
        showNotes: true
      });
      $("#tag-search input[name='search']").focus();
      m.visibility();
    }],
    [/^\/event-tag\/([1-9][0-9]*)$/, function (eventtagIdString) {
      m.initTagForm();
      m.initEventtagSearch("tag-form", "name", {
        showPath: true,
        excludeTagIdList: [parseInt(eventtagIdString, 10)]
      });
    }],
    [/^\/event-tag\/new$/, function () {
      m.initTagForm();
      m.initEventtagSearch("tag-form", "name", {
        showPath: true
      });
    }],
    [/^\/event-tag\/([1-9][0-9]*)\/note$/, function (eventtagIdString) {
      m.noteMarkdown();
    }],
    [/^\/history$/, function () {
      m.convertUtcToLocal();
    }],
    [/revision$/, function () {
      m.convertUtcToLocal();
    }]
  ],



  handle: function () {
    m.setParameters();
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
  m.handle();
});





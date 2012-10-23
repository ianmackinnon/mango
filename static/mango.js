"use strict";

/*global window, $, _, Backbone, markdown, google */

var m = {

  parameters: null,

  _templateCache: {},

  template: function (name, data) {
    var url = "/static/template/" + name;

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

  shrinkGeobox: function (geobox) {
    var other = {
      south: geobox.south * 0.8 + geobox.north * 0.2,
      north: geobox.south * 0.2 + geobox.north * 0.8,
      west: geobox.west * 0.8 + geobox.east * 0.2,
      east: geobox.west * 0.2 + geobox.east * 0.8
    };
    return other;
  },

  latitude: function(value) {
    value = parseFloat(value);
    if (value > 90) {
      return NaN;
    }
    if (value < -90) {
      return NaN;
    }
    return value;
  },

  longitude: function(value) {
    value = parseFloat(value);
    if (value > 180) {
      return NaN;
    }
    if (value < -180) {
      return NaN;
    }
    return value;
  },

  mapBoundsToGeobox: function (bounds) {
    var southWest = bounds.getSouthWest();
    var northEast = bounds.getNorthEast();
    var geobox = {
      south: southWest.lat(),
      north: northEast.lat(),
      west: southWest.lng(),
      east: northEast.lng()
    };
    return geobox;
  },

  stringToGeobox: function (string) {
    var coords = string.split(",");
    if (coords.length != 4) {
      return null;
    }
    var geobox = {};
    var points = ["south", "north", "west", "east"];
    for (var c = 0; c < 4; c += 1) {
      var value;
      if (c < 2) {
        value = m.latitude(coords[c]);
      } else {
        value = m.longitude(coords[c]);
      }
      if (isNaN(value)) {
        return null;
      }
      geobox[points[c]] = value;
    }
    return geobox;
  },

  geoboxToString: function (geobox) {
    return geobox.south + ", " + geobox.north +
      ", " + geobox.west + ", " + geobox.east;
  },

  geoboxArea: function (geobox) {
    var radiusOfEarth = 6378.1;
    var circumferenceOfEarth = 40075;
    var areaOfEarth = 510072000;

    var east = geobox.east + 360 * (geobox.east < geobox.west);

    var height = (
      Math.sin(geobox.north * Math.PI / 180) -
      Math.sin(geobox.south * Math.PI / 180)
    );

    var segmentArea = 2 * Math.PI * radiusOfEarth * height * radiusOfEarth;

    var sliceArea = segmentArea * (east - geobox.west) / 360;

    return sliceArea;
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

  "map": null,
  "markers": [],
  "positions": [],

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

  "clear_points": function () {
    $.each(m.markers, function (index, marker) {
      marker.setMap(null);
    });
    m.markers = [];
    m.positions = [];
  },

  "fit_map": function (callback) {
    m.fit_map_delay();
    google.maps.event.addListener(m.map, 'idle', function () {
      m.fit_map_delay();
      google.maps.event.clearListeners(m.map, 'idle');
      if (callback) {
        callback();
      }
    });
  },

  "fit_map_delay": function () {
    var bounds = null;
    $.each(m.markers, function (index, marker) {
      if (!bounds) {
        bounds = new google.maps.LatLngBounds();
      }
      bounds.extend(marker.position);
    });
    $.each(m.positions, function (index, position) {
      if (!bounds) {
        bounds = new google.maps.LatLngBounds();
      }
      bounds.extend(position);
    });
    if (bounds) {
      m.map.fitBounds(bounds);
      m.map.setZoom(Math.min(m.map.getZoom(), 16));
    }
  },

  "url_rewrite": function (path, parameters) {
    var url = path;
    if (url.indexOf("/") === 0) {
      url = m.url_root + url.substring(1);
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

  "init_entity_search": function (searchId, tagList, process, packet) {
    var form = $(searchId);
    var name_search = m.get_field(form, "name_search");
    var lookup = m.get_field(form, "lookup");
    var tag = form.find("input[name='tag']");
    var past = m.get_field(form, "past");
    var visibility = form.find("input[name='visibility']");
    var dropdown = form.find("ul.dropdown");
    var throbber = $("<img>").attr({
      "src": m.url_root + "static/image/throbber.gif",
      "class": "throbber"
    }).hide();

    var change;  // change passes itself

    var tag_values = function () {
      var text = tag.val();
      var parts = text.split(",");
      _(parts).each(function (p) {
        parts[p] = parts[p]
          .replace(/(^\s|\s$)+/g, '')
          .replace(/\s+/g, '-');
      });
      return parts;
    };

    var tag_search_term = function () {
      var parts = tag_values();
      return (!!parts && parts[parts.length - 1]) || null;
    };

    var tag_replace_last = function (term) {
      var parts = tag_values();
      parts.pop();
      parts.push(term);
      tag.val(parts.join(", ") + ((parts && ", ") || ""));
      change();
    };

    var update_dropdown = function () {
      dropdown.empty();
      var term = tag_search_term();
      var tags = (term && tagList.filter(function (element, index, array) {
        return element.short.substring(0, term.length) === term;
      })) || [];
      var helper = function (name) {
        return function () {
          tag_replace_last(name);
        };
      };
      var i;
      for (i = 0; i < Math.min(10, tags.length); i += 1) {
        var tag = tags[i];
        var li = $("<li>" + tag.short + "</li>");
        li.click(helper(tag.short));
        dropdown.append(li);
      }
    };

    tag.focus(function () {
      update_dropdown();
      dropdown.show();
    });

    tag.blur(function () {
      dropdown.fadeOut(100, function () {
        if (tag.is(":focus")) {
          dropdown.show();
        }
      });
    });

    tag.keyup(update_dropdown);

    form.append(throbber);
    var xhr = null;

    change = function (value, offset) {
      if (xhr && xhr.readyState !== 4) {
        xhr.abort();
      }
      var data = m.filter_object_true({
        "name_search": name_search.input.val(),
        "tag": tag_values(),
        "offset": offset || 0,
      });
      if (!!lookup) {
        data.lookup = lookup.input.val();
      }
      if (past) {
        data.past = past.input.attr("checked") && past.input.val();
      }
      if (visibility.length) {
        data.visibility = visibility.val();
      }
      xhr = $.ajax(window.location.pathname, {
        "dataType": "json",
        "data": data,
        "success": function (data, textStatus, jqXHR) {
          process(data, change);
        },
        "error": m.ajaxError,
        "complete": function (jqXHR, textStatus) {
          throbber.hide();
        }
      });
      throbber.show();
    };
    m.on_change(name_search.input, "name_search", change, 500);
    if (!!lookup) {
      m.on_change(lookup.input, "lookup", change, 500);
    }
    m.on_change(tag, "tag", change, 500);
    if (past) {
      m.on_change(past.input, "past", change, 500);
    }
    visibility.change(change);
    process(packet, change);
  },

  "all_addresses": function () {
    var data = {};
    if (m.parameters.visibility) {
      data.visibility = m.parameters.visibility;
    }
    $.ajax(m.url_root + "address", {
      "dataType": "json",
      "data": data,
      "success": function (data, textStatus, jqXHR) {
        m.clear_points();
        $.each(data, function (i, result) {
          var position = new google.maps.LatLng(result.latitude, result.longitude);
          var color;
          if (result.entity === "org") {
            color = "ff7755";
          } else {
            color = "5577ff";
          }
          var pin_url = m.url_root + "static/image/map/marker/dot-" + color + ".png";
          var marker = new google.maps.Marker({
            position: position,
            map: m.map,
            icon: pin_url,
            title: result.name,
          });
          if (result.entity === "event") {
            marker.setZIndex(500);
          }
          var helper = function () {
            return function () {
              window.location.replace(m.url_root + "address/" + result.address_id);
            };
          };
          google.maps.event.addListener(marker, 'click', helper());
          m.markers.push(marker);

        });
        m.fit_map(function () {
          m.map.setCenter(new google.maps.LatLng(
            54.12667879191665,
            -2.8131760625000224
          ));
          m.map.setZoom(5);
        });
      },
      "error": m.ajaxError
    });

    var manual_control = $("<div class='caption'>");
    var img1 = $("<img>").attr("src", m.url_root + "static/image/map/marker/dot-ff7755.png");
    var img2 = $("<img>").attr("src", m.url_root + "static/image/map/marker/dot-5577ff.png");
    var manual_control_hint = $("<ul>");
    var li1 = $("<li>").text(" Arms company");
    var li2 = $("<li>").text(" Future action/event");
    li1.prepend(img1);
    li2.prepend(img2);
    manual_control_hint.append(li1);
    manual_control_hint.append(li2);
    manual_control.append(manual_control_hint);
    $("#mango-map-box").append(manual_control);

  },

  initMap: function () {
    var mapView = new window.MapView();
    $("#mango-map-box").replaceWith(mapView.$el);
    return mapView;
  },

  initOrgSearch: function (mapView) {
    var orgSearch = new window.OrgSearch();
    var orgSearchView = new window.OrgSearchView({
      model: orgSearch,
      $source: $("#org-search"),
      $orgColumn: $("#org_list").find(".column"),
      $orgPaging: $("#org_list").find(".counts"),
      mapView: mapView
    });
    $("#org-search").replaceWith(orgSearchView.$el);
    orgSearchView.send();
    return orgSearch;
  },

  "ajaxError": function (jqXHR, textStatus, errorThrown) {
    if (textStatus === "abort") {
      return;
    }
    console.log("error", jqXHR, textStatus, errorThrown);
  },

  "init_orgtag_search": function (id, field) {
    var form = $("#" + id);
    var search = m.get_field(form, field);
    var visibility = form.find("input[name='visibility']");
    var throbber = $("<img>").attr({
      "src": m.url_root + "static/image/throbber.gif",
      "class": "throbber"
    }).hide();
    form.append(throbber);
    var xhr = null;

    var change = function (value) {

      if (xhr && xhr.readyState !== 4) {
        xhr.abort();
      }
      var data = {
        "search": search.input.val()
      };
      if (visibility.length) {
        data.visibility = visibility.val();
      }
      xhr = $.ajax(m.url_root + "organisation-tag", {
        "dataType": "json",
        "data": data,
        "success": function (data, textStatus, jqXHR) {
          m.process.orgtag_packet("#tag_list", data);
        },
        "error": m.ajaxError,
        "complete": function (jqXHR, textStatus) {
          throbber.hide();
        }
      });
      throbber.show();
    };

    m.on_change(search.input, id + "_" + field, change, 500);
    visibility.change(change);
  },

  "init_eventtag_search": function (id, field) {
    var form = $("#" + id);
    var search = m.get_field(form, field);
    var visibility = form.find("input[name='visibility']");
    var throbber = $("<img>").attr({
      "src": m.url_root + "static/image/throbber.gif",
      "class": "throbber"
    }).hide();
    form.append(throbber);
    var xhr = null;

    var change = function (value) {

      if (xhr && xhr.readyState !== 4) {
        xhr.abort();
      }
      var data = {
        "search": search.input.val()
      };
      if (visibility.length) {
        data.visibility = visibility.val();
      }
      xhr = $.ajax(m.url_root + "event-tag", {
        "dataType": "json",
        "data": data,
        "success": function (data, textStatus, jqXHR) {
          m.process.eventtag_packet("#tag_list", data);
        },
        "error": m.ajaxError,
        "complete": function (jqXHR, textStatus) {
          throbber.hide();
        }
      });
      throbber.show();
    };

    m.on_change(search.input, id + "_" + field, change, 500);
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

  "init_address_form": function (id) {
    var form = $("#" + id).find("form");
    var latitude = null;
    var longitude = null;
    if (!form.length) {
      var $span = $("span[latitude]");
      if (!$span.length) {
        return;
      }
      latitude = $span.attr("latitude");
      longitude = $span.attr("longitude");
      m.clear_points();
      var position = new google.maps.LatLng(
        latitude,
        longitude
      );
      var marker = new google.maps.Marker({
        position: position,
        map: m.map
      });
      m.markers.push(marker);
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
    latitude = form.find("[name='latitude']");
    longitude = form.find("[name='longitude']");

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
    $("#mango-map-box").append(manual_control);
    manual_control.append(manual_control_hint);
    manual_control.append(manual_control_span1);
    manual_control.append(manual_control_span2);
    manual_control.append(manual_control_button);

    var set_manual_position = function (position) {
      manual_latitude.val(position.lat());
      manual_longitude.val(position.lng());
      manual_control_hint.hide();
      manual_control_span1.hide();
      manual_control_span2.show();
      manual_control_button.show();
    };

    var clear_manual_position = function () {
      manual_latitude.val(null);
      manual_longitude.val(null);
      manual_control_hint.hide();
      manual_control_span1.show();
      manual_control_span2.hide();
      manual_control_button.hide();
    };

    manual_control_button.click(function () {
      m.clear_points();
      clear_manual_position();
    });

    var set_marker = function (position, title) {
      m.clear_points();
      var marker = new google.maps.Marker({
        position: position,
        title: title,
        draggable: true,
        map: m.map
      });
      google.maps.event.addListener(marker, 'drag', function () {
        var pos = marker.getPosition();
        set_manual_position(pos);
      });
      m.markers.push(marker);
    };

    google.maps.event.addListener(m.map, 'click', function (event) {
      var pos = event.latLng;
      set_marker(pos, postal.input.val());
      set_manual_position(pos);
    });

    var address_search = function () {
      $.ajax(m.url_root + "address/lookup", {
        "dataType": "json",
        "data": {
          "postal": postal.input.val(),
          "lookup": lookup.input.val(),
        },
        "success": function (data, textStatus, jqXHR) {
          if (!data.latitude) {
            m.clear_points();
            clear_manual_position();
            manual_control_hint.show();
            manual_control_span1.hide();
            return;
          }
          var position = new google.maps.LatLng(
            data.latitude,
            data.longitude
          );
          set_marker(position, data.postal);
          clear_manual_position();
          m.map.setCenter(position);
          m.map.setZoom(10);
        },
        "error": m.ajaxError
      });
    };

    search.click(address_search);

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
        var pos = new google.maps.LatLng(
          latitude.val(),
          longitude.val()
        );
        set_marker(pos, postal.input.val());
        m.map.setCenter(pos);
        m.map.setZoom(10);
      }
    }
    if (manual_latitude.val().length && manual_longitude.val().length) {
      manual_control_hint.hide();
      manual_control_span1.hide();
      manual_control_span2.show();
      manual_control_button.show();
    }

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
    m.on_change(text.input, "event-form" + "_" + "text", function (value) {
      text.label.attr("status", !!value ? "good" : "bad");
      $(".description.markdown-preview").html(m.filter.markdown(value));
      m.convert_inline_links($(".description.markdown-preview"));
    }, 500);

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
      if ($el.attr("href").indexOf(m.url_root) !== 0) {
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

  "visibility": function () {
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
      m.all_addresses();
    }],
    [/^\/note\/new$/, function () {
      m.note_markdown();
    }],
    [/^\/note\/([1-9][0-9]*)$/, function () {
      m.note_markdown();
    }],

    [/^\/organisation$/, function () {
      var mapView = m.initMap();
      window.mapView = mapView;
      m.initOrgSearch(mapView);
      m.visibility();
    }],
    [/^\/event$/, function () {
      m.init_event_search();
      m.visibility();
    }],
    [/^\/task\/address$/, function () {
      m.initOrgSearch();
      m.visibility();
    }],
    [/^\/organisation\/([1-9][0-9]*)$/, function () {
      m.clear_points();
      m.add_pins();
      m.fit_map();
    }],
    [/^\/organisation\/([1-9][0-9]*)\/address$/, function () {
      m.init_address_form("address-form");
      $("#address-form textarea[name='postal']").focus();
    }],
    [/^\/organisation\/([1-9][0-9]*)\/note$/, function () {
      m.note_markdown();
    }],
    [/^\/event\/([1-9][0-9]*)$/, function () {
      m.clear_points();
      m.add_pins();
      m.fit_map();
      m.event_markdown();
    }],
    [/^\/event\/([1-9][0-9]*)\/address$/, function () {
      m.init_address_form("address-form");
      $("#address-form textarea[name='postal']").focus();
    }],
    [/^\/event\/([1-9][0-9]*)\/note$/, function () {
      m.note_markdown();
    }],

    [/^\/address\/([1-9][0-9]*)$/, function () {
      m.init_address_form("address-form");
      $("#address-form textarea[name='postal']").focus();
    }],
    [/^\/address\/([1-9][0-9]*)\/note$/, function () {
      m.note_markdown();
    }],

    [/^\/organisation-tag$/, function () {
      m.init_orgtag_search("tag-search", "search");
      $("#orgtag-search input[name='search']").focus();
      m.visibility();
    }],
    [/^\/organisation-tag\/([1-9][0-9]*)$/, function () {
      m.init_orgtag_search("orgtag-form", "name");
      $("#orgtag-form input[name='name']").focus();
    }],
    [/^\/organisation-tag\/new$/, function () {
      m.init_orgtag_search("orgtag-form", "name");
      $("#orgtag-form input[name='name']").focus();
    }],
    [/^\/organisation-tag\/([1-9][0-9]*)\/note$/, function () {
      m.note_markdown();
    }],

    [/^\/event-tag$/, function () {
      m.init_eventtag_search("tag-search", "search");
      $("#eventtag-search input[name='search']").focus();
      m.visibility();
    }],
    [/^\/event-tag\/([1-9][0-9]*)$/, function () {
      m.init_eventtag_search("eventtag-form", "name");
      $("#eventtag-form input[name='name']").focus();
    }],
    [/^\/event-tag\/new$/, function () {
      m.init_eventtag_search("eventtag-form", "name");
      $("#eventtag-form input[name='name']").focus();
    }],
    [/^\/event-tag\/([1-9][0-9]*)\/note$/, function () {
      m.note_markdown();
    }],
  ],

  "handle": function () {
    var path = window.location.pathname;
    if (path.indexOf(m.url_root) !== 0) {
      console.log("Path does not match url root", path, m.url_root);
    }
    path = "/" + path.substring(m.url_root.length);
    $.each(m.route, function (index, value) {
      var regex = value[0];
      var func = value[1];
      if (path.match(regex)) {
        func();
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





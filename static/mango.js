/*global window, $, _, Backbone, google, History */

var m = (function () {
  "use strict";

  var m = {

    urlRoot: null,
    parameters: null,
    currentUser: null,
    moderator: null,
    eventsEnabled: null,
    map: null,
    xsrf: null,
    cookiePrefix: null,
    next: null,

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

    setCookie: function (key, value) {
      var path = m.urlRoot;

      if (m.cookiePrefix) {
        key = "" + m.cookiePrefix + "-" + key;
      }

      var cmd = ("" + key + "=" + JSON.stringify(value) +
                 "; path=" + path);

      console.log("cookie", cmd);

      window.document.cookie = cmd;
    },

    ukGeobox: new window.Geobox({
      "south": 49.829,
      "north": 58.988,
      "west": -12.304,
      "east": 3.912
    }),

    searchString: function () {
      var url = window.History.getState().hash;

      var index = url.indexOf("?");
      if (index === -1) {
        return "";
      }
      return url.substr(index + 1);
    },

    templator: templator,

    currentUser: null,

    filter: {
      h: function (text) {
        return String(text)
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/"/g, "&apos;");
      },

      newline: function (text) {
        return String(text)
          .replace(/\n/g, "<br />");
      },

      newlineComma: function (text) {
        return String(text)
          .replace(/\n/g, ", ");
      },

      nbsp: function (text) {
        return String(text)
          .replace(/[\s]+/g, "&nbsp;")
          .replace(/-/g, "&#8209;");

      },

      pageTime: function (time) {
        return time;
      },

      pageDate: function (date) {
        return $.datepicker.formatDate("D dd M yy", new Date(date));
      }

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
          m.templator.load(["tag-li.html", "visibility-bar.html"], function () {
            var html = m.templator.render("tag-li.html", templateParameters, {
              compact: true
            });
	    var $tagLi = $(html);
	    $tagList.append($tagLi);
	    $tagList.append(" ");
          });
        });
      },

      orgtagPacket: function (tagListId, orgtagPacket, options) {
        return m.process.tagPacket(
          tagListId, orgtagPacket, "orgtag_list", options);
      },

      eventtagPacket: function (tagListId, eventtagPacket, options) {
        return m.process.tagPacket(
          tagListId, eventtagPacket, "eventtag_list", options);
      }
    },

    timers: {},

    lastValues: {},

    onChange: function (input, name, callback, ms) {
      m.lastValues[name] = m.values(input);
      m.timers[name] = null;
      var change = function () {
        var value = m.values(input);
        if (value === m.lastValues[name]) {
          return;
        }
        m.lastValues[name] = value;
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

    values: function (input) {
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
      var data = {
        pageView: "marker"
      };
      if (tag) {
        data.tag = tag;
      }

      var orgCollection = new window.OrgCollection();
      var orgCollectionView = new window.OrgCollectionView({
        collection: orgCollection,
        mapView: mapView
      });
      orgCollection.fetch({
        data: data,
        success: function (collection, response) {
          orgCollectionView.initialize();
          orgCollectionView.render(true);
        },
        error: function (collection, response) {
          if (response.statusText !== "abort") {
            console.error("error", collection, response);
          }
        }
      });

      if (m.eventsEnabled) {
        var eventCollection = new window.EventCollection();
        var eventCollectionView = new window.EventCollectionView({
          collection: eventCollection,
          mapView: mapView
        });

        eventCollection.fetch({
          data: data,
          success: function (collection, response) {
            eventCollectionView.initialize();
            eventCollectionView.render(true);
          },
          error: function (collection, response) {
            if (response.statusText !== "abort") {
              console.error("error", collection, response);
            }
          }
        });
      }
    },

    initHome: function (tagUrl, orgUrl) {

      (function () {
        var $form = $("#mango-dsei-form-country");
        $form.submit(false);
        var $inputDisplay = $("#mango-dsei-input-country-display");
        var $inputValue = $("#mango-dsei-input-country-value");
        var url = m.urlRoot + tagUrl;
        $.getJSON(url, function (data) {
          var autoData = [];
          _.each(data.countries, function (el) {
            autoData.push({
              "value": el[1],
              "label": el[0],
              "count": el[2]
            });
          });
          var autocomplete = $inputDisplay.autocomplete({
            source: autoData,
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
            source: function (request, response) {
              var autoData = [];
              var term = request.term.toLowerCase();
              _.each(data, function (item, i) {
                if (item.label.toLowerCase().indexOf(term) > -1) {
                  autoData.push(item);
                } else if (!!item.alias) {
                  _.each(item.alias, function (alias, j) {
                    if (alias.toLowerCase().indexOf(term) > -1) {
                      autoData.push({
                        "label": item.label + " (" + alias + ")",
                        "value": item.value
                      });
                    }
                  });
                }
              });
              response(autoData);
            },
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
      if (!!mapView) {
        $("div.address-row div.pin").each(function (i) {
          var $pin = $(this);
          var $circle = mapView.addMarker(
            parseFloat($pin.attr("latitude")),
            parseFloat($pin.attr("longitude"))
          );
          $pin.html($circle);
        });
        mapView.fit();
      }

      $("input[name='end_date']").datepicker({
        dateFormat: "yy-mm-dd",
        numberOfMonths: 1,
        changeMonth: true,
        changeYear: true
      });

      m.orgMarkdown();
      m.initOrgSearchCreate();
    },

    initOrgSearchForm: function (mapView) {
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
        if (!mapView) {
          orgSearchView.send();
        }
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
      if (!!mapView) {
        $("div.address-row div.pin").each(function (i) {
          var $pin = $(this);
          var $circle = mapView.addMarker(
            $pin.attr("latitude"),
            $pin.attr("longitude")
          );
          $pin.html($circle);
        });
        mapView.fit();
      }

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

    initEventSearchForm: function (mapView) {
      var eventSearch = new window.EventSearch();
      var eventSearchView = new window.EventSearchView({
        model: eventSearch,
        $form: $("#event-search"),
        $results: $("#event_list").find(".column"),
        $paging: $("#event_list").find(".counts"),
        mapView: mapView
      });
      $("#event-search").replaceWith(eventSearchView.$el);

      if (window.location.href.indexOf("#") === -1) {
        if (!mapView) {
          eventSearchView.send();
        }
      } else {
        eventSearchView.popstate();
      }

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
      console.error("error", jqXHR, textStatus, errorThrown);
    },

    initTagSearch: function (id, field, url, callback, options) {
      var form = $("#" + id);
      var search = m.getField(form, field);
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
        m.onChange(search.input, id + "_" + field, change, 500);
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

    getField: function (form, name) {
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
      var postal = m.getField(form, "postal");
      var lookup = m.getField(form, "lookup");
      var source = m.getField(form, "source");

      var manualLatitude = form.find("[name='manual_latitude']");
      var manualLongitude = form.find("[name='manual_longitude']");
      var latitude = form.find("[name='latitude']");
      var longitude = form.find("[name='longitude']");

      var validate = function () {
        var x = form.find("[status='bad']");
        if (x.length) {
          submit.attr("disabled", "disabled");
        } else {
          submit.removeAttr("disabled");
        }

        if (postal.input.val().length || lookup.input.val().length) {
          search.removeAttr("disabled");
        } else {
          search.attr("disabled", "disabled");
        }
      };

      var manualControl = $("<div class='caption'>");
      var manualControlHint = $("<span>").text("The address could not be found automatically. You may wish to check the address for accuracy, consider adding a machine-friendly 'Lookup' address, or click the map to set the position manually.").hide();
      var manualControlSpan1 = $("<span>").text("Click on the map or drag a marker to set position manually.").hide();
      var manualControlSpan2 = $("<span>").text("Map position has been set manually.").hide();
      var manualControlButton = $("<input type='button' id='manual_position_clear' value='Remove'>").hide();
      var manualControlSpan3 = $("<p>").text("Map position has not yet been saved.").hide();
      $("#mango-map-box").append(manualControl);
      manualControl.append(manualControlHint);
      manualControl.append(manualControlSpan1);
      manualControl.append(manualControlSpan2);
      manualControl.append(manualControlButton);
      manualControl.append(manualControlSpan3);

      var setManualPosition = function (lat, lng) {
        manualLatitude.val(lat);
        manualLongitude.val(lng);
        manualControlHint.hide();
        manualControlSpan1.hide();
        manualControlSpan2.show();
        manualControlButton.show();
        manualControlSpan3.show();
      };

      var clearManualPosition = function () {
        manualLatitude.val(null);
        manualLongitude.val(null);
        manualControlHint.hide();
        manualControlSpan1.show();
        manualControlSpan2.hide();
        manualControlButton.hide();
        manualControlSpan3.hide();
      };

      var updateMarker = mapView.clickDraggableMarker(setManualPosition);

      var addressSearch = function () {
        $.ajax(m.urlRoot + "address/lookup", {
          "dataType": "json",
          "data": {
            "postal": postal.input.val(),
            "lookup": lookup.input.val()
          },
          "success": function (data, textStatus, jqXHR) {
            if (!data.latitude) {
              clearManualPosition();
              manualControlHint.show();
              manualControlSpan1.hide();
              return;
            }
            updateMarker(data.latitude, data.longitude);
            clearManualPosition();
            mapView.fit();
          },
          "error": m.ajaxError
        });
      };

      manualControlButton.click(function () {
        updateMarker();
        clearManualPosition();
        addressSearch();
      });

      search.click(addressSearch);

      var id = "address-form";
      m.onChange(postal.input, id + "_postal", function (value) {
        postal.label.attr("status", !!value ? "good" : "bad");
        validate();
      }, 500);
      m.onChange(source.input, id + "_source", function (value) {
        source.label.attr("status", !!value ? "good" : "bad");
        validate();
      }, 500);
      m.onChange(lookup.input, id + "_lookup", function (value) {
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
      if (manualLatitude.val().length && manualLongitude.val().length) {
        manualControlHint.hide();
        manualControlSpan1.hide();
        manualControlSpan2.show();
        manualControlButton.show();
        manualControlSpan3.hide();
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

    markdownSafe: function (text, convertLinks, callback) {
      $.ajax(m.urlRoot + "api/markdown-safe", {
        data: {
          "text": text,
          "convertLinks": convertLinks,
          "_xsrf": m.xsrf
        },
        method: "POST",
        success: function (data, textStatus, jqXHR) {
          callback(data);
        },
        error: function (jqXHR, textStatus, errorThrown) {
          m.ajaxError(jqXHR, textStatus, errorThrown);
        }
      });
    },

    noteMarkdown: function () {
      var form = $("#note-form");
      var text = m.getField(form, "text");
      var source = m.getField(form, "source");
      m.onChange(text.input, "note-form" + "_" + "text", function (value) {
        text.label.attr("status", !!value ? "good" : "bad");
        m.markdownSafe(value, true, function (html) {
          $("#note-preview .note-text").html(html);
        });
      }, 500);
      m.onChange(source.input, "note-form" + "_" + "source", function (value) {
        source.label.attr("status", !!value ? "good" : "bad");
        m.markdownSafe(value, true, function (html) {
          $("#note-preview .note-source").html(html);
        });
      }, 500);
    },

    orgMarkdown: function () {
      var form = $("#org-form");
      var text = m.getField(form, "description");
      var preview = $(".description.markdown-preview");
      var onChange = function (value) {
        m.markdownSafe(value, true, function (html) {
          preview.html(html);
        });
      };
      if (text) {
        m.onChange(text.input, "org-form" + "_" + "text", onChange, 500);
        onChange(text.input.val());
      }
    },

    initOrgSearchCreate: function () {
      var form = $("#org-form");
      var text = m.getField(form, "name");
      var $list = $("#mango-similar-org-list");
      if (!$list.length) {
        return;
      }
      var url = m.urlRoot + "organisation/search";
      var onChange = function (value) {
        $list.empty();
        if (!value) {
          return;
        }
        $.getJSON(url, {name: value}, function (data, textStatus, jqXHR) {
          _.each(data, function (org) {
            org.url = "/organisation/" + org.orgId;

            m.templator.load(["org-box.html", "visibility-bar.html"], function () {

              var html = m.templator.render("org-box.html", {
                org: org,
                m: m,
                parameters: m.parameters,
                note: false
              });
              $list.append($("<div>").html(html));
            });

          });
        });
      };
      if (text && $list) {
        m.onChange(text.input, "org-form" + "_" + "name", onChange, 500);
        onChange(text.input.val());
      }
    },

    eventMarkdown: function () {
      var form = $("#event-form");
      var text = m.getField(form, "description");
      var preview = $(".description.markdown-preview");
      var onChange = function (value) {
        m.markdownSafe(value, true, function (html) {
          preview.html(html);
        });
      };
      if (text) {
        m.onChange(text.input, "event-form" + "_" + "text", onChange, 500);
        onChange(text.input.val());
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

    compareVisibility: function (a, b) {
      if (a === b) {
        return false;
      }

      var equals = [undefined, null, "public"];
      if (_.contains(equals, a) && _.contains(equals, b)) {
        return false;
      }

      return true;
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
      $(".date-utc").each(function (el) {
        var $el = $(this);
        var date = new Date($el.text());
        var dateString = $.datepicker.formatDate("yy-mm-dd", new Date(date));
        var timeString = ("0" + date.getHours()).slice(-2) + ":" +
            ("0" + date.getMinutes()).slice(-2) + ":" +
            ("0" + date.getSeconds()).slice(-2);
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
      var $deleteForm = $("input[name='_method'][value='delete']").parent();
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
      [/^\/(home)?$/, function () {
        m.initHome("home-target", "home-org");
        m.initMap(function (mapView) {
          m.initHomeMap(mapView, null);
        });
      }],
      [/^\/dsei$/, function () {
        m.initHome("dsei-target", "dsei-org");
        m.initMap(function (mapView) {
          m.initHomeMap(mapView, "dsei-2015");
        });
      }],
      [/^\/dprte$/, function () {
        m.initHome("dprte-target", "dprte-org");
        m.initMap(function (mapView) {
          m.initHomeMap(mapView, "dprte-2016");
        });
      }],
      [/^\/farnborough$/, function () {
        m.initHome("farnborough-target", "farnborough-org");
        m.initMap(function (mapView) {
          m.initHomeMap(mapView, "farnborough-2014");
        });
      }],
      [/^\/security-and-policing$/, function () {
        m.initHome("security-and-policing-target",
                   "security-and-policing-org");
        m.initMap(function (mapView) {
          m.initHomeMap(mapView, "security-and-policing-2016");
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
          m.initOrgSearchForm(mapView);
          m.visibility();
        });
      }],
      [/^\/event$/, function () {
        m.initMap(function (mapView) {
          m.initEventSearchForm(mapView);
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
        m.initOrg(null);
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
        m.initEvent(null);
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
      [/^\/user\/([1-9][0-9]*)$/, function (userIdString) {
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
        if (path.indexOf(m.urlRoot.substr(0, m.urlRoot.length - 1)) !== 0) {
          console.warn("Path does not match url root", path, m.urlRoot);
        }
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

    var a = document.createElement("a");
    a.href = uri;

    var scheme = a.protocol;
    var schemeIndex = null;
    if (!!scheme) {
      schemeIndex = uri.indexOf(scheme);
      if (schemeIndex !== 0) {
        scheme = null;
        schemeIndex = null;
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
    if (path.length && path.indexOf("/") !== 0) {
      // Internet Explorer returns pathname without '/'
      path = "/" + path;
    }

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
        var key, value;
        if (index === -1) {
          key = segment;
          value = "";
        } else {
          key = segment.substr(0, index);
          value = segment.substr(index + 1);
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
      arguments_.next = urlRewriteStatic(next, root);
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

    var uriOut = "";
    if (scheme) {
      uriOut += scheme + "//";
    }
    if (netloc) {
      uriOut += netloc;
    }
    if (path) {
      uriOut += path;
    }
    if (query) {
      uriOut += "?" + query;
    }
    if (fragment) {
      uriOut += "#" + fragment;
    }

    return uriOut;
  }

  $(window.document).ready(function () {
    m.setCookie("javascript", 1);
    $.ajaxSetup({ "traditional": true });
    m.templator.setUrl(m.urlRewrite("/static/template/"));
    m.handle();
  });

  return m;

})();

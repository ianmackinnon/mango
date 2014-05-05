"use strict";

/*global window, jQuery, _, Backbone, m */

(function ($) {

  // Tag

  window.Tag = Backbone.Model.extend({
    toAutocomplete: function () {
      return {
        value: this.get("base_short"),
        label: this.get("base_short") + " (" + this.get("path") + ")"
      };
    }
  });

  window.Orgtag = window.Tag.extend({
    urlRoot: m.urlRoot + "organisation-tag",
  });

  window.Eventtag = window.Tag.extend({
    urlRoot: m.urlRoot + "event-tag",
  });

  window.OrgtagCollection = Backbone.Collection.extend({
    url: m.urlRoot + "organisation-tag",
    model: window.Orgtag,

    parse: function (response) {
      response = _.sortBy(response, function (tag) {
        return tag["base_short"] + " " + tag["path_short"];
      });
      return response;
    }
  });

  window.EventtagCollection = Backbone.Collection.extend({
    url: m.urlRoot + "event-tag",
    model: window.Eventtag,

    parse: function (response) {
      response = _.sortBy(response, function (tag) {
        return tag["base_short"] + " " + tag["path_short"];
      });
      return response;
    }
  });

  window.tagCollectionSearch = function (tagCollection, search, limit) {
    var start = [];   // search matches start of string
    var middle = [];  // search matches start of word
    var end = [];     // search matches inside of word

    var comparator = function (a, b) {
      var av = a.get("base_short").split("-").length;
      var bv = b.get("base_short").split("-").length;
      if (av < bv) {
        return -1;
      }
      if (av > bv) {
        return 1;
      }
      av = a.get("base_short") + " " + a.get("path_short");
      bv = b.get("base_short") + " " + b.get("path_short");
      if (av < bv) {
        return -1;
      }
      if (av > bv) {
        return 1;
      }
      return 0;
    }
    
    tagCollection.each(function (tag) {
      var index = tag.get("base_short").toLowerCase().indexOf(
        search.term);
      if (index === 0) {
        start.push(tag);
      } else if (index > 0) {
        var index2 = tag.get("base_short").toLowerCase().indexOf(
          "-" + search.term);
        if (index2 > 0) {
          middle.push(tag);
        } else {
          end.push(tag);
        }
      }
    });

    start.sort(comparator);

    if (start.length < limit && middle.length) {
      middle.sort(comparator);
      start = start.concat(middle);
    }

    if (start.length < limit && end.length) {
      end.sort(comparator);
      start = start.concat(end);
    }

    start =  start.slice(0, limit);

    start = _.map(start, function (tag) {
      return tag.toAutocomplete();
    });

    return start;
  }

}(jQuery));

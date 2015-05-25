/*global window, $, _, Backbone, google, History */

var templator = (function () {
  "use strict";

  var t = {

    _templateUrl: null,

    _promiseCache: {},

    setUrl: function (path) {
      if (path.indexOf("/", path.length - 1) === -1) {
        path += "/";
      }
      t._templateUrl = path;
    },

    loadPromise: function (name) {
      var url = t._templateUrl + name;
      var cache = t._promiseCache;

      if (!_.has(cache, name)) {
        var deferred = new $.Deferred();

        $.ajax({
          url: url,
          success: function (response) {
            var f = _.template(response);
            deferred.resolveWith(null, [f]);
          },
          error: function (jqXHR, textStatus, errorThrown) {
            deferred.reject();
          }
        });

        cache[name] = deferred.promise();
      }

      return cache[name];
    },

    load: function (nameList, callback) {
      var deferredList = [];
      _.each(nameList, function (name, i) {
        deferredList.push(t.loadPromise(name));
      });
      if (_.isFunction(callback)) {
        $.when.apply($, deferredList).then(callback);
      }
    },

    process: function (name, f, data, options) {
      try {
        var html = f(data);
      } catch (error) {
        console.error("Template function error: " + name);
        throw error.stack;
      }
      
      html = html.trim();
      
      if (options && _.has(options, "compact") && options.compact) {
        html = html.replace(/>\s+/gm, ">");
        html = html.replace(/\s+</gm, "<");
      }

      return html;
    },

    renderSync: function (name, data, callback, options) {
      t.loadPromise(name).done(function (f) {
        var html = t.process(name, f, data, options);
        if (_.isFunction(callback)) {
          callback(html);
        }
      }).fail(function () {
        console.error("Template load error: " + t._templateUrl + name);
      });
    },

    render: function (name, data, options) {
      // Fails if template is not already loaded.
      var cache = t._promiseCache;
      var promise = cache[name];
      if (!promise) {
        throw new Error("Template '" + name + "' not loaded.");
      }
      var state = promise.state();
      if (state !== "resolved") {
        throw new Error("Template '" + name + "' failed to load: " + state);
      }
      var html;
      promise.done(function (f) {
        html = t.process(name, f, data, options);
      })
      return html;
    }
  };

  return t
  
})();

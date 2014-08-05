var _ = require('underscore');
var jsdom = require("jsdom");
var knownValues = require("./dataUrlRewrite.json");
var document = jsdom.jsdom("");



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



var returnCode = 0;

_.each(knownValues, function (data, i) {
  var inputs = data[0];
  var resultKnown = data[1];

  var resultFound = urlRewriteStatic(
    inputs.uri, inputs.root, inputs.options, inputs.parameters, inputs.next);

  if (resultFound !== resultKnown) {
    console.log("FAIL");
    console.log(inputs);
    console.log(resultFound);
    console.log(resultKnown);
    console.log("");
    returnCode = 1;
  }

});

process.exit(code=returnCode)

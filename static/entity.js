/*global window, jQuery, _, Backbone, google, m */

(function ($) {
  "use strict";

  // Marker

  window.Marker = Backbone.Model.extend();

  window.MarkerViewDot = Backbone.View.extend({
    initialize: function () {
      this.mapView = this.options.mapView;
      this.color = this.options.color;
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
        this.color,
        this.model.get("name"),
        onClick
      );

      return this;
    }
  });

  // Address

  window.AddressViewRow = Backbone.View.extend({
    tagName: "div",
    className: "address-row",
    templateName: "address-row.html",

    initialize: function () {
      this.mapView = this.options.mapView;
      this.color = this.options.color;
    },

    render: function () {
      var view = this;

      m.templator.renderSync(view.templateName, {
        address: view.model.toJSON(),
        m: m,
        parameters: m.parameters
      }, function (html) {
        $(view.el).html(html);

        var $circle = view.mapView.addMarker(
          view.model.get("latitude"),
          view.model.get("longitude"),
          view.color
        );

        var $pin = $("<div class='pin'>").append($circle);
        view.$el.prepend($pin);
      });

      return this;
    }
  });

  window.AddressViewDot = Backbone.View.extend({
    initialize: function () {
      this.mapView = this.options.mapView;
      this.color = this.options.color;
      this.entityName = this.options.entityName;
    },

    render: function () {
      var view = this;

      var onClick = function (event) {
        var href = view.model.collection[view.entityName].get("url");
        window.document.location.href = href;
      };

      view.mapView.addDot(
        view.model.get("latitude"),
        view.model.get("longitude"),
        view.color,
        view.model.collection[view.entityName].get("name"),
        onClick
      );

      return this;
    }
  });

  // Address

  window.AddressCollectionViewRows = Backbone.View.extend({
    tagName: "div",

    className: function () {
      return this.entityName + "_address_list";
    },

    initialize: function () {
      var view = this;

      view.mapView = this.options.mapView;
      view.limit = this.options.limit;
      view.color = this.options.color;
      view.entityName = this.options.entityName;

      this._modelViews = [];
      this.collection.each(function (model) {

        if (!!model.get("latitude") && !view.mapView.contains(
          model.get("latitude"),
          model.get("longitude")
        )) {
          view._modelViews.push(new AddressViewDot({
            model: model,
            mapView: view.mapView,
            entityName: view.entityName,
            color: view.color
          }));
          return;
        }

        if (view.limit.offset <= 0 && view.limit.offset > -view.limit.limit) {
          view._modelViews.push(new AddressViewRow({
            model: model,
            mapView: view.mapView,
            color: view.color
          }));
          view.limit.offset -= 1;
          return;
        }

        view._modelViews.push(new AddressViewDot({
          model: model,
          mapView: view.mapView,
          entityName: view.entityName,
          color: undefined
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

}(jQuery));

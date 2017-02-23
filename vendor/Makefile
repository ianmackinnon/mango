SHELL := /bin/bash
.PHONY := jquery-ui

all :

JS := 
LN := 

define DOWNLOAD
NAME := $(1)
SUBDIR := $(2)
URL := $(3)

$$(NAME) :
	wget $(3) -O $$@ || ( rm -f $$@ && false )

../static/$(2)$(1) : $(1)
	ln -sf $$$$(realpath --relative-to="../static/$(2)" $$^) $$@

JS := $(JS) $(1)
LN := $(LN) ../static/$(2)$(1)
endef


$(eval $(call DOWNLOAD,jquery.3.min.js,, \
	https://code.jquery.com/jquery-3.0.0.min.js))
$(eval $(call DOWNLOAD,underscore-min.js,, \
	https://raw.github.com/documentcloud/underscore/master/underscore-min.js))
$(eval $(call DOWNLOAD,backbone-min.js,, \
	https://raw.github.com/documentcloud/backbone/master/backbone-min.js))
$(eval $(call DOWNLOAD,markerclusterer.js,, \
	https://raw.github.com/googlemaps/js-marker-clusterer/gh-pages/src/markerclusterer.js))

$(eval $(call DOWNLOAD,jquery.ui.timepicker.js,, \
	https://raw.github.com/fgelinas/timepicker/master/jquery.ui.timepicker.js))
$(eval $(call DOWNLOAD,jquery.ui.timepicker.css,, \
	https://raw.github.com/fgelinas/timepicker/master/jquery.ui.timepicker.css))

$(eval $(call DOWNLOAD,tag-it.js,, \
	https://raw.github.com/ianmackinnon/tag-it/master/js/tag-it.js))
$(eval $(call DOWNLOAD,tag-it.css,, \
	https://raw.github.com/ianmackinnon/tag-it/master/css/jquery.tagit.css))

$(eval $(call DOWNLOAD,geolocation.py,../, \
	https://raw.github.com/jfein/PyGeoTools/master/geolocation.py))


# Download the latest jQuery-UI package from <http://jqueryui.com/download/>
# to a temporary location. It should include at least the modules:
#
# -   Autocomplete
# -   Datepicker
# -   Blind Effect
#    
# Expand to vendor directory
#    
#     unzip jquery-ui-*.custom.zip -d vendor
# 

JQUERY_UI_PATH := $(shell ls -1d jquery-ui-*.custom | head -n 1)

jquery-ui :
	echo $(JQUERY_UI_PATH)
	mkdir -p ../static/jquery-ui

../static/jquery-ui/% : ../vendor/$(JQUERY_UI_PATH)/%
	ln -sf ../$^ $@

LN := $(LN) ../static/jquery-ui/images
LN := $(LN) ../static/jquery-ui/jquery-ui.css
LN := $(LN) ../static/jquery-ui/jquery-ui.js
LN := $(LN) ../static/jquery-ui/jquery-ui.min.js


all : $(JS) $(LN)

clean :
	rm -f $(JS)
	for f in $(LN); do unlink $$f || true; done;





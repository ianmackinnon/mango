SHELL := /bin/bash
.PHONY: all jquery

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


all : backbone-min.js underscore-min.js tag-it.js tag-it.css jquery.3.min.js jquery-ui jquery.ui.timepicker.js jquery.ui.timepicker.css geolocation.py markerclusterer.js

backbone-min.js:
	wget https://raw.github.com/documentcloud/backbone/master/backbone-min.js -O $@ || ( rm -f $@ && false )

underscore-min.js:
	wget https://raw.github.com/documentcloud/underscore/master/underscore-min.js -O $@ || ( rm -f $@ && false )

tag-it.js:
	wget https://raw.github.com/ianmackinnon/tag-it/master/js/tag-it.js -O $@ || ( rm -f $@ && false )

tag-it.css:
	wget https://raw.github.com/ianmackinnon/tag-it/master/css/jquery.tagit.css -O $@ || ( rm -f $@ && false )

jquery.3.min.js :
	wget https://code.jquery.com/jquery-3.0.0.min.js -O $@ || ( rm -f $@ && false )
	ln -sf ../vendor/$@ ../static/$@

jquery-ui : JQUERY_UI_PATH := $(shell ls -1d jquery-ui-*.custom | head -n 1)
jquery-ui :
	echo $(JQUERY_UI_PATH)
	mkdir -p ../static/jquery-ui
	ln -sf ../../vendor/$(JQUERY_UI_PATH)/images ../static/jquery-ui/
	ln -sf ../../vendor/$(JQUERY_UI_PATH)/jquery-ui.css ../static/jquery-ui/
	ln -sf ../../vendor/$(JQUERY_UI_PATH)/jquery-ui.js ../static/jquery-ui/
	ln -sf ../../vendor/$(JQUERY_UI_PATH)/jquery-ui.min.js ../static/jquery-ui/

jquery.ui.timepicker.js:
	wget https://raw.github.com/fgelinas/timepicker/master/$@ -O $@ || ( rm -f $@ && false )

jquery.ui.timepicker.css:
	wget https://raw.github.com/fgelinas/timepicker/master/$@ -O $@ || ( rm -f $@ && false )

geolocation.py:
	wget https://raw.github.com/jfein/PyGeoTools/master/geolocation.py -O $@ || ( rm -f $@ && false )

markerclusterer.js:
	false

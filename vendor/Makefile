SHELL := /bin/bash
.PHONY: all jquery

JQUERY_VERSION_LIST = $(shell ls -d jquery-ui-*.custom/js/jquery-[0-9]*.js | grep -o '[0-9.]*[0-9]')
JQUERY_VERSION = $(word 2, $(JQUERY_VERSION_LIST))
JQUERY_UI_VERSION = $(word 1, $(JQUERY_VERSION_LIST))
JQUERY_UI_THEME_PATH = $(shell ls -d jquery-ui-*.custom/css/* | head -1)

all : backbone-min.js underscore-min.js markdown.js tag-it.js tag-it.css jquery jquery.history.js jquery.ui.timepicker.js jquery.ui.timepicker.css geolocation.py markerclusterer.js

backbone-min.js:
	wget https://raw.github.com/documentcloud/backbone/master/backbone-min.js -O $@ || rm -f $@

underscore-min.js:
	wget https://raw.github.com/documentcloud/underscore/master/underscore-min.js -O $@ || rm -f $@

markdown.js:
	wget https://raw.github.com/evilstreak/markdown-js/master/lib/markdown.js -O $@ || rm -f $@

tag-it.js:
	wget https://raw.github.com/ianmackinnon/tag-it/master/js/tag-it.js -O $@ || rm -f $@

tag-it.css:
	wget https://raw.github.com/ianmackinnon/tag-it/master/css/jquery.tagit.css -O $@ || rm -f $@

jquery : jquery-version-check jquery-$(JQUERY_VERSION).min.js ../static/jquery-ui
	ln -sf ../vendor/jquery-$(JQUERY_VERSION).min.js ../static/jquery.min.js
	ln -sf ../vendor/jquery-ui-$(JQUERY_UI_VERSION).custom/js/jquery-$(JQUERY_VERSION).js ../static/jquery.js

	ln -sf ../../vendor/jquery-ui-$(JQUERY_UI_VERSION).custom/js/jquery-ui-$(JQUERY_UI_VERSION).custom.min.js ../static/jquery-ui/jquery-ui.min.js
	ln -sf ../../vendor/jquery-ui-$(JQUERY_UI_VERSION).custom/js/jquery-ui-$(JQUERY_UI_VERSION).custom.js ../static/jquery-ui/jquery-ui.js
	ln -sf ../../vendor/$(JQUERY_UI_THEME_PATH)/jquery-ui-$(JQUERY_UI_VERSION).custom.css ../static/jquery-ui/jquery-ui.css
	ln -sf ../../vendor/$(JQUERY_UI_THEME_PATH)/images ../static/jquery-ui/

jquery-version-check :
	@[ "$$(echo $(JQUERY_VERSION_LIST) | wc -w)" -gt 0 ] || (echo "No jQuery UI version" && false)
	@[ "$$(echo $(JQUERY_VERSION_LIST) | wc -w)" -eq 2 ] || (echo "Too many jQuery UI versions" && false)
	@[ -n "$$(echo $(JQUERY_UI_THEME_PATH))" ] || (echo "No jQuery UI theme path" && false)
	@echo "jQuery:     $(JQUERY_VERSION)"
	@echo "jQuery UI:  $(JQUERY_UI_VERSION)"

../static/jquery-ui:
	mkdir -p ../static/jquery-ui

jquery-$(JQUERY_VERSION).min.js:
	wget http://code.jquery.com/$@ -O $@ || rm -f $@

jquery.history.js:
	wget https://raw.github.com/browserstate/history.js/master/scripts/bundled/html4+html5/jquery.history.js -O $@ || rm -f $@

jquery.ui.timepicker.js:
	wget https://raw.github.com/fgelinas/timepicker/master/$@ -O $@ || rm -f $@

jquery.ui.timepicker.css:
	wget https://raw.github.com/fgelinas/timepicker/master/$@ -O $@ || rm -f $@

geolocation.py:
	wget https://raw.github.com/jfein/PyGeoTools/master/geolocation.py -O $@ || rm -f $@

markerclusterer.js:
	false

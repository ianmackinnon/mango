SHELL := /bin/bash

all : backbone-min.js underscore-min.js tag-it.js tag-it.css jquery.history.js

backbone-min.js:
	wget https://raw.github.com/documentcloud/backbone/master/backbone-min.js -O $@ || rm -f $@

underscore-min.js:
	wget https://raw.github.com/documentcloud/underscore/master/underscore-min.js -O $@ || rm -f $@

tag-it.js:
	wget https://raw.github.com/ianmackinnon/tag-it/master/js/tag-it.js -O $@ || rm -f $@

tag-it.css:
	wget https://raw.github.com/ianmackinnon/tag-it/master/css/jquery.tagit.css -O $@ || rm -f $@

jquery.history.js:
	wget https://raw.github.com/balupton/history.js/master/scripts/bundled/html4+html5/jquery.history.js -O $@ || rm -f $@


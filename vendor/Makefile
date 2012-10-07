SHELL := /bin/bash

all : backbone-min.js underscore-min.js tag-it.js tag-it.css 

backbone-min.js:
	wget https://raw.github.com/documentcloud/backbone/master/backbone-min.js -O $@ || rm -f $@

underscore-min.js:
	wget https://raw.github.com/documentcloud/underscore/master/underscore-min.js -O $@ || rm -f $@

tag-it.js:
	wget https://raw.github.com/aehlke/tag-it/master/js/tag-it.js -O $@ || rm -f $@

tag-it.css:
	wget https://raw.github.com/aehlke/tag-it/master/css/jquery.tagit.css -O $@ || rm -f $@


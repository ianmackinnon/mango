SHELL := /bin/bash
.PHONY : all purge \
	vendor \
	test \
	serve-test \
	lint-py \
	lint-py-error \
	lint-js



all : vendor .xsrf

purge :
	rm -rf .xsrf

vendor:
ifneq (,$(wildcard vendor))
	$(MAKE) -C vendor
endif

.xsrf :
	head -c 32 /dev/urandom | base64 > .xsrf
	chmod o-rwx .xsrf

test : mysql-test serve-test

serve-test :
#	Ignore BS4 File/URL warnings
#	Ignore httplib2 Google app engine install warning
	python \
	  -W error \
	  -W ignore::UserWarning:bs4 \
	  -W ignore::ImportWarning:httplib2 \
	  ./mango.py --local=1 --events=0



# Static analysis

lint : lint-py lint-js

lint-py : lint-py-web lint-py-tools

lint-py-web :
	pylint --rcfile=test/pylintrc \
	  --disable=duplicate-code \
	  conf.py geo.py model.py model_v.py \
	  mango.py handle/*.py \
	  skin/*/*.py

lint-py-tools :
	pylint --rcfile=test/pylintrc \
	  --disable=duplicate-code \
	  conf.py geo.py model.py model_v.py \
	  tools/*.py \

lint-js :
	jshint -c test/jshint.json \
	  static/address.js \
	  static/entity.js \
	  static/org.js \
	  static/event.js \
	  static/map.js \
	  static/mango.js \
	  static/geobox.js \
	  static/tag.js

	jscs -c test/jscs.json -v \
	  static/address.js \
	  static/entity.js \
	  static/org.js \
	  static/event.js \
	  static/map.js \
	  static/mango.js \
	  static/geobox.js \
	  static/tag.js

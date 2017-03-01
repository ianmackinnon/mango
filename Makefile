>SHELL := /bin/bash
.PHONY : all purge \
	vendor \
	test \


NAME := mango
REDIS_NAMESPACE := $(NAME)

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


deps-local :
	make -f deps.Makefile dev


# Cache

drop-cache-live :
	ssh $(LIVE_HOST) -t " \
	  redis-cli keys \"$(REDIS_NAMESPACE):*\" | xargs -n 100 redis-cli DEL; \
	  "

drop-cache :
	-redis-cli keys "$(REDIS_NAMESPACE):*" | xargs -n 100 redis-cli DEL;

# Database

mysql-import :
	$(MAKE) -f mysql.Makefile mysql-import
mysql-test :
	$(MAKE) -f mysql.Makefile mysql-test

# Serve & test


test : mysql-test serve-test

serve-test :
#	Ignore BS4 File/URL warnings
#	Ignore httplib2 Google app engine install warning
	python3 \
	  -W error \
	  -W ignore::UserWarning:bs4 \
	  -W ignore::ImportWarning:httplib2 \
	  -W ignore::ResourceWarning: \
	  ./mango.py --local=1 --events=0 \
	    --log=/tmp/$(NAME)-log

test-web :
	./test/test_web.py -v

test-local :
	HTTP_TEST_HOST=localhost.org:8802 \
	HTTP_TEST_CONF=test/mango.json \
	time ~/jobs/test_http/test_http.py -v   # Change

test-live :
	HTTP_TEST_HOST=https://www.caat.org.uk/resources/mapping \
	HTTP_TEST_CONF=test/mango.json \
	time ~/jobs/test_http/test_http.py -v   # Change


# Static analysis

lint : lint-py lint-js

lint-py : lint-py-web lint-py-test lint-py-tools

lint-py-web :
	python3 -m pylint --rcfile=test/pylintrc \
	  --disable=duplicate-code \
	  geo.py model.py model_v.py \
	  mysql/*.py \
	  mango.py handle/*.py \
	  skin/*/*.py

lint-py-test :
	PYTHONPATH="." python3 -m pylint --rcfile=test/pylintrc \
	  --disable=duplicate-code \
	  test/*.py \

lint-py-tools :
	python3 -m pylint --rcfile=test/pylintrc \
	  --disable=duplicate-code \
	  geo.py model.py model_v.py \
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

	jscs -c test/jscs.json --no-colors \
	  static/address.js \
	  static/entity.js \
	  static/org.js \
	  static/event.js \
	  static/map.js \
	  static/mango.js \
	  static/geobox.js \
	  static/tag.js

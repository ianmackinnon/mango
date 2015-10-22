SHELL := /bin/bash
.PHONY : all clean purge \
	database clean-database purge-database \
	vendor \
	sqlite clean-sqlite purge-sqlite \
	mysql-exist clean-mysql mysql mysql-build-triggers mysql-drop-triggers purge-mysql \
	lint


NAME := mango
TMP := /tmp/$(NAME).tmp
CONF_PATH := .$(NAME).conf
CONF_EXAMPLE_PATH := $(NAME).example.conf
MYSQL_CONF_PATH := .$(NAME).mysql.conf
MYSQLDUMP_CONF_PATH := .$(NAME).mysqldump.conf

SQLITE_DB := $(NAME).db
MYSQL_IMPORT = mysql/import.my.sql
MYSQL_TEST = mysql/test.my.sql

DATE := $(shell date -u '+%Y-%m-%d.%H:%M:%S')
DUMP_NAME := $(NAME).$(DATE).data-only.my.sql


all : .xsrf $(CONF_PATH) database

clean : purge-database

purge :
	rm -rf .xsrf
	rm -rf $(CONF_PATH)

database: mysql
clean-database: clean-mysql
purge-database: purge-mysql

vendor:
	$(MAKE) -C vendor

.xsrf :
	head -c 32 /dev/urandom | base64 > .xsrf
	chmod 600 .xsrf

test : mysql-test serve-test

serve-test :
#	Ignore BS4 File/URL warnings
#	Ignore httplib2 Google app engine install warning
	python \
	  -W error \
	  -W ignore::UserWarning:bs4 \
	  -W ignore::ImportWarning:httplib2 \
	  ./mango.py --local=1 --events=0

# Configuration

$(CONF_PATH) :
	@echo "Create a configuration file:"
	@echo
	@echo "  cp ${CONF_EXAMPLE_PATH} ${CONF_PATH}"
	@echo "  chmod 600 ${CONF_PATH}"
	@echo "  $$EDITOR ${CONF_PATH}  # Add passwords, set options."
	@echo
	@false

# SQLite

sqlite : $(SQLITE_DB)

clean-sqlite:
	rm -rf $(SQLITE_DB)

purge-sqlite:

$(SQLITE_DB) : model.py sqlite/build.sqlite.sql
	rm -rf $(SQLITE_DB)
	./model.py $(SQLITE_DB)
	sqlite3 $(SQLITE_DB) < sqlite/build.sqlite.sql

# MySQL

$(MYSQL_CONF_PATH) : $(CONF_PATH)
	./mysql/mysql.py -g $(CONF_PATH) > $(TMP)
	chmod 600 $(TMP)
	mv $(TMP) $@

$(MYSQLDUMP_CONF_PATH) : $(CONF_PATH)
	./mysql/mysql.py -G $(CONF_PATH) > $(TMP)
	chmod 600 $(TMP)
	mv $(TMP) $@

mysql-exist : $(CONF_PATH)
# Create the database and users if necessary (root)
	./mysql/mysql.py $(CONF_PATH)

clean-mysql : $(CONF_PATH)
# Empty the database (admin)
	./mysql/mysql.py -e $(CONF_PATH)






mysql : $(MYSQL_CONF_PATH) $(MYSQLDUMP_CONF_PATH) mysql-exist clean-mysql
# Empty and rebuild the database (admin)
	./model.py
	mysql --defaults-extra-file=$(MYSQL_CONF_PATH) < mysql/org_include.mysql.sql
	mysql --defaults-extra-file=$(MYSQL_CONF_PATH) < mysql/build.mysql.sql
	mysql --defaults-extra-file=$(MYSQL_CONF_PATH) < mysql/build_triggers.mysql.sql
	mysql --defaults-extra-file=$(MYSQL_CONF_PATH) < mysql/seed.mysql.sql

mysql-import : $(MYSQL_CONF_PATH) $(MYSQLDUMP_CONF_PATH) mysql-exist clean-mysql $(MYSQL_IMPORT)
# Empty and build the mango database from import data (admin)
	./model.py
	mysql --defaults-extra-file=$(MYSQL_CONF_PATH) < mysql/org_include.mysql.sql
	mysql --defaults-extra-file=$(MYSQL_CONF_PATH) < mysql/build.mysql.sql
	mysql --defaults-extra-file=$(MYSQL_CONF_PATH) < "$(MYSQL_IMPORT)"
	mysql --defaults-extra-file=$(MYSQL_CONF_PATH) < mysql/build_triggers.mysql.sql

$(MYSQL_TEST) : $(MYSQL_CONF_PATH) $(MYSQLDUMP_CONF_PATH) mysql/build.mysql.sql mysql/build_triggers.mysql.sql mysql/seed.mysql.sql model.py ./test/seed_data.py 
	make mysql
	./test/seed_data.py
	mysqldump --defaults-extra-file=$(MYSQLDUMP_CONF_PATH) $$(./mysql/mysql.py -k database $(CONF_PATH)) > $(TMP)
	mv $(TMP) $@

mysql-dump : $(MYSQLDUMP_CONF_PATH)
	mysqldump --defaults-extra-file=$(MYSQLDUMP_CONF_PATH) -c --no-create-info --skip-triggers $$(./mysql/mysql.py -k database $(CONF_PATH)) > /tmp/$(DUMP_NAME)
	ln -sf /tmp/$(DUMP_NAME) $(MYSQL_IMPORT)

mysql-test : $(MYSQL_CONF_PATH) $(MYSQLDUMP_CONF_PATH) mysql-exist
# Empty and build the mango database from test data (admin)
	-find $(MYSQL_TEST) -mtime +5 -exec rm {} \;
	make $(MYSQL_TEST)
	mysql --defaults-extra-file=$(MYSQL_CONF_PATH) < "$(MYSQL_TEST)"

mysql-drop-triggers :
# Drops all triggers (admin)
	./mysql/mysql.py -t $(CONF_PATH)

mysql-build-triggers : $(MYSQL_CONF_PATH) $(MYSQLDUMP_CONF_PATH)
# Builds all triggers (admin)
	mysql --defaults-extra-file=$(MYSQL_CONF_PATH) < mysql/build_triggers.mysql.sql

purge-mysql:
# Delete the mango database and users (root)
	./mysql/mysql.py -x $(CONF_PATH)
	rm -rf $(MYSQL_CONF_PATH)


# Static analysis

lint : lint-py lint-js

lint-py :
	pylint --rcfile=test/pylintrc \
	  --disable=duplicate-code \
	  conf.py geo.py mango.py model.py model_v.py \
	  handle/*.py \
	  tools/*.py \
	  skin/*/*.py

lint-py-error :
	pylint --rcfile=test/pylintrc -E\
	  --disable=duplicate-code \
	  conf.py geo.py mango.py model.py model_v.py \
	  handle/*.py \
	  tools/*.py \
	  skin/*/*.py

lint-js :
	jshint \
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

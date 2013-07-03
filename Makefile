SHELL := /bin/bash
.PHONY : all clean purge database clean-database purge-database vendor sqlite clean-sqlite purge-sqlite mysql-exist clean-mysql mysql mysql-build-triggers mysql-drop-triggers purge-mysql lint


MYSQL_IMPORT = "mysql/import.my.sql"
TMP := "/tmp/mango"


all : .xsrf .mango.conf database

clean : purge-database

purge :
	rm -rf .xsrf
	rm -rf .mango.conf

database: mysql
clean-database: clean-mysql
purge-database: purge-mysql

vendor:
	$(MAKE) -C vendor

.xsrf :
	head -c 32 /dev/urandom | base64 > .xsrf
	chmod 600 .xsrf

.mango.conf :
	@echo "Set your configuration in 'mango.example.conf', rename it to '.mango.conf, and chmod it to 600.'." && false

# SQLite

sqlite : mango.db

clean-sqlite:
	rm -rf mango.db

purge-sqlite:

mango.db : model.py sqlite/build.sqlite.sql
	rm -rf mango.db
	./model.py mango.db
	sqlite3 mango.db < sqlite/build.sqlite.sql

# MySQL

.mango.mysql.conf : .mango.conf
	./mysql/mysql.py -g > $(TMP)
	chmod 600 $(TMP)
	mv $(TMP) $@

mysql-exist:
# Create the mango database and users if necessary (root)
	./mysql/mysql.py

clean-mysql:
# Empty the mango database (admin)
	./mysql/mysql.py -e

mysql : .mango.mysql.conf mysql-exist clean-mysql
# Empty and rebuild the mango database (admin)
	./model.py
	mysql --defaults-extra-file=.mango.mysql.conf < mysql/build.mysql.sql
	@([ -f "$(MYSQL_IMPORT)" ] && echo "Importing data" && mysql --defaults-extra-file=.mango.mysql.conf < "$(MYSQL_IMPORT)") || true

	mysql --defaults-extra-file=.mango.mysql.conf < mysql/build_triggers.mysql.sql
	@[ -f "$(MYSQL_IMPORT)" ] || (echo "Seeding data" && mysql --defaults-extra-file=.mango.mysql.conf < mysql/seed.mysql.sql)

mysql-drop-triggers :
# Drops all triggers (admin)
	./mysql/mysql.py -t

mysql-build-triggers :
# Builds all triggers (admin)
	mysql --defaults-extra-file=.mango.mysql.conf < mysql/build_triggers.mysql.sql

purge-mysql:
# Delete the mango database and users (root)
	./mysql/mysql.py -x
	rm -rf .mango.mysql.conf


# Static analysis

lint :
	jslint --indent=2 --nomen --vars --es5=false \
	static/address.js static/org.js static/map.js static/mango.js

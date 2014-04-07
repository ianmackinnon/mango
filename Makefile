SHELL := /bin/bash
.PHONY : all clean purge database clean-database purge-database vendor sqlite clean-sqlite purge-sqlite mysql-exist clean-mysql mysql mysql-build-triggers mysql-drop-triggers purge-mysql lint


MYSQL_IMPORT = mysql/import.my.sql
MYSQL_TEST = mysql/test.my.sql
TMP := /tmp/mango


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
	@echo "Set your configuration in 'mango.example.conf', then rename it to '.mango.conf, and chmod it to 600.'." && false

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

.mango.mysql.conf .mango.mysqldump.conf : .mango.conf
	./mysql/mysql.py -g > $(TMP)
	chmod 600 $(TMP)
	mv $(TMP) .mango.mysql.conf
	./mysql/mysql.py -g | grep -v "database=" > $(TMP)
	chmod 600 $(TMP)
	mv $(TMP) .mango.mysqldump.conf

mysql-exist:
# Create the mango database and users if necessary (root)
	./mysql/mysql.py

clean-mysql:
# Empty the mango database (admin)
	./mysql/mysql.py -e

mysql : .mango.mysql.conf mysql-exist clean-mysql
# Empty and build a fresh mango database (admin)
	./model.py
	mysql --defaults-extra-file=.mango.mysql.conf < mysql/org_include.mysql.sql
	mysql --defaults-extra-file=.mango.mysql.conf < mysql/build.mysql.sql
	mysql --defaults-extra-file=.mango.mysql.conf < mysql/build_triggers.mysql.sql
	mysql --defaults-extra-file=.mango.mysql.conf < mysql/seed.mysql.sql

mysql-import : .mango.mysql.conf mysql-exist clean-mysql $(MYSQL_IMPORT)
# Empty and build the mango database from import data (admin)
	./model.py
	mysql --defaults-extra-file=.mango.mysql.conf < mysql/org_include.mysql.sql
	mysql --defaults-extra-file=.mango.mysql.conf < mysql/build.mysql.sql
	mysql --defaults-extra-file=.mango.mysql.conf < "$(MYSQL_IMPORT)"
	mysql --defaults-extra-file=.mango.mysql.conf < mysql/build_triggers.mysql.sql

$(MYSQL_TEST) : mysql/build.mysql.sql mysql/build_triggers.mysql.sql mysql/seed.mysql.sql model.py ./test/seed_data.py 
	make mysql
	./test/seed_data.py
	mysqldump --defaults-extra-file=.mango.mysqldump.conf $$(./mysql/mysql.py -k database) > $(TMP)
	mv $(TMP) $@

mysql-test : .mango.mysql.conf mysql-exist $(MYSQL_TEST)
# Empty and build the mango database from test data (admin)
	mysql --defaults-extra-file=.mango.mysql.conf < "$(MYSQL_TEST)"

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

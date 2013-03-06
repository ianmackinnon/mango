SHELL := /bin/bash
.PHONY : all clean database clean-database vendor sqlite clean-sqlite mysql mysql-build mysql-import mysql-triggers mysql-seed clean-mysql lint


MYSQL_IMPORT = "mysql/import.my.sql"


all : .xsrf seed database

clean : clean-database
	rm -rf mango.db
	rm -rf .xsrf

database: mysql
clean-database: clean-mysql

vendor:
	$(MAKE) -C vendor

.xsrf :
	head -c 32 /dev/urandom | base64 > .xsrf
	chmod 600 .xsrf

# SQLite

sqlite : mango.db

clean-sqlite:
	rm -rf mango.db

mango.db : model.py sqlite/build.sqlite.sql
	rm -rf mango.db
	./model.py mango.db
	sqlite3 mango.db < sqlite/build.sqlite.sql

# MySQL

mysql : mysql-build mysql-import mysql-triggers mysql-seed

mysql-build:
	@./mysql/mysql_init.py > /dev/null
	@echo "Logging into MySQL as user 'root'"
	@./mysql/mysql_init.py | mysql -u root -p
	./model.py
	@cat \
	  mysql/build.mysql.sql \
	 | mysql -u root -p -D $$(./mysql/mysql_init.py -d database)

mysql-import:
	@([ -f "$(MYSQL_IMPORT)" ] && mysql -u root -p -D $$(./mysql/mysql_init.py -d database) < "$(MYSQL_IMPORT)") || true

mysql-triggers:
	@cat \
	  mysql/build_triggers.mysql.sql \
	 | mysql -u root -p -D $$(./mysql/mysql_init.py -d database)

mysql-seed:
	@([ -f "$(MYSQL_IMPORT)" ] || @cat \
	  mysql/seed.mysql.sql \
	 | mysql -u root -p -D $$(./mysql/mysql_init.py -d database))

clean-mysql:
	@./mysql/mysql_init.py > /dev/null
	@echo "Logging into MySQL as user 'root'"
	@./mysql/mysql_init.py -x | mysql -u root -p

# Static analysis

lint :
	jslint --indent=2 --nomen --vars \
	static/address.js static/org.js static/map.js static/mango.js

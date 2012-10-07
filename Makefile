SHELL := /bin/bash
.PHONY : all clean seed sqlite mysql clean-sqlite clean-mysql clean-database vendor

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


sqlite : mango.db

clean-sqlite:
	rm -rf mango.db

mango.db : model.py sqlite/build.sqlite.sql
	rm -rf mango.db
	./model.py mango.db
	sqlite3 mango.db < sqlite/build.sqlite.sql

mysql : mysql-build mysql-triggers mysql-seed

mysql-build:
	@./mysql/mysql_init.py > /dev/null
	@echo "Logging into MySQL as user 'root'"
	@./mysql/mysql_init.py | mysql -u root -p
	./model.py
	@cat \
	  mysql/build.mysql.sql \
	 | mysql -u root -p -D $$(./mysql/mysql_init.py -d database)

mysql-triggers:
	@cat \
	  mysql/build_triggers.mysql.sql \
	 | mysql -u root -p -D $$(./mysql/mysql_init.py -d database)

mysql-seed:
	@cat \
	  mysql/seed.mysql.sql \
	 | mysql -u root -p -D $$(./mysql/mysql_init.py -d database)

clean-mysql:
	@./mysql/mysql_init.py > /dev/null
	@echo "Logging into MySQL as user 'root'"
	@./mysql/mysql_init.py -x | mysql -u root -p

seed :
	if [ -e seed.bash ]; then ./seed.bash; fi


lint :
	jslint --indent=2 --nomen --vars static/org.js
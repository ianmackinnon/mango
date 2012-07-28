SHELL := /bin/bash
.PHONY : all clean seed sqlite mysql clean-sqlite clean-mysql clean-database

all : .xsrf seed database

clean : clean-database
	rm -rf mango.db
	rm -rf .xsrf

database: mysql
clean-database: clean-mysql



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

mysql : 
	@./mysql/mysql_init.py > /dev/null
	@echo "Logging into MySQL as user 'root'"
	@./mysql/mysql_init.py | mysql -u root -p
	./model.py
	@cat \
	  <(echo "use $$(./mysql/mysql_init.py -d database) ;") \
	  mysql/build.mysql.sql | mysql -u root -p

clean-mysql:
	@./mysql/mysql_init.py > /dev/null
	@echo "Logging into MySQL as user 'root'"
	@./mysql/mysql_init.py -c | mysql -u root -p

seed :
	if [ -e seed.bash ]; then ./seed.bash; fi



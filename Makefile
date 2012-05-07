SHELL := /bin/bash
.PHONY : all clean

all : arms-map.db .xsrf



.xsrf :
	head -c 32 /dev/urandom | base64 > .xsrf
	chmod 600 .xsrf



arms-map.db : model.py build.sqlite.sql
	rm -rf arms-map.db
	./model.py arms-map.db
	sqlite3 arms-map.db < build.sqlite.sql


clean :
	rm -rf arms-map.db
	rm -rf .xsrf


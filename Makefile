SHELL := /bin/bash
.PHONY : all clean

all : mango.db .xsrf



.xsrf :
	head -c 32 /dev/urandom | base64 > .xsrf
	chmod 600 .xsrf



mango.db : model.py build.sqlite.sql
	rm -rf mango.db
	./model.py mango.db
	sqlite3 mango.db < build.sqlite.sql


clean :
	rm -rf mango.db
	rm -rf .xsrf


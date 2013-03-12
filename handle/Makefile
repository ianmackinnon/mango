SHELL := /bin/bash
.PHONY : all lint

all :

# Static analysis

lint :
	pylint --disable R,C,W,E,F -r n -e E0602,W0611,W0612,W0613,W0614 \
	base_tag orgtag.py eventtag.py

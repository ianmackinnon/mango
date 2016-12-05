SHELL := /bin/bash
.PHONY : all \
	dev \
	deps-linux deps-python \
	deps-linux-dev deps-python-dev


ifneq (,$(wildcard /opt/python3-webapps))  # If we're on the server
PIP_CMD := sudo -H -u www-caat-webapps /opt/python3-webapps/bin/pip
else
PIP_CMD := sudo -H pip3
endif


DEBIAN := \
	libxml2-dev libxslt1-dev \
	python3 python3-pip python3-dev \
	sqlite3 libsqlite3-dev \
	mysql-client mysql-server libmysqlclient-dev \
	redis-server redis-tools \
	default-jre-headless

DEBIAN_DEV := \
	pylint \
	expect \
	nodejs \
	npm

PYTHON := \
	pip \
	beautifulsoup4 \
	bleach \
	geopy \
	httplib2 \
	lxml \
	mako \
	markdown \
	pyelasticsearch \
	pymysql \
	python-levenshtein \
	redis \
	requests \
	sqlalchemy \
	tornado

PYTHON_DEV := 

PIP_ARGS := install --upgrade --src=/tmp


all : deps-linux deps-python

dev : all deps-linux-dev deps-python-dev

deps-linux :
	sudo apt install $(DEBIAN)

deps-linux-dev :
	sudo apt install $(DEBIAN_DEV)
	sudo update-alternatives --install /usr/bin/node nodejs /usr/bin/nodejs 100

deps-python :
	$(PIP_CMD) $(PIP_ARGS) $(PYTHON)

deps-python-dev :
	$(PIP_CMD) $(PIP_ARGS) $(PYTHON_DEV)

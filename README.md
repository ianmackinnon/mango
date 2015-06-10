# Mango

Mapping Application for NGOs


## Installation


### Package dependencies (Ubuntu)

    sudo apt-get install \
      python python-dev \
      python-setuptools sqlite3 libsqlite3-dev \
      redis-server mysql-server mysql-client libmysqlclient-dev \
      nodejs npm pylint
      
    sudo update-alternatives --install /usr/bin/node nodejs /usr/bin/nodejs 100

    sudo apt-get install openjdk-7-jre-headless
    # download elasticsearch deb from http://www.elasticsearch.org/download
    sudo dpkg -i elasticsearch-0...
    
On the CAAT server

-   Select virtual Python with `source ~ian.mackinnon/bin/python-webapps`
-   Don't run pip with `sudo`
-   Install build tools first with `~ian.mackinnon/bin/install-compilers`
-   Uninstall build tools later with `~ian.mackinnon/bin/uninstall-compilers`

    sudo -H \
      pip install --upgrade \
      pip \
      Mako tornado \
      BeautifulSoup BeautifulSoup4 \
      markdown bleach \
      sqlalchemy pysqlite \
      mysql-python \
      redis pyelasticsearch \
      python-levenshtein \
      httplib2 geopy


### Node

    sudo npm install -g jslint jscs


### 3rd party static content

Download the latest jQuery-UI package from <http://jqueryui.com/download/> to a temporary location. It should include at least the modules:

-   Autocomplete
-   Datepicker
-   Blind Effect
    
Expand to vendor directory
    
    unzip jquery-ui-*.custom.zip -d vendor


### Build

Now make:

    make

And follow any instructions


## Launch

    ./mango.py


### Inserting Organisation JSON

Example:

    ./tools/insert_organisations.py /tmp/dsei-2015.json

MySQL

    select count(*) from org_orgtag join orgtag using (orgtag_id) where base_short = "dsei-2015";
    

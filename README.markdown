# Mango

Mapping Application for NGOs


## Installation


### Package dependencies (Ubuntu)

    sudo apt-get install python-setuptools sqlite3 libsqlite3-dev \
      redis-server mysql-server mysql-client libmysqlclient-dev \
      nodejs npm pylint

If you're using a virtual Python environment, repace 'pip' below with the path to your virtual environment's pip path.

    sudo pip install \
      Mako tornado sqlalchemy markdown redis pysqlite BeautifulSoup4 \
      python-levenshtein mysql-python python-memcached BeautifulSoup \
      httplib2 MySQLdb pyelasticsearch geopy

    sudo npm install -g jslint

    sudo apt-get install openjdk-7-jre-headless
    # download elasticsearch deb from http://www.elasticsearch.org/download
    sudo dpkg -i elasticsearch-0...


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

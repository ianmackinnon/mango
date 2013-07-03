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
      httplib2 MySQLdb pyelasticsearch

Install 'geopy' from the GitHub repository, because we need Google Maps API v3 support which is not yet in the release version.

    sudo pip install https://github.com/geopy/geopy/tarball/master
      
    sudo npm install -g jslint


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

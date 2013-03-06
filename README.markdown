# Mango

Mapping Application for NGOs

## Installation

### Package dependencies (Ubuntu)

    sudo apt-get install python-setuptools sqlite3 libsqlite3-dev \
      redis-server mysql-server mysql-client libmysqlclient-dev \
      nodejs npm

    sudo pip install \
      Mako tornado sqlalchemy geopy markdown redis pysqlite BeautifulSoup4 \
      python-levenshtein mysql-python python-memcached BeautifulSoup \
      httplib2
      
    sudo npm install -g jslint

### 3rd party static content

Download the latest jQuery-UI package from <http://jqueryui.com/download/> to a temporary location. It should include at least the modules:

-   Autocomplete
-   Datepicker
-   Blind Effect
    
Expand to vendor directory
    
    unzip jquery-ui-*.custom.zip -d vendor

Now make:

    make

    ./mango.py

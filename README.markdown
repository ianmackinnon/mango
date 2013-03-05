# Mango

Mapping Application for NGOs

## Installation instructions (Ubuntu)

    sudo apt-get install python-setuptools sqlite3 libsqlite3-dev \
      redis-server mysql-server mysql-client libmysqlclient-dev \
      nodejs npm

    sudo pip install \
      mako tornado sqlalchemy geopy markdown redis pysqlite BeautifulSoup4 \
      python-levenshtein mysql-python python-memcached BeautifulSoup \
      httplib2
      
    sudo npm install -g jslint

Download jQuery and jQuery-UI including at least the modules:

-   Autocomplete
-   Date Picker

Expand and link
    
    mkdir -p vendor

    unzip jquery-ui-*.custom.zip -d vendor

    set $(ls vendor/jquery-ui*.custom/js/jquery-[0-9]*.js | grep -o '[0-9.]*[0-9]')
    jquiv=$1; echo $jquiv;
    jqv=$2; echo $jqv;

    wget -P vendor http://code.jquery.com/jquery-${jqv}.min.js

    mkdir -p static/jquery-ui
    mkdir -p static/image

    pushd static
    ln -sf ../vendor/jquery-${jqv}.min.js jquery.min.js
    ln -sf ../vendor/jquery-ui-${jquiv}.custom/js/jquery-${jqv}.js jquery.js
    pushd jquery-ui
    ln -sf ../../vendor/jquery-ui-${jquiv}.custom/js/jquery-ui-${jquiv}.custom.min.js jquery-ui.min.js
    ln -sf ../../vendor/jquery-ui-${jquiv}.custom/js/jquery-ui-${jquiv}.custom.js jquery-ui.js
    ln -sf ../../vendor/jquery-ui-${jquiv}.custom/css/*/jquery-ui-${jquiv}.custom.css jquery-ui.css
    ln -sf ../../vendor/jquery-ui-${jquiv}.custom/css/*/images images
    popd
    popd
    
    
Now make:

    make

    ./mango.py

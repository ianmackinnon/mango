# Mango

Mapping Application for NGOs

## Installation instructions (Ubuntu)

    sudo apt-get install python-setuptools sqlite3 libsqlite3-dev \
      redis-server mysql-server mysql-client libmysqlclient-dev \
      node npm

    sudo pip install \
      mako tornado sqlalchemy geopy markdown redis pysqlite BeautifulSoup4 \
      python-levenshtein mysql-python python-memcached BeautifulSoup
      
    sudo npm install -g jslint

    make

    ./mango.py
# Mango

Mapping Application for NGOs

## Installation instructions (Ubuntu)

    sudo apt-get install python-setuptools sqlite3 libsqlite3-dev \
      redis-server mysql-server mysql-client libmysqlclient-dev

    sudo pip install \
      mako tornado sqlalchemy geopy markdown redis pysqlite BeautifulSoup4 \
      python-levenshtein mysql-python python-memcached

    make

    ./mango.py
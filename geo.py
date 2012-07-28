# -*- coding: utf-8 -*-

import re
import json
import time
import redis
import geopy
import logging

from urllib2 import URLError
from hashlib import md5



log = logging.getLogger('geo')
log.addHandler(logging.StreamHandler())



geocoder = geopy.geocoders.Google(domain='maps.google.co.uk')
redis_server = redis.Redis("localhost")
wait = 0.0


exclude = [
    "po box",
    "p o box",
    "p.o. box",
    "p. o. box",
    ]


def geocode(address, use_cache=True):
    global wait

    address = re.sub("\s+", " ", address)
    address = address.strip()
    address = re.sub("[^\w\s]+", "", address)
    key = "geo:%s" % md5(address).hexdigest()

    if use_cache:
        value = None
        try:
            value = redis_server.get(key)
        except redis.ConnectionError as e:
            log.warning("Connection to redis server on localhost failed.")
            pass
            
        if value:
            try:
                return json.loads(value)
            except ValueError:
                log.debug("Could not decode JSON.")

    while True:
        if wait:
            print "Waiting: %.3f" % wait
            time.sleep(wait)
        for term in exclude:
            if term in address.lower():
                return None
        try:
            address, (latitude, longitude) = \
                geocoder.geocode(address.encode("utf-8"))
        except geopy.geocoders.google.GQueryError as e:
            print e
            return None
        except geopy.geocoders.google.GTooManyQueriesError as e:
            wait += 1
            continue
        except URLError as e:
            return None
        except ValueError as e:
            return None
        
        value = json.dumps((latitude, longitude))
        try:
            redis_server.set(key, value)
        except redis.ConnectionError as e:
            log.warning("Connection to redis server on localhost failed.")
            pass
        wait = max(0, wait - .1)
        break
        
    return (latitude, longitude)

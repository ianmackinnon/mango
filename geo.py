# -*- coding: utf-8 -*-

import re
import redis
import geopy
import json
import logging

from urllib2 import URLError
from hashlib import md5



log = logging.getLogger('geo')
log.addHandler(logging.StreamHandler())



geocoder = geopy.geocoders.Google()
redis_server = redis.Redis("localhost")



def geocode(address, use_cache=True):
    address = re.sub("\s+", " ", address)
    address = address.strip()
    address = re.sub("[^\w\s]+", "", address)
    key = "geo:%s" % md5(address).hexdigest()

    if use_cache:
        value = redis_server.get(key)
        if value:
            try:
                return json.loads(value)
            except ValueError:
                log.debug("Could not decode JSON.")
        
    try:
        address, (latitude, longitude) = geocoder.geocode(address.encode("utf-8"))
    except geopy.geocoders.google.GQueryError as e:
        print e
        return None
    except URLError as e:
        return None
    except ValueError as e:
        return None
    
    value = json.dumps((latitude, longitude))
    redis_server.set(key, value)

    return (latitude, longitude)

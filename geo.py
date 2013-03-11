# -*- coding: utf-8 -*-

import re
import sys
import json
import time
import redis
import geopy
import urllib
import logging
import httplib2

from urllib2 import URLError
from hashlib import md5



log = logging.getLogger('geo')
log.addHandler(logging.StreamHandler())



http = httplib2.Http(cache=None)
geocoder = geopy.geocoders.GoogleV3(domain='maps.google.co.uk')
redis_server = redis.Redis("localhost")
wait = 0.0
attempts = 3



exclude = [
    "po box",
    "p o box",
    "p.o. box",
    "p. o. box",
    ]



def _latitude(lat):
    lat = float(lat)
    if lat < -90:
        raise ValueError(u"%0.3f: Latitude below -90°", lat)
    if lat > 90:
        raise ValueError(u"%0.3f: Latitude above 90°", lat)
    return lat



def _longitude(lon):
    lon = float(lon)
    if lon < -180:
        raise ValueError(u"%0.3f: Longitude below -180°", lon)
    if lon > 180:
        raise ValueError(u"%0.3f: Longitude above 180°", lon)
    return lon



class Geobox(object):
    def __init__(self, *args, **kwargs):
        self.name = None
        if "name" in kwargs:
            self.name = kwargs["name"]
        if len(args) == 4:
            self.set_from_coords(*args)
            return
        elif len(args) == 1:
            if isinstance(args[0], Geobox):
                self.set_from_geobox(args[0])
                return
            elif isinstance(args[0], basestring):
                self.set_from_string(args[0])
                return
        raise ValueError("Geobox accepts four coordinates or a Geobox.")

    def set_from_coords(self, south, north, west, east):
        self.south = _latitude(south)
        self.north = _latitude(north)
        self.west = _longitude(west)
        self.east = _longitude(east)

    def set_from_geobox(self, other):
        self.set_from_coords(
            other.south, other.north, other.west, other.east)
        self.name = other.name

    def set_from_string(self, s):
        coords = s.split(",")
        if not len(coords) == 4:
            raise ValueError("Geobox string must be four comma-separated numbers.")
        self.set_from_coords(*coords)

    def to_obj(self):
        obj = {
            "south": self.south,
            "north": self.north,
            "east": self.east,
            "west": self.west,
            }
        if self.name:
            obj["name"] = self.name
        return obj

    def to_json(self):
        return json.dumps(self.to_obj)

    def to_string(self):
        return "%f,%f,%f,%f" % (
            self.south, self.north, self.west, self.east)

    def __str__(self):
        return "<Geobox%s %.2f,%.2f %.2f,%.2f>" % (
            self.name and (" '" + self.name[:16] + "'") or "",
            self.south, self.north, self.west, self.east)



def clean_address(address):
    address = re.sub("\s+", " ", address)
    address = address.strip()
    address = re.sub("[^\w\s]+", "", address)
    address = address.lower()
    return address



def coords(address, cache=True):
    global wait

    address = clean_address(address)

    key = "geo:coords:%s" % md5(address).hexdigest()

    if cache:
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

    for attempt in xrange(attempts):
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
            print e
            wait += 1
            continue
        except geopy.geocoders.base.GeocoderError as e:
            print e
            return None
        except URLError as e:
            print e
            return None
        except ValueError as e:
            print e
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



def bounds(address_full, cache=True, domain='maps.google.co.uk'):
    global wait
    
    address = clean_address(address_full)

    key = "geo:bounds:%s" % md5(address).hexdigest()

    if cache:
        value = None
        try:
            value = redis_server.get(key)
        except redis.ConnectionError as e:
            log.warning("Connection to redis server on localhost failed.")
            pass
            
        if value:
            try:
                bounds = Geobox(value)
                value.name = address_full
                return bounds
            except ValueError:
                log.debug("Could not decode Redis value '%s' to Geobox." % value)

    for attempt in xrange(attempts):
        if wait:
            log.info("Waiting: %.3f" % wait)
            time.sleep(wait)

        parameters = urllib.urlencode({
                "sensor": "false",
                "address": address,
                })

        url = u"http://maps.googleapis.com/maps/api/geocode/json?%s" % parameters
        response, content = http.request(url)

        if response.status != 200:
            continue

        content = json.loads(content)

        if content["status"] != "OK":
            return None

        content = content["results"][0]["geometry"]
        viewport = content["viewport"]
        bounds = Geobox(
                viewport["southwest"]["lat"],
                viewport["northeast"]["lat"],
                viewport["southwest"]["lng"], 
                viewport["northeast"]["lng"]
                )

        value = bounds

        try:
            redis_server.set(key, value.to_string)
        except redis.ConnectionError as e:
            log.warning("Connection to redis server on localhost failed.")
            pass

        bounds.name = address_full

        wait = max(0, wait - .1)
        break
        
    return bounds

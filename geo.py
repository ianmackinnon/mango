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

from geolocation import GeoLocation



log = logging.getLogger('geo')
log.addHandler(logging.StreamHandler())



http = httplib2.Http(cache=None)
geocoder = geopy.geocoders.GoogleV3()
redis_server = redis.Redis("localhost")
wait = 0.0
attempts = 3
geocode_cache_default = True
# https://developers.google.com/maps/documentation/geocoding/#RegionCodes
geocode_default_region = "uk"



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
        self.long_name = None
        self.type_ = None
        if "name" in kwargs:
            self.name = kwargs["name"]
        if "long_name" in kwargs:
            self.long_name = kwargs["long_name"]
        if "type" in kwargs:
            self.type_ = kwargs["type"]
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

    def latitude(self):
        return (self.north + self.south) / 2

    def longitude(self):
        average = (self.west + self.east) / 2
        if self.is_inverse():
            average += 180
            if average > 360:
                average -= 360
        return average

    def is_inverse(self):
        return self.west > self.east

    def west_east_right(self):
        if not self.is_inverse():
            return self.west, self.east
        if self.longitude > 0:
            return self.west, self.east + 360
        return self.west - 360, self.east

    def set_from_coords(self, south, north, west, east):
        self.south = _latitude(south)
        self.north = _latitude(north)
        self.west = _longitude(west)
        self.east = _longitude(east)

    def set_from_geobox(self, other):
        self.set_from_coords(
            other.south, other.north, other.west, other.east)
        self.name = other.name
        self.long_name = other.long_name
        self.type_ = other.type_

    def set_from_string(self, s):
        coords = s.split(",")
        if not len(coords) == 4:
            raise ValueError("Geobox string must be four comma-separated numbers.")
        self.set_from_coords(*coords)

    def to_obj(self):
        obj = {
            "south": self.south,
            "north": self.north,
            "west": self.west,
            "east": self.east,
            }
        if self.name:
            obj["name"] = self.name
        if self.long_name:
            obj["longName"] = self.long_name
        if self.type_:
            obj["type"] = self.type_
        return obj

    @staticmethod
    def from_obj(obj):
        geobox = Geobox(
            obj.get("south", None),
            obj.get("north", None),
            obj.get("west", None),
            obj.get("east", None),
            )
        geobox.name = obj.get("name", None);
        geobox.long_name = obj.get("longName", None);
        geobox.type_ = obj.get("type", None);
        return geobox

    def to_json(self):
        json_text = json.dumps(self.to_obj())
        return json_text

    @staticmethod
    def from_json(text):
        obj = json.loads(text)
        return Geobox.from_obj(obj)

    def to_string(self):
        return "%f,%f,%f,%f" % (
            self.south, self.north, self.west, self.east)

    def __str__(self):
        return "<Geobox%s %.2f,%.2f %.2f,%.2f>" % (
            self.name and (" '" + self.name[:16] + "'") or "",
            self.south, self.north, self.west, self.east)

    def set_min_radius(bounds, radius=None):
        # Radius in Km
        if radius is None:
            return
        bbox = GeoLocation.from_degrees(bounds.latitude(), bounds.longitude()).bounding_locations(radius)
        bounds.south = min(bounds.south, bbox[0].deg_lat)
        bounds.north = max(bounds.north, bbox[1].deg_lat)
        bounds.west = min(bounds.west, bbox[0].deg_lon)
        bounds.east = max(bounds.east, bbox[1].deg_lon)



def clean_address(address):
    address = re.sub("\s+", " ", address)
    address = address.strip()
    address = re.sub("[^\w\s]+", "", address)
    address = address.lower()
    return address



def coords(address, cache=geocode_cache_default):
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
            address, (latitude, longitude) = geocoder.geocode(
                address.encode("utf-8"),
                # https://developers.google.com/maps/documentation/geocoding/#RegionCodes
                region=geocode_default_region,  
                )
        except geopy.geocoders.googlev3.GeocoderQueryError as e:
            print e
            return None
        except geopy.geocoders.googlev3.GeocoderQuotaExceeded as e:
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



def bounds(address_full, min_radius=None, cache=geocode_cache_default):
    global wait
    bounds = None
    
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
                bounds = Geobox.from_json(value)
                bounds.name = address_full
                bounds.set_min_radius(min_radius)
            except ValueError:
                log.debug("Could not decode Redis value '%s' to Geobox." % value)

    for attempt in xrange(attempts):
        if wait:
            log.info("Waiting: %.3f" % wait)
            time.sleep(wait)

        parameters = urllib.urlencode({
                "sensor": "false",
                "address": address,
                "region": geocode_default_region,
                })

        url = u"http://maps.googleapis.com/maps/api/geocode/json?%s" % parameters
        response, content = http.request(url)

        if response.status != 200:
            continue

        content = json.loads(content)

        if content["status"] != "OK":
            return None

        long_name = None
        type_ = None
        for component in content["results"][0]["address_components"]:
            type_set = set(["postal_code", "political"]) & set(component["types"])
            if type_set:
                long_name = component["long_name"]
                type_ = type_set.pop()
                break;
        geometry = content["results"][0]["geometry"]
        viewport = geometry["viewport"]
        bounds = Geobox(
                viewport["southwest"]["lat"],
                viewport["northeast"]["lat"],
                viewport["southwest"]["lng"], 
                viewport["northeast"]["lng"]
                )

        value = bounds

        bounds.long_name = long_name
        bounds.type_ = type_

        try:
            redis_server.set(key, value.to_json())
        except redis.ConnectionError as e:
            log.warning("Connection to redis server on localhost failed.")
            pass

        bounds.name = address_full

        wait = max(0, wait - .1)
        break

    if bounds:
        bounds.set_min_radius(min_radius)
    return bounds

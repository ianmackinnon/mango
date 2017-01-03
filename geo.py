
import re
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import logging
import socket
from hashlib import md5

import redis
import geopy
import requests

from geolocation import GeoLocation



LOG = logging.getLogger('geo')
LOG.addHandler(logging.StreamHandler())



GEOCODER = geopy.geocoders.GoogleV3()
REDIS_SERVER = redis.Redis("localhost")
WAIT = 0.0
ATTEMPTS = 3
GEOCODE_CACHE_DEFAULT = True
# https://developers.google.com/maps/documentation/geocoding/#RegionCodes
GEOCODE_DEFAULT_REGION = "uk"



EXCLUDE = [
    "po box",
    "p o box",
    "p.o. box",
    "p. o. box",
    ]



def _latitude(lat):
    lat = float(lat)
    if lat < -90:
        raise ValueError("%0.3f: Latitude below -90°", lat)
    if lat > 90:
        raise ValueError("%0.3f: Latitude above 90°", lat)
    return lat



def _longitude(lon):
    lon = float(lon)
    if lon < -180:
        raise ValueError("%0.3f: Longitude below -180°", lon)
    if lon > 180:
        raise ValueError("%0.3f: Longitude above 180°", lon)
    return lon



class Geobox(object):
    def __init__(self, *args, **kwargs):
        self.name = None
        self.long_name = None
        self.type_ = None

        self.south = None
        self.north = None
        self.west = None
        self.east = None

        if "name" in kwargs:
            self.name = kwargs["name"]
        if "long_name" in kwargs:
            self.long_name = kwargs["long_name"]
        if "type" in kwargs:
            self.type_ = kwargs["type"]
        if len(args) == 4:
            (south, north, west, east) = args
            self.set_from_coords(south, north, west, east)
            return

        elif len(args) == 1:
            if isinstance(args[0], Geobox):
                self.set_from_geobox(args[0])
                return
            elif isinstance(args[0], str):
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
        parts = s.split(",")
        if len(parts) != 4:
            raise ValueError(
                "Geobox string must be four comma-separated numbers.")
        self.set_from_coords(*parts)

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
        geobox.name = obj.get("name", None)
        geobox.long_name = obj.get("longName", None)
        geobox.type_ = obj.get("type", None)
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

    def set_min_radius(self, radius=None):
        # Radius in Km
        if radius is None:
            return
        bbox = GeoLocation.from_degrees(
            self.latitude(), self.longitude()
        ).bounding_locations(radius)
        self.south = min(self.south, bbox[0].deg_lat)
        self.north = max(self.north, bbox[1].deg_lat)
        self.west = min(self.west, bbox[0].deg_lon)
        self.east = max(self.east, bbox[1].deg_lon)



def clean_address(address):
    address = re.sub(r"\s+", " ", address)
    address = address.strip()
    address = re.sub(r"[^\w\s]+", "", address)
    address = address.lower()
    return address



def geo_key(category, value):
    return "geo:%s:%s" % (
        category,
        md5(value.encode("utf-8")).hexdigest()
    )



def coords(address, cache=GEOCODE_CACHE_DEFAULT):
    # pylint: disable=too-many-return-statements
    global WAIT

    address = clean_address(address)

    key = geo_key("coords", address)

    if cache:
        value = None
        try:
            value = REDIS_SERVER.get(key)
        except redis.ConnectionError as e:
            LOG.warning("Connection to redis server on localhost failed.")

        if value:
            value = value.decode("utf-8")
            try:
                return json.loads(value)
            except ValueError:
                LOG.debug("Could not decode JSON.")

    attempts = ATTEMPTS
    while attempts:
        # pylint: disable=unpacking-non-sequence
        attempts -= 1

        if WAIT:
            LOG.info("Waiting: %.3f", WAIT)
            time.sleep(WAIT)
        for term in EXCLUDE:
            if term in address.lower():
                return None
        try:
            result = GEOCODER.geocode(
                address,
                region=GEOCODE_DEFAULT_REGION,
                )
        except geopy.exc.GeocoderUnavailable as e:
            print(e)
            return None
        except geopy.exc.GeocoderQueryError as e:
            print(e)
            return None
        except geopy.exc.GeocoderQuotaExceeded as e:
            print(e)
            WAIT += 1
            continue
        except urllib.error.URLError as e:
            print(e)
            return None
        except ValueError as e:
            print(e)
            return None
        if result is None:
            print("No address found for %s." % repr(address))
            return None

        address, (latitude, longitude) = result

        value = json.dumps((latitude, longitude))
        try:
            REDIS_SERVER.set(key, value)
        except redis.ConnectionError as e:
            LOG.warning("Connection to redis server on localhost failed.")
        WAIT = max(0, WAIT - .1)
        break

    return (latitude, longitude)



def bounds(address_full, min_radius=None, cache=GEOCODE_CACHE_DEFAULT):
    global WAIT
    bounds_ = None

    address = clean_address(address_full)

    key = geo_key("bounds", address)

    if cache:
        value = None
        try:
            value = REDIS_SERVER.get(key)
        except redis.ConnectionError:
            LOG.warning("Connection to redis server on localhost failed.")

        if value:
            value = value.decode("utf-8")
            try:
                bounds_ = Geobox.from_json(value)
            except ValueError:
                LOG.debug("Could not decode Redis value '%s' to Geobox.",
                          value)

    if not value:
        for _i in range(ATTEMPTS):
            if WAIT:
                time.sleep(WAIT)

            parameters = urllib.parse.urlencode({
                "sensor": "false",
                "address": address,
                "region": GEOCODE_DEFAULT_REGION,
            })

            # Force IPv4 address to avoid timeouts
            host = socket.gethostbyname('maps.googleapis.com')
            url = ("http://%s/maps/api/geocode/json?%s" % (
                host, parameters))

            response = requests.get(url)

            if response.status_code != 200:
                continue

            print(("R", response.encoding))

            content = json.loads(response.text)

            if content["status"] != "OK":
                return None

            long_name = None
            type_ = None
            for component in content["results"][0]["address_components"]:
                type_set = (set(["postal_code", "political"]) &
                            set(component["types"]))
                if type_set:
                    long_name = component["long_name"]
                    type_ = type_set.pop()
                    break
            geometry = content["results"][0]["geometry"]
            viewport = geometry["viewport"]
            bounds_ = Geobox(
                viewport["southwest"]["lat"],
                viewport["northeast"]["lat"],
                viewport["southwest"]["lng"],
                viewport["northeast"]["lng"]
            )
            bounds_.long_name = long_name
            bounds_.type_ = type_
            value = bounds_

            try:
                REDIS_SERVER.set(key, value.to_json())
            except redis.ConnectionError:
                LOG.warning("Connection to redis server on localhost failed.")

            WAIT = max(0, WAIT - .1)
            break
        else:
            return None

    bounds_.name = address_full
    bounds_.set_min_radius(min_radius)
    return bounds_

#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import math
import time
import logging
import mysql.mysql_init

import geo

from hashlib import sha1, md5
from optparse import OptionParser
from urllib import urlencode

from sqlalchemy import create_engine, MetaData
from sqlalchemy import Column, Table, and_
from sqlalchemy import ForeignKey, ForeignKeyConstraint, UniqueConstraint, CheckConstraint, PrimaryKeyConstraint
from sqlalchemy import Boolean, Integer, Float, Numeric
from sqlalchemy.orm import sessionmaker, create_session, relationship, backref, object_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.interfaces import MapperExtension 
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy import Unicode as UnicodeOrig, String as StringOrig

from sqlalchemy.orm.exc import NoResultFound

log = logging.getLogger('model')

Base = declarative_base()

String = lambda : StringOrig
Unicode = lambda : UnicodeOrig

def use_mysql():
    global String, Unicode
    String = lambda : LONGTEXT(charset="latin1", collation="latin1_swedish_ci")
    Unicode = lambda : LONGTEXT(charset="utf8", collation="utf8_general_ci")


if __name__ == '__main__':
    log.addHandler(logging.StreamHandler())
    log.setLevel(logging.WARNING)

    usage = """%prog [SQLITE]

SQLITE :  Destination SQLite database. If not supplied, you must
          specify MySQL credentials in your .mango.conf"""

    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="store_true", dest="verbosity",
                      help="Print verbose information for debugging.", default=None)
    parser.add_option("-q", "--quiet", action="store_false", dest="verbosity",
                      help="Suppress warnings.", default=None)

    (options, args) = parser.parse_args()

    if options.verbosity:
        log.setLevel(logging.INFO)
    elif options.verbosity is False:
        log.setLevel(logging.ERROR)

    if len(args) == 1:
        # SQLite
        sql_db = args[0]
        connection_url = 'sqlite:///' + sql_db
    else:
        # MySQL
        (database,
         app_username, app_password,
         admin_username, admin_password) = mysql.mysql_init.get_conf()
        connection_url = 'mysql://%s:%s@localhost/%s?charset=utf8' % (
            admin_username, admin_password, database)
        use_mysql()



def short_name(name):
    short = name.lower()
    short = re.compile(u"[-_]", re.U).sub(" ", short)
    short = re.compile(u"[^\w\s\|]", re.U).sub("", short)
    short = re.compile(u"[\s]+", re.U).sub(" ", short)
    short = short.strip()
    short = re.compile(u"[\s]*\|[\s]*", re.U).sub("|", short)
    short = re.compile(u"\|+", re.U).sub("|", short)
    short = re.compile(u"(^\||\|$)", re.U).sub("", short)
    short = re.compile(u"[\s]", re.U).sub("-", short)
    return short



def assert_session_is_fresh(session):
    assert not session.new, "Session has new objects: %s" % repr(session.new)
    assert not session.dirty, "Session has dirty objects: %s" % repr(session.dirty)
    assert not session.deleted, "Session has deleted objects: %s" % repr(session.deleted)



def gravatar_hash(plaintext):
    "Generate a pseudorandom 40 digit hexadecimal hash using SHA1"
    return md5(plaintext).hexdigest()



def generate_hash(plaintext):
    "Generate a pseudorandom 40 digit hexadecimal hash using SHA1"
    return sha1(plaintext).hexdigest()



def verify_hash(plaintext, hash_):
    return hash_ == generate_hash(plaintext)



def generate_salted_hash(plaintext, salted_hash=None):
    "Generate a pseudorandom 40 digit hexadecimal salted hash using SHA1"
    if not salted_hash:
        salted_hash = sha1(os.urandom(40)).hexdigest()
    salt = salted_hash[:5]
    return (salt + sha1(salt + plaintext).hexdigest())[:40]



def verify_salted_hash(plaintext, salted_hash):
    return salted_hash == generate_salted_hash(plaintext, salted_hash)



class NotableEntity(object):

    @property
    def note_list_query(self):
        return object_session(self) \
            .query(Note).with_parent(self, "note_list")

    def note_list_query_filtered(self, note_search=None, note_order=None):
        query = self.note_list_query
        if note_search:
            query = query \
                .join((note_fts, note_fts.c.docid == Note.note_id)) \
                .filter(note_fts.c.content.match(note_search))
        if note_order:
            query = query \
                .order_by({
                        "desc":Note.a_time.desc(),
                        "asc":Note.a_time.asc(),
                        }[note_order])
        return query
    
    

address_note = Table(
    'address_note', Base.metadata,
    Column('address_id', Integer, ForeignKey('address.address_id'), primary_key=True),
    Column('note_id', Integer, ForeignKey('note.note_id'), primary_key=True),
    Column('a_time', Float),
   )



org_note = Table(
    'org_note', Base.metadata,
    Column('org_id', Integer, ForeignKey('org.org_id'), primary_key=True),
    Column('note_id', Integer, ForeignKey('note.note_id'), primary_key=True),
    Column('a_time', Float),
    )



orgtag_note = Table(
    'orgtag_note', Base.metadata,
    Column('orgtag_id', Integer, ForeignKey('orgtag.orgtag_id'), primary_key=True),
    Column('note_id', Integer, ForeignKey('note.note_id'), primary_key=True),
    Column('a_time', Float),
    )



org_address = Table(
    'org_address', Base.metadata,
    Column('org_id', Integer, ForeignKey('org.org_id'), primary_key=True),
    Column('address_id', Integer, ForeignKey('address.address_id'), primary_key=True),
    Column('a_time', Float),
    )



org_orgtag = Table(
    'org_orgtag', Base.metadata,
    Column('org_id', Integer, ForeignKey('org.org_id'), primary_key=True),
    Column('orgtag_id', Integer, ForeignKey('orgtag.orgtag_id'), primary_key=True),
    Column('a_time', Float),
    )



note_fts = Table(
    'note_fts', Base.metadata,
    Column('docid', Integer, primary_key=True),
    Column('content', Unicode()),
    mysql_charset='utf8'
    )



class Auth(Base):
    __tablename__ = 'auth'
    __table_args__ = {'sqlite_autoincrement':True}
     
    auth_id = Column(Integer, primary_key=True)

    url = Column(Unicode(), nullable=False)
    name_hash = Column(String(), nullable=False)
    gravatar_hash = Column(String(), nullable=False)
    
    UniqueConstraint(url, name_hash)
    
    def __init__(self, url, name):
        """
        "name" must be a unique value for the specified provider url,
        eg. an email address or unique user name for that service
        """
        self.url = unicode(url)
        self.name_hash = generate_hash(name)
        self.gravatar_hash = gravatar_hash(name)
        


class User(Base):
    __tablename__ = 'user'
    __table_args__ = {'sqlite_autoincrement':True}
     
    user_id = Column(Integer, primary_key=True)
    auth_id = Column(Integer, ForeignKey(Auth.auth_id), nullable=False)
    
    PrimaryKeyConstraint(auth_id)

    name = Column(Unicode(), nullable=False)

    auth = relationship(Auth, backref='user_list')

    def __init__(self, auth, name):
        self.auth = auth
        self.name = unicode(name)

    def verify_auth_name(self, auth_name):
        return verify_hash(auth_name, self.auth.name_hash)

    @staticmethod
    def get_from_auth(session, auth_url, auth_name):
        auth_name_hash = generate_hash(auth_name)
        try:
            user = session.query(User).join(Auth).\
                filter_by(url=auth_url).\
                filter_by(name_hash=auth_name_hash).\
                one()
        except NoResultFound as e:
            user = None;
        return user

        
      
class Session(Base):
    __tablename__ = 'session'
    __table_args__ = {'sqlite_autoincrement':True}

    session_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey(User.user_id), nullable=False)

    c_time = Column(Float, nullable=False)
    a_time = Column(Float, nullable=False)
    d_time = Column(Float)

    ip_address = Column(String(), nullable=False)
    accept_language = Column(String(), nullable=False)
    user_agent = Column(String(), nullable=False)
    
    user = relationship(User, backref='session_list')

    def __init__(self, user, ip_address=None, accept_language=None, user_agent=None):
        self.user = user
        self.c_time = time.time()
        self.a_time = time.time()
        self.ip_address = ip_address
        self.accept_language = accept_language
        self.user_agent = user_agent
        
    def touch_commit(self):
        "Update the accessed time on the db."
        session = object_session(self)
        assert_session_is_fresh(session)
        self.a_time = time.time()
        session.commit()

    def close_commit(self):
        "Close the session by setting 'd_time'."
        session = object_session(self)
        assert_session_is_fresh(session)
        self.d_time = time.time()
        session.commit()



class Org(Base, NotableEntity):
    __tablename__ = 'org'
    __table_args__ = {'sqlite_autoincrement':True}

    org_id = Column(Integer, primary_key=True)

    name = Column(Unicode(), nullable=False)

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float, nullable=False)
    public = Column(Boolean)

    moderation_user = relationship(User, backref='moderation_org_list')
    
    note_list = relationship(
        "Note", secondary=org_note, backref='org_list')
    address_list = relationship(
        "Address", secondary=org_address, backref='org_list')
    orgtag_list = relationship(
        "Orgtag", secondary=org_orgtag, backref='org_list')

    note_list_public = relationship(
        "Note",
        secondary=org_note,
        primaryjoin="Org.org_id == org_note.c.org_id",
        secondaryjoin=(
            "and_(Note.note_id == org_note.c.note_id, "
            "Note.public==True)"
            ),
        passive_deletes=True,
        )
    address_list_public = relationship(
        "Address",
        secondary=org_address,
        primaryjoin="Org.org_id == org_address.c.org_id",
        secondaryjoin=(
            "and_(Address.address_id == org_address.c.address_id, "
            "Address.public==True)"
            ),
        passive_deletes=True,
        )
    orgtag_list_public = relationship(
        "Orgtag",
        secondary=org_orgtag,
        primaryjoin="Org.org_id == org_orgtag.c.org_id",
        secondaryjoin=(
            "and_(Orgtag.orgtag_id == org_orgtag.c.orgtag_id, "
            "Orgtag.public==True)"
            ),
        passive_deletes=True,
        )
    
    def __init__(self, name, moderation_user=None, public=None):
        self.name = self.sanitise_name(name)

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public

    def __unicode__(self):
        return u"<Org-%s(%d) '%s'>" % (
            self.org_id or "?",
            self.public,
            self.name,
            )

    def __str__(self):
        return unicode(self).encode("utf8")

    def obj(self, public=False,
            note_obj_list=None, address_obj_list=None, orgtag_obj_list=None):
        obj = {
            "id": self.org_id,
            "url": self.url,
            "date": self.a_time,
            "name": self.name,
            }
        if public:
            obj["public"] = self.public
        if note_obj_list is not None:
            obj["note_list"] = note_obj_list
        if address_obj_list is not None:
            obj["address_list"] = address_obj_list
        if orgtag_obj_list is not None:
            obj["orgtag_list"] = orgtag_obj_list
        return obj

    def merge(self, other, moderation_user=False, public=None):
        session = object_session(self)
        assert session
        alias_note = Note(
            u"Alias: %s" % other.name, "merge", moderation_user, public)
        self.note_list = list(set(
                self.note_list + other.note_list + [alias_note]))
        self.address_list = list(set(self.address_list + other.address_list))
        self.orgtag_list = list(set(self.orgtag_list + other.orgtag_list))
        other.note_list = []
        other.address_list = []
        other.orgtag_list = []
        session.commit()
        session.delete(other)
        session.commit()

    @property
    def url(self):
        return "/organisation/%d" % self.org_id

    @staticmethod
    def sanitise_name(name):
        return re.sub("[\s]+", " ", name).strip()

    @staticmethod
    def get(orm, name, moderation_user=None, public=None):
        name = Org.sanitise_name(name)
        try:
            org = orm.query(Org).filter(Org.name == name).one()
        except NoResultFound:
            org = Org(
                name,
                moderation_user=moderation_user, public=public,
                )
            orm.add(org)
        return org



class Address(Base, NotableEntity):
    __tablename__ = 'address'
    __table_args__ = {'sqlite_autoincrement':True}

    address_id = Column(Integer, primary_key=True)

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float, nullable=False)
    public = Column(Boolean)

    postal = Column(Unicode(), nullable=False)
    source = Column(Unicode(), nullable=False)
    lookup = Column(Unicode())
    manual_longitude = Column(Float)
    manual_latitude = Column(Float)
    longitude = Column(Float)
    latitude = Column(Float)

    moderation_user = relationship(User, backref='moderation_address_list')
    
    note_list = relationship(
        "Note",
        secondary=address_note,
        backref='address_list'
        )

    note_list_public = relationship(
        "Note",
        secondary=address_note,
        primaryjoin="Address.address_id == address_note.c.address_id",
        secondaryjoin=(
            "and_(Note.note_id == address_note.c.note_id, "
            "Note.public==True)"
            ),
        passive_deletes=True,
        )
    org_list_public = relationship(
        "Org",
        secondary=org_address,
        primaryjoin="Address.address_id == org_address.c.address_id",
        secondaryjoin=(
            "and_(Org.org_id == org_address.c.org_id, "
            "Org.public==True)"
            ),
        passive_deletes=True,
        )

    def __init__(self,
                 postal=None, source=None, lookup=None,
                 manual_longitude=None, manual_latitude=None,
                 longitude=None, latitude=None,
                 moderation_user=None, public=None):

        self.postal = postal
        self.source = source
        self.lookup = lookup
        self.manual_longitude = manual_longitude
        self.manual_latitude = manual_latitude
        self.longitude = longitude
        self.latitude = latitude

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public

    def __unicode__(self):
        return u"<Addr-%s '%s' '%s' %s %s>" % (
            self.address_id or "?",
            self.postal[:10].replace("\n", " "),
            (self.lookup or "")[:10],
            self.repr_coordinates(self.manual_longitude, self.manual_latitude),
            self.repr_coordinates(self.longitude, self.latitude),
            )

    def __str__(self):
        return unicode(self).encode("utf8")

    def geocode(self):
        if self.manual_longitude is not None and self.manual_latitude is not None:
            self.longitude = self.manual_longitude
            self.latitude = self.manual_latitude
            return
        
        if self.lookup:
            coords = geo.geocode(self.lookup)
            if coords:
                (self.latitude, self.longitude) = coords
        else:
            coords = geo.geocode(self.postal)
            if coords:
                (self.latitude, self.longitude) = coords

    def obj(self, public=False,
            note_obj_list=None, org_obj_list=None):
        obj = {
            "id": self.address_id,
            "url": self.url,
            "date": self.a_time,
            "name": self.postal,
            "source": self.source,
            "postal": self.postal,
            "lookup": self.lookup,
            "manual_longitude": self.manual_longitude,
            "manual_latitude": self.manual_latitude,
            "longitude": self.longitude,
            "latitude": self.latitude,
            }
        if public:
            obj["public"] = self.public
        if note_obj_list is not None:
            obj["note_list"] = note_obj_list
        if org_obj_list is not None:
            obj["org_list"] = org_obj_list
        return obj

    @property
    def split(self):
        return filter(None, re.split("(?:\n|,)", self.postal))

    @property
    def name(self):
        return (self.split + [None])[0]

    @property
    def url(self):
        if self.address_id is None:
            return None
        return "/address/%d" % self.address_id

    @staticmethod
    def repr_coordinates(longitude, latitude):
        if longitude and latitude:
            return u"%0.2f°%s %0.2f°%s" % (
                abs(latitude), ("S", "", "N")[cmp(latitude, 0.0) + 1],
                abs(longitude), ("W", "", "E")[cmp(longitude, 0.0) + 1],
                )
        return ""
 
    @staticmethod
    def geobox(latitude, longitude, distance):
        # Cheap
        r = 6378.1
        distance_degrees = 360 * distance / (2 * math.pi * r)
        distance_degrees_lon = distance_degrees * math.cos(math.radians(latitude))
        latmin = latitude - distance_degrees
        latmax = latitude + distance_degrees
        lonmin = longitude - distance_degrees_lon
        lonmax = longitude + distance_degrees_lon
        return {
            "latmax": latmax, "latmin": latmin,
            "lonmax": lonmax, "lonmin": lonmin,
            }

    @staticmethod
    def filter_geobox(query, geobox):
        if not geobox:
            return query
        return query \
            .filter(Address.latitude >= geobox["latmin"]) \
            .filter(Address.latitude <= geobox["latmax"]) \
            .filter(Address.longitude >= geobox["lonmin"]) \
            .filter(Address.longitude <= geobox["lonmax"])

    @staticmethod
    def scale(latitude):
        return math.cos(math.radians(latitude))

    @staticmethod
    def order_distance(query, latlon):
        # Very simplistic
        latitude, longitude = latlon
        lat = func.abs(latitude - Address.latitude)
        lon = func.abs(longitude - Address.longitude)
        scale = Address.scale(latitude)
        return query \
            .filter(Address.latitude != None) \
            .filter(Address.longitude != None) \
            .order_by(lat + lon * scale)

    @staticmethod
    def max_distance(orm, query, latitude, longitude, default=1):
        lat = func.abs(latitude - Address.latitude)
        lon = func.abs(longitude - Address.longitude)
        scale = Address.scale(latitude)

        func_max = func.max
        if orm.connection().dialect.name == "mysql":
            func_max = func.greatest

        query = query.add_columns(func_max(lat, lon * scale).label("dist"))
        sq = query.subquery()
        result = orm.query(sq).order_by("dist desc").first()
        if result:
            return result.dist
        return default



class OrgtagExtension(MapperExtension):
    def before_insert(self, mapper, connection, instance):
        instance.short = short_name(instance.name)

    def before_update(self, mapper, connection, instance):
        instance.short = short_name(instance.name)



class Orgtag(Base, NotableEntity):
    __tablename__ = 'orgtag'
    __table_args__ = {'sqlite_autoincrement':True}
    __mapper_args__ = {'extension':OrgtagExtension()}

    orgtag_id = Column(Integer, primary_key=True)

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float, nullable=False)
    public = Column(Boolean)

    name = Column(Unicode(), nullable=False)
    short = Column(Unicode(), nullable=False)

    moderation_user = relationship(User, backref='moderation_orgtag_list')

    note_list = relationship("Note",
                             secondary=orgtag_note,
                             backref='orgtag_list'
                             )

    note_list_public = relationship(
        "Note",
        secondary=orgtag_note,
        primaryjoin="Orgtag.orgtag_id == orgtag_note.c.orgtag_id",
        secondaryjoin=(
            "and_(Note.note_id == orgtag_note.c.note_id, "
            "Note.public==True)"
            ),
        passive_deletes=True,
        )
    org_list_public = relationship(
        "Org",
        secondary=org_orgtag,
        primaryjoin="Orgtag.orgtag_id == org_orgtag.c.orgtag_id",
        secondaryjoin=(
            "and_(Org.org_id == org_orgtag.c.org_id, "
            "Org.public==True)"
            ),
        passive_deletes=True,
        )

    def __init__(self, name, moderation_user=None, public=None):
        self.name = name

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public

    def __unicode__(self):
        return u"<Orgtag-%s '%s'>" % (
            self.orgtag_id or "?",
            self.name,
            )

    def __str__(self):
        return unicode(self).encode("utf8")

    def obj(self, public=False,
            note_obj_list=None, org_obj_list=None,
            org_len=None):
        obj = {
            "id": self.orgtag_id,
            "url": self.url,
            "date": self.a_time,
            "org_list_url": self.org_list_url(None),
            "name": self.name,
            "short": self.short,
            }
        if public:
            obj["public"] = self.public
        if note_obj_list is not None:
            obj["note_list"] = note_obj_list
        if org_obj_list is not None:
            obj["org_list"] = org_obj_list
        if org_len is not None:
            obj["org_len"] = org_len
        return obj

    def org_list_url(self, parameters=None):
        if parameters == None:
            parameters = {}
        parameters["tag"] = self.short

        return "/organisation?%s" % urlencode(parameters)

    @property
    def url(self):
        return "/organisation-tag/%d" % self.orgtag_id

    @staticmethod
    def get(orm, name, moderation_user=None, public=None):
        try:
            orgtag = orm.query(Orgtag).filter(Orgtag.name == name).one()
        except NoResultFound:
            orgtag = Orgtag(
                name,
                moderation_user=moderation_user, public=public,
                )
            orm.add(orgtag)
        return orgtag

        

class Note(Base):
    __tablename__ = 'note'
    __table_args__ = {'sqlite_autoincrement':True}

    note_id = Column(Integer, primary_key=True)

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float, nullable=False)
    public = Column(Boolean)

    text = Column(Unicode(), nullable=False)
    source = Column(Unicode(), nullable=False)

    moderation_user = relationship(User, backref='moderation_note_list')

    org_list_public = relationship(
        "Org",
        secondary=org_note,
        primaryjoin="Note.note_id == org_note.c.note_id",
        secondaryjoin=(
            "and_(Org.org_id == org_note.c.org_id, "
            "Org.public==True)"
            ),
        passive_deletes=True,
        )
    address_list_public = relationship(
        "Address",
        secondary=address_note,
        primaryjoin="Note.note_id == address_note.c.note_id",
        secondaryjoin=(
            "and_(Address.address_id == address_note.c.address_id, "
            "Address.public==True)"
            ),
        passive_deletes=True,
        )
    orgtag_list_public = relationship(
        "Orgtag",
        secondary=orgtag_note,
        primaryjoin="Note.note_id == orgtag_note.c.note_id",
        secondaryjoin=(
            "and_(Orgtag.orgtag_id == orgtag_note.c.orgtag_id, "
            "Orgtag.public==True)"
            ),
        passive_deletes=True,
        )

    def __init__(self, text=None, source=None,
                 moderation_user=None, public=None):
        self.text = text
        self.source = source

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public

    def __unicode__(self):
        return u"<Note-%s '%s' '%s'>" % (
            self.note_id or "?",
            self.text[:10].replace("\n", " "),
            self.source[:10],
            )

    def __str__(self):
        return unicode(self).encode("utf8")

    def obj(self, public=False,
            org_obj_list=None, address_obj_list=None, orgtag_obj_list=None):
        obj = {
            "id": self.note_id,
            "url": self.url,
            "date": self.a_time,
            "text": self.text,
            "source": self.source,
            }
        linked = False
        if public:
            obj["public"] = self.public
        if org_obj_list is not None:
            obj["org_list"] = org_obj_list
            linked = (linked or []) + org_obj_list
        if address_obj_list is not None:
            obj["address_list"] = address_obj_list
            linked = (linked or []) + address_obj_list
        if orgtag_obj_list is not None:
            obj["orgtag_list"] = orgtag_obj_list
            linked = (linked or []) + orgtag_obj_list
        if linked is not False:
            obj["linked"] = linked
        return obj

    @property
    def url(self):
        return "/note/%d" % self.note_id



Base._types = {
    "Org":Org,
    "Address":Address,
    "Orgtag":Orgtag,
    "Note":Note,
    }


if __name__ == '__main__':
    engine = create_engine(connection_url)
    Base.metadata.create_all(engine)



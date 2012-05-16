#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import time
import logging

import geopy
from urllib2 import URLError

from hashlib import sha1
from optparse import OptionParser

from sqlalchemy import create_engine, MetaData
from sqlalchemy import Column, Table, and_
from sqlalchemy import ForeignKey, ForeignKeyConstraint, UniqueConstraint, CheckConstraint, PrimaryKeyConstraint
from sqlalchemy import Boolean, Integer, Float, Unicode, Numeric, String
from sqlalchemy.orm import sessionmaker, create_session, relationship, backref, object_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.interfaces import MapperExtension 
from sqlalchemy.sql import func

from sqlalchemy.orm.exc import NoResultFound

log = logging.getLogger('model')

Base = declarative_base()



def short_name(name):
    short = name.lower()
    r = re.compile(u"[-_]", re.U)
    short = r.sub(" ", short)
    r = re.compile(u"[^\w\s]", re.U)
    short = r.sub("", short)
    r = re.compile(u"[\s]+", re.U)
    short = r.sub(" ", short)
    short = short.strip()
    r = re.compile(u"[\s]", re.U)
    short = r.sub("-", short)
    return short



def assert_session_is_fresh(session):
    assert not session.new, "Session has new objects: %s" % repr(session.new)
    assert not session.dirty, "Session has dirty objects: %s" % repr(session.dirty)
    assert not session.deleted, "Session has deleted objects: %s" % repr(session.deleted)



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

    

class Auth(Base):
    __tablename__ = 'auth'
    __table_args__ = {'sqlite_autoincrement':True}
     
    auth_id = Column(Integer, primary_key=True)

    url = Column(Unicode, nullable=False)
    name_hash = Column(String, nullable=False)
    
    UniqueConstraint(url, name_hash)
    
    def __init__(self, url, name):
        """
        "name" must be a unique value for the specified provider url,
        eg. an email address or unique user name for that service
        """
        self.url = url
        self.name_hash = generate_hash(name)



class User(Base):
    __tablename__ = 'user'
    __table_args__ = {'sqlite_autoincrement':True}
     
    user_id = Column(Integer, primary_key=True)
    auth_id = Column(Integer, ForeignKey(Auth.auth_id), nullable=False)
    
    PrimaryKeyConstraint(auth_id)

    name = Column(Unicode, nullable=False)

    auth = relationship(Auth, backref='user_list')

    def __init__(self, auth, name):
        self.auth = auth
        self.name = name

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

    ip_address = Column(String, nullable=False)
    accept_language = Column(String, nullable=False)
    user_agent = Column(String, nullable=False)
    
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



organisation_address = Table(
    'organisation_address', Base.metadata,
    Column('organisation_id', Integer, ForeignKey('organisation.organisation_id'), primary_key=True),
    Column('address_e', Integer, ForeignKey('address.address_e'), primary_key=True)
    )



organisation_organisation_tag = Table(
    'organisation_organisation_tag', Base.metadata,
    Column('organisation_id', Integer, ForeignKey('organisation.organisation_id'), primary_key=True),
    Column('organisation_tag_e', Integer, ForeignKey('organisation_tag.organisation_tag_e'), primary_key=True)
    )



class Organisation(Base):
    __tablename__ = 'organisation'
    __table_args__ = {'sqlite_autoincrement':True}

    organisation_id = Column(Integer, primary_key=True)
    organisation_e = Column(Integer)

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float, nullable=False)
    visible = Column(Boolean, nullable=False, default=True)

    name = Column(Unicode, nullable=False)

    moderation_user = relationship(User, backref='moderation_organisation_list')
    
    address_entity_list = relationship("Address",
                                       secondary=organisation_address,
                                       backref='organisation_list'
                                       )
    organisation_tag_entity_list = relationship("OrganisationTag",
                                                secondary=organisation_organisation_tag,
                                                backref='organisation_list'
                                                )
    
    def __init__(self, name, moderation_user=None, visible=True):
        self.name = name

        self.moderation_user = moderation_user
        self.a_time = time.time()
        self.visible = visible

    def __repr__(self):
        return "<Org-%d,%d(%d) '%s'>" % (self.organisation_e, self.organisation_id, self.visible, self.name)

    def copy(self, moderation_user=None, visible=True):
        assert self.organisation_e
        new = Organisation(self.name, moderation_user, visible)
        new.organisation_e = self.organisation_e

        for address in self.address_list():
            new.address_entity_list.append(address)

        for tag in self.tag_list():
            new.organisation_tag_entity_list.append(tag)

        return new

    def obj(self):
        return {
            "id": self.organisation_e,
            "url": self.url,
            "name": self.name,
            "address_id": [address.address_e for address in self.address_list()],
            "address": [address.obj() for address in self.address_list()],
            "tag_id": [tag.organisation_tag_e for tag in self.tag_list()],
            "tag": [tag.obj() for tag in self.tag_list()],
            }
            
        
    def address_list(self):
        orm = object_session(self)
        
        latest_address = orm.query(Address.address_e, func.max(Address.address_id)\
                             .label("address_id")).group_by("address_e").subquery()

        return orm.query(Address).join((latest_address, and_(
            latest_address.c.address_e == Address.address_e,
            latest_address.c.address_id == Address.address_id,
            ))).join(organisation_address).filter_by(organisation_id=self.organisation_id).all()

    def tag_list(self):
        orm = object_session(self)
        
        latest_organisation_tag = orm.query(OrganisationTag.organisation_tag_e, func.max(OrganisationTag.organisation_tag_id)\
                             .label("organisation_tag_id")).group_by("organisation_tag_e").subquery()

        return orm.query(OrganisationTag).join((latest_organisation_tag, and_(
            latest_organisation_tag.c.organisation_tag_e == OrganisationTag.organisation_tag_e,
            latest_organisation_tag.c.organisation_tag_id == OrganisationTag.organisation_tag_id,
            ))).join(organisation_organisation_tag).filter_by(organisation_id=self.organisation_id).all()

    @property
    def url(self):
        return "/organisation/%d" % self.organisation_e

    @property
    def revision_url(self):
        return "/organisation/%d,%d" % (self.organisation_e, self.organisation_id)

    @staticmethod
    def query_latest(orm):
        latest = orm.query(
            func.max(Organisation.organisation_id)\
                .label("organisation_id")
            )\
            .group_by(Organisation.organisation_e)
            
        return orm.query(Organisation)\
            .filter(Organisation.organisation_id.in_(latest))



class Address(Base):
    __tablename__ = 'address'
    __table_args__ = {'sqlite_autoincrement':True}

    address_id = Column(Integer, primary_key=True)
    address_e = Column(Integer)

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float, nullable=False)

    postal = Column(Unicode, nullable=False)
    lookup = Column(Unicode)
    manual_longitude = Column(Float)
    manual_latitude = Column(Float)
    longitude = Column(Float)
    latitude = Column(Float)

    moderation_user = relationship(User, backref='moderation_address_list')
    
    geocoder = geopy.geocoders.Google()

    def __init__(self, postal=None, lookup=None,
                 manual_longitude=None, manual_latitude=None,
                 longitude=None, latitude=None,
                 moderation_user=None):
        self.moderation_user = moderation_user
        self.a_time = time.time()

        self.postal = postal
        self.lookup = lookup
        self.manual_longitude = manual_longitude
        self.manual_latitude = manual_latitude
        self.longitude = longitude
        self.latitude = latitude

    def __repr__(self):
        return "<Addr-%d,%d '%s' '%s' %s %s>" % (
            self.address_e, self.address_id,
            self.postal[:10],
            (self.lookup or "")[:10],
            self.repr_coordinates(self.manual_longitude, self.manual_latitude),
            self.repr_coordinates(self.longitude, self.latitude),
            )

    def copy(self, moderation_user=None):
        assert self.address_e
        address = Address(
            self.postal, self.lookup,
            self.manual_longitude, self.manual_latitude,
            self.longitude, self.latitude,
            moderation_user)
        address.address_e = self.address_e
        return address

    def _geocode(self, address):
        address, (latitude, longitude) = self.geocoder.geocode(address.encode("utf-8"))
        return (latitude, longitude)

    def geocode(self):
        if self.manual_longitude and self.manual_latitude:
            self.longitude = self.manual_longitude
            self.latitude = self.manual_latitude
            return
        
        if self.lookup:
            try:
                (self.latitude, self.longitude) = self._geocode(self.lookup)
            except geopy.geocoders.google.GQueryError as e:
                pass
            except URLError as e:
                pass
            except ValueError as e:
                pass
            return

        try:
            (self.latitude, self.longitude) = self._geocode(self.postal)
        except geopy.geocoders.google.GQueryError as e:
            pass
        except URLError as e:
            pass
        except ValueError as e:
            pass

    def obj(self):
        return {
            "id": self.address_e,
            "url": self.url,
            "postal": self.postal,
            "lookup": self.lookup,
            "manual_longitude": self.manual_longitude,
            "manual_latitude": self.manual_latitude,
            "longitude": self.longitude,
            "latitude": self.latitude,
            }

    @property
    def url(self):
        return "/address/%d" % self.address_e

    @property
    def revision_url(self):
        return "/address/%d,%d" % (self.address_e, self.address_id)

    @staticmethod
    def repr_coordinates(longitude, latitude):
        if longitude and latitude:
            return u"%0.2f°%s %0.2f°%s" % (
                abs(latitude), ("S", "", "N")[cmp(latitude, 0.0) + 1],
                abs(longitude), ("W", "", "E")[cmp(longitude, 0.0) + 1],
                )
        return ""

    @staticmethod
    def query_latest(orm):
        latest = orm.query(Address.address_e, func.max(Address.address_id)\
                             .label("address_id")).group_by("address_e").subquery()

        return orm.query(Address).join((latest, and_(
            latest.c.address_e == Address.address_e,
            latest.c.address_id == Address.address_id,
            )))



class OrganisationTagExtension(MapperExtension):
    def before_insert(self, mapper, connection, instance):
        instance.short = short_name(instance.name)

    def before_update(self, mapper, connection, instance):
        instance.short = short_name(instance.name)



class OrganisationTag(Base):
    __tablename__ = 'organisation_tag'
    __table_args__ = {'sqlite_autoincrement':True}
    __mapper_args__ = {'extension':OrganisationTagExtension()}

    organisation_tag_id = Column(Integer, primary_key=True)
    organisation_tag_e = Column(Integer)

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float, nullable=False)

    name = Column(Unicode, nullable=False)
    short = Column(Unicode, nullable=False)

    moderation_user = relationship(User, backref='moderation_organisation_tag_list')

    def __init__(self, name, moderation_user=None):
        self.moderation_user = moderation_user
        self.a_time = time.time()

        self.name = name

    def __repr__(self):
        return "<OrgTag-%d,%d '%s'>" % (
            self.organisation_tag_e,
            self.organisation_tag_id,
            self.name,
            )

    def copy(self, moderation_user=None):
        assert self.organisation_tag_e
        organisation_tag = OrganisationTag(
            self.name,
            moderation_user)
        organisation_tag.organisation_tag_e = self.organisation_tag_e
        return organisation_tag

    def obj(self):
        return {
            "id": self.organisation_tag_e,
            "url": self.url,
            "name": self.name,
            "short": self.short,
            }

    @property
    def url(self):
        return "/organisation-tag/%d" % self.organisation_tag_e

    @property
    def revision_url(self):
        return "/organisation-tag/%d,%d" % (
            self.organisation_tag_e,
            self.organisation_tag_id,
            )

    @staticmethod
    def query_latest(orm):
        latest = orm.query(
            func.max(OrganisationTag.organisation_tag_id)\
                .label("organisation_tag_id")
            )\
            .group_by(OrganisationTag.organisation_tag_e)

        return orm.query(OrganisationTag)\
            .filter(OrganisationTag.organisation_tag_id.in_(latest))



if __name__ == '__main__':
    log.addHandler(logging.StreamHandler())
    log.setLevel(logging.WARNING)

    usage = """%prog SQLITE"""

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

    if not len(args) == 1:
        parser.print_usage()
        sys.exit(1)

    sql_db = args[0]

    connection_url = 'sqlite:///' + sql_db
    
    engine = create_engine(connection_url)
    Base.metadata.create_all(engine)

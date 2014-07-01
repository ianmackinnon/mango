#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import math
import time
import logging
from hashlib import sha1, md5
from optparse import OptionParser
from urllib import urlencode

from sqlalchemy import create_engine, MetaData
from sqlalchemy import Column, Table, and_
from sqlalchemy import ForeignKey, ForeignKeyConstraint, UniqueConstraint, CheckConstraint, PrimaryKeyConstraint
from sqlalchemy.orm import sessionmaker, create_session, relationship, backref, object_session
from sqlalchemy.orm.util import has_identity
from sqlalchemy.orm.interfaces import MapperExtension 
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

from sqlalchemy import Boolean, Integer, Float as FloatOrig, Numeric, Date, Time
from sqlalchemy import Unicode as UnicodeOrig, String as StringOrig
from sqlalchemy.dialects.mysql import LONGTEXT, DOUBLE, VARCHAR
from sqlalchemy import event as sqlalchemy_event

import geo

import conf
from mysql import mysql
from search import search



log = logging.getLogger('model')

Base = declarative_base()

Float = lambda : FloatOrig
String = lambda : StringOrig
Unicode = lambda : UnicodeOrig
StringKey = lambda : StringOrig
UnicodeKey = lambda : UnicodeOrig

conf_path = ".mango.conf"



def use_mysql():
    global Float, String, Unicode, StringKey, UnicodeKey
    Float = lambda : DOUBLE()
    String = lambda : LONGTEXT(charset="latin1", collation="latin1_swedish_ci")
    Unicode = lambda : LONGTEXT(charset="utf8", collation="utf8_bin")
    # MySQL needs a character limit to use a variable-length column as a key.
    StringKey = lambda : VARCHAR(length=128, charset="latin1", collation="latin1_swedish_ci")
    UnicodeKey = lambda : VARCHAR(length=128, charset="utf8", collation="utf8_bin")



def get_database():
    database = conf.get(conf_path, u"database", u"database")
    if not database in [u'mysql', u'sqlite']:
        log.error("""Value for database/database in configuration file '%s' is '%s'. Valid values are 'sqlite' or 'mysql'.""" % (database, conf_path))
        sys.exit(1)
    return database



def set_database():
    database = get_database()
    if database == "mysql":
        use_mysql()



def sqlite_connection_url(username, password, database):
    sqlite_path = conf.get(conf_path, u"sqlite", u"database")
    return 'sqlite:///%s' % sqlite_path



def mysql_connection_url(username, password, database):
    return 'mysql://%s:%s@localhost/%s?charset=utf8' % (
        username, password, database)



def connection_url_admin():
    database = conf.get(conf_path, u"database", u"database")
    if database == "sqlite":
        return sqlite_connection_url()
    if database == "mysql":
        username = conf.get(conf_path, u"mysql-admin", u"username")
        password = conf.get(conf_path, u"mysql-admin", u"password")
        database = conf.get(conf_path, u"mysql", u"database")
        return mysql_connection_url(username, password, database)



def connection_url_app():
    database = conf.get(conf_path, u"database", u"database")
    if database == "sqlite":
        return sqlite_connection_url()
    if database == "mysql":
        username = conf.get(conf_path, u"mysql-app", u"username")
        password = conf.get(conf_path, u"mysql-app", u"password")
        database = conf.get(conf_path, u"mysql", u"database")
        return mysql_connection_url(username, password, database)



if __name__ == '__main__':
    log.addHandler(logging.StreamHandler())
    search.log.addHandler(logging.StreamHandler())

    usage = """%%prog"""

    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", dest="verbose",
                      help="Print verbose information for debugging.", default=0)
    parser.add_option("-q", "--quiet", action="count", dest="quiet",
                      help="Suppress warnings.", default=0)

    (options, args) = parser.parse_args()
    args = [arg.decode(sys.getfilesystemencoding()) for arg in args]

    log_level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG,)[max(0, min(3, 1 + options.verbose - options.quiet))]
    log.setLevel(log_level)
    search.log.setLevel(log_level)

    set_database()




def short_name(name, allow_end_pipe=False):
    """
    Accept letters and numbers in all alphabets, converting to lower case.
    Reject symbols except '-'.
    Use '|' as a namespace separator.
    """
    if not name:
        return name
    short = name.lower()
    short = re.compile(u"[-_/]", re.U).sub(" ", short)
    short = re.compile(u"[^\w\s\|]", re.U).sub("", short)
    short = re.compile(u"[\s]+", re.U).sub(" ", short)
    short = short.strip()
    short = re.compile(u"[\s]*\|[\s]*", re.U).sub("|", short)
    short = re.compile(u"\|+", re.U).sub("|", short)
    if not allow_end_pipe:
        short = re.compile(u"(^\||\|$)", re.U).sub("", short)
    short = re.compile(u"[\s]", re.U).sub("-", short)
    return short



def sanitise_name(name):
    return re.sub(u"[\s]+", u" ", name).strip()



def sanitise_address(address, allow_commas=True):
    if not address:
        return address
    address = re.sub("(\r|\n)+", "\n", address)
    address = re.sub("(^|\n)[\s,]+", "\n", address)
    address = re.sub("[\s,]+($|\n)", "\n", address)
    if (not allow_commas) or (not "\n" in address):
        address = re.sub("(,|\n)+", "\n", address)
        address = re.sub("(^|\n)[\s,]+", "\n", address)
        address = re.sub("[\s,]+($|\n)", "\n", address)
    address = re.sub("[ \t]+", " ", address).strip()
    return address



def assert_session_is_fresh(session):
    assert not session.new, "Session has new objects: %s" % repr(session.new)
    assert not session.dirty, "Session has dirty objects: %s" % repr(session.dirty)
    assert not session.deleted, "Session has deleted objects: %s" % repr(session.deleted)



def detach(entity):
    session = object_session(entity)
    if session and not has_identity(entity):
        session.expunge(entity)
        


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



class classproperty(property):
    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()


    
url_directory = {
    "org": "organisation",
    "org_v": "organisation",
    "orgtag": "organisation-tag",
    "orgalias": "organisation-alias",
    "event": "event",
    "event_v": "event",
    "eventtag": "event-tag",
    "address": "address",
    "address_v": "address",
    "note": "note",
    "note_v": "note",
    "contact": "contact",
    "contact_v": "contact",
    }


class MangoEntity(object):
    content_hints = []

    def content_same(self, other, public=True):
        extra = public and ["public"] or []
        for name in self.content + extra:
            if getattr(self, name) != getattr(other, name):
                return False
        return True

    def content_copy(self, other, user, public=True):
        extra = public and ["public"] or []
        for name in self.content + extra:
            setattr(self, name, getattr(other, name))
        self.moderation_user = user

    @property
    def url(self):
        name = url_directory[self.__tablename__]
        if not name:
            raise HTTPError(500, "No URL space for type '%s'." % type(entity))
        if not self.entity_id_value:
            return None
        url = "/%s/%d" % (name, self.entity_id_value)
        return url

    @property
    def url_v(self):
        assert self.entity_v_id_value
        if not self.entity_v_id_value:
            return None
        return "%s/revision/%d" % (self.url, self.entity_v_id_value)

    def obj(self, **kwargs):
        obj = {
            "id": self.entity_id_value,
            "url": self.url,
            "date": self.a_time,
            }

        if hasattr(self, "entity_v_id"):
            obj.update({
                    "v_id": self.entity_v_id_value,
                    "suggestion": True,
                    })
            
        if bool(kwargs.pop("public", None)):
            obj["public"] = self.public

        for name in self.content + self.content_hints:
            if kwargs.pop(name, None) == False:
                continue
            value = getattr(self, name)
            if name.endswith("_date") and value:
                value = value.strftime("%Y-%m-%d")
            if name.endswith("_time") and value:
                value = value.strftime("%H:%M")
                
            obj[name] = value

        if hasattr(self, "obj_extra"):
            obj.update(self.obj_extra(obj))

        obj.update(kwargs)
            
        return obj

    @property
    def entity_id_value(self):
        return getattr(self, self.entity_id.key, None)

    @property
    def entity_v_id_value(self):
        return getattr(self, self.entity_v_id.key, None)




class NotableEntity(object):

    @property
    def note_list_query(self):
        return object_session(self) \
            .query(Note).with_parent(self, "note_list")

    def note_list_filtered(self,
                           note_search=None, note_order=None,
                           all_visible=None,
                           note_offset=None):
        query = self.note_list_query
        if not all_visible:
            query = query \
                .filter(Note.public==True)
        if note_search:
            query = query \
                .join((note_fts, note_fts.c.docid == Note.note_id)) \
                .filter(note_fts.c.content.match(note_search))
        if not note_order:
            note_order = 'desc'
        query = query \
            .order_by({
                "desc":Note.a_time.desc(),
                "asc":Note.a_time.asc(),
                        }[note_order])
            
#        if note_offset is not None:
#            query = query.offset(note_offset)

        count = query.count()
#        query = query.limit(30).all()
        return query, count
    
    

address_note = Table(
    'address_note', Base.metadata,
    Column('address_id', Integer, ForeignKey('address.address_id'), primary_key=True),
    Column('note_id', Integer, ForeignKey('note.note_id'), primary_key=True),
    Column('a_time', Float()),
    mysql_engine='InnoDB',
   )



org_note = Table(
    'org_note', Base.metadata,
    Column('org_id', Integer, ForeignKey('org.org_id'), primary_key=True),
    Column('note_id', Integer, ForeignKey('note.note_id'), primary_key=True),
    Column('a_time', Float()),
    mysql_engine='InnoDB',
    )



event_note = Table(
    'event_note', Base.metadata,
    Column('event_id', Integer, ForeignKey('event.event_id'), primary_key=True),
    Column('note_id', Integer, ForeignKey('note.note_id'), primary_key=True),
    Column('a_time', Float()),
    mysql_engine='InnoDB',
    )



orgtag_note = Table(
    'orgtag_note', Base.metadata,
    Column('orgtag_id', Integer, ForeignKey('orgtag.orgtag_id'), primary_key=True),
    Column('note_id', Integer, ForeignKey('note.note_id'), primary_key=True),
    Column('a_time', Float()),
    mysql_engine='InnoDB',
    )



eventtag_note = Table(
    'eventtag_note', Base.metadata,
    Column('eventtag_id', Integer, ForeignKey('eventtag.eventtag_id'), primary_key=True),
    Column('note_id', Integer, ForeignKey('note.note_id'), primary_key=True),
    Column('a_time', Float()),
    mysql_engine='InnoDB',
    )



org_address = Table(
    'org_address', Base.metadata,
    Column('org_id', Integer, ForeignKey('org.org_id'), primary_key=True),
    Column('address_id', Integer, ForeignKey('address.address_id'), primary_key=True),
    Column('a_time', Float()),
    mysql_engine='InnoDB',
    )



event_address = Table(
    'event_address', Base.metadata,
    Column('event_id', Integer, ForeignKey('event.event_id'), primary_key=True),
    Column('address_id', Integer, ForeignKey('address.address_id'), primary_key=True),
    Column('a_time', Float()),
    mysql_engine='InnoDB',
    )



org_orgtag = Table(
    'org_orgtag', Base.metadata,
    Column('org_id', Integer, ForeignKey('org.org_id'), primary_key=True),
    Column('orgtag_id', Integer, ForeignKey('orgtag.orgtag_id'), primary_key=True),
    Column('a_time', Float()),
    mysql_engine='InnoDB',
    )



event_eventtag = Table(
    'event_eventtag', Base.metadata,
    Column('event_id', Integer, ForeignKey('event.event_id'), primary_key=True),
    Column('eventtag_id', Integer, ForeignKey('eventtag.eventtag_id'), primary_key=True),
    Column('a_time', Float()),
    mysql_engine='InnoDB',
    )



org_event = Table(
    'org_event', Base.metadata,
    Column('org_id', Integer, ForeignKey('org.org_id'), primary_key=True),
    Column('event_id', Integer, ForeignKey('event.event_id'), primary_key=True),
    Column('a_time', Float()),
    mysql_engine='InnoDB',
    )



org_contact = Table(
    'org_contact', Base.metadata,
    Column('org_id', Integer, ForeignKey('org.org_id'), primary_key=True),
    Column('contact_id', Integer, ForeignKey('contact.contact_id'), primary_key=True),
    Column('a_time', Float()),
    mysql_engine='InnoDB',
    )



event_contact = Table(
    'event_contact', Base.metadata,
    Column('event_id', Integer, ForeignKey('event.event_id'), primary_key=True),
    Column('contact_id', Integer, ForeignKey('contact.contact_id'), primary_key=True),
    Column('a_time', Float()),
    mysql_engine='InnoDB',
    )



note_fts = Table(
    'note_fts', Base.metadata,
    Column('docid', Integer, primary_key=True),
    Column('content', Unicode()),
    mysql_engine='MyISAM',
    mysql_charset='utf8'
    )







class Auth(Base):
    __tablename__ = 'auth'
    __table_args__ = (
        UniqueConstraint('url', 'name_hash'),    
        {
            'sqlite_autoincrement': True,
            "mysql_engine": 'InnoDB',
            }
        )
    
    auth_id = Column(Integer, primary_key=True)

    url = Column(StringKey(), nullable=False)
    name_hash = Column(StringKey(), nullable=False)
    gravatar_hash = Column(String(), nullable=False)
    
    def __init__(self, url, name):
        """
        "name" must be a unique value for the specified provider url,
        eg. an email address or unique user name for that service
        """
        self.url = unicode(url)
        self.name_hash = generate_hash(name)
        self.gravatar_hash = gravatar_hash(name)

    @staticmethod
    def get(orm, url, name):
        url = unicode(url)
        name_hash = generate_hash(name)

        auth = None
        try:
            auth = orm.query(Auth).filter_by(url=url, name_hash=name_hash).one()
        except NoResultFound:
            pass

        if not auth:
            auth = Auth(url, name)
            orm.add(auth)

        return auth
        


class User(Base):
    __tablename__ = 'user'
    __table_args__ = (
        UniqueConstraint('auth_id'),    
        {
            'sqlite_autoincrement': True,
            "mysql_engine": 'InnoDB',
            }
        )
     
    user_id = Column(Integer, primary_key=True)
    auth_id = Column(Integer, ForeignKey(Auth.auth_id), nullable=True)
    
    PrimaryKeyConstraint(auth_id)

    name = Column(Unicode(), nullable=False)

    moderator = Column(Boolean, nullable=False, default=False)

    locked = Column(Boolean, nullable=False, default=False)

    auth = relationship(Auth, backref='user_list')

    def __init__(self, auth, name, moderator=False, locked=False):
        self.auth = auth
        self.name = sanitise_name(name)
        self.moderator = moderator
        self.locked = locked

    def verify_auth_name(self, auth_name):
        return verify_hash(auth_name, self.auth.name_hash)

    def gravatar_hash(self):
        return self.auth and self.auth.gravatar_hash or gravatar_hash(str(self.user_id))

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

    @staticmethod
    def get(orm, auth, name):
        name = unicode(name)

        user = None
        try:
            user = orm.query(User).filter_by(auth=auth, name=name).one()
        except NoResultFound:
            pass

        if not user:
            user = User(auth, name)
            orm.add(user)

        return user

        
      
class Session(Base):
    __tablename__ = 'session'
    __table_args__ = {
        'sqlite_autoincrement': True,
        "mysql_engine": 'InnoDB',
        }

    session_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey(User.user_id), nullable=False)

    c_time = Column(Float(), nullable=False)
    a_time = Column(Float(), nullable=False)
    d_time = Column(Float())

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



class Medium(Base):
    __tablename__ = 'medium'
    __table_args__ = {
        'sqlite_autoincrement': True,
        "mysql_engine": 'InnoDB',
        }

    medium_id = Column(Integer, primary_key=True)
    name = Column(Unicode(), nullable=False)

    contact_list = relationship(
        "Contact",
        backref='medium',
        cascade="all, delete, delete-orphan",
        )

    def __init__(self, name):
        self.name = unicode(name)



class Org(Base, MangoEntity, NotableEntity):
    __tablename__ = 'org'
    __table_args__ = {
        'sqlite_autoincrement': True,
        "mysql_engine": 'InnoDB',
        }

    org_id = Column(Integer, primary_key=True)

    name = Column(Unicode(), nullable=False)
    description = Column(Unicode())
    end_date = Column(Date)

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float(), nullable=False)
    public = Column(Boolean)

    moderation_user = relationship(User, backref='moderation_org_list')
    
    orgalias_list = relationship(
        "Orgalias",
        backref='org',
        cascade="all, delete, delete-orphan",
        )
    note_list = relationship(
        "Note",
        secondary=org_note,
        backref='org_list',
        single_parent=True,  # shouldn't be single parent
        cascade="all, delete, delete-orphan",
        )
    address_list = relationship(
        "Address",
        secondary=org_address,
        backref='org_list',
        single_parent=True,
        cascade="all, delete, delete-orphan",
        order_by="Address.latitude.desc()",
        )
    orgtag_list = relationship(
        "Orgtag",
        secondary=org_orgtag,
        backref='org_list',
        cascade="save-update",
        order_by="Orgtag.name",
        )
    event_list = relationship(
        "Event",
        secondary=org_event,
        backref='org_list',
        cascade="save-update",
        )
    contact_list = relationship(
        "Contact",
        secondary=org_contact,
        backref='org_list',
        single_parent=True,
        cascade="all, delete, delete-orphan",
        )

    orgalias_list_public = relationship(
        "Orgalias",
        primaryjoin=(
            "and_(Orgalias.org_id == Org.org_id, "
            "Orgalias.public==True)"
            ),
        passive_deletes=True,
        )
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
        order_by="Address.latitude.desc()",
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
        order_by="Orgtag.name",
        )
    event_list_public = relationship(
        "Event",
        secondary=org_event,
        primaryjoin="Org.org_id == org_event.c.org_id",
        secondaryjoin=(
            "and_(Event.event_id == org_event.c.event_id, "
            "Event.public==True)"
            ),
        passive_deletes=True,
        )
    contact_list_public = relationship(
        "Contact",
        secondary=org_contact,
        primaryjoin="Org.org_id == org_contact.c.org_id",
        secondaryjoin=(
            "and_(Contact.contact_id == org_contact.c.contact_id, "
            "Contact.public==True)"
            ),
        passive_deletes=True,
        )
    
    content = [
        "name",
        "description",
        "end_date",  # '..._date' causes formatting in 'obj()'
        ]

    @classproperty
    @classmethod
    def entity_id(cls):
        return cls.org_id

    def __init__(self,
                 name, description=None, end_date=None,
                 moderation_user=None, public=None):
        self.name = sanitise_name(name)

        self.description = description and unicode(description) or None
        self.end_date = end_date

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public

    def __unicode__(self):
        return u"<Org-%s (%s) '%s'>" % (
            self.org_id or "?",
            {True:"public", False:"private", None: "pending"}[self.public],
            self.name,
            )

    def pprint(self, indent=""):
        o = u"";
        o += u"%sOrg: %s %s\n" % (indent, self.org_id, self.name)
        for orgalias in self.orgalias_list:
            o += orgalias.pprint(indent + "  ")
        for contact in self.contact_list:
            o += contact.pprint(indent + "  ")
        for orgtag in self.orgtag_list:
            o += orgtag.pprint(indent + "  ")
        for address in self.address_list:
            o += address.pprint(indent + "  ")
        for note in self.note_list:
            o += note.pprint(indent + "  ")
        for event in self.event_list:
            o += u"%sEvent: %s %s...\n" % (indent + "  ", event.event_id, event.name)
        return o

    def merge(self, other, moderation_user):
        "Merge other into self."
        
        session = object_session(self)
        assert session

        print "[", self.org_id, other.org_id, len(other.orgalias_list), "]"

        orgalias = Orgalias.get(session, other.name, self, moderation_user, other.public)

        self.orgalias_list = list(set(self.orgalias_list + other.orgalias_list))
        self.note_list = list(set(self.note_list + other.note_list))
        self.address_list = list(set(self.address_list + other.address_list))
        self.orgtag_list = list(set(self.orgtag_list + other.orgtag_list))
        self.event_list = list(set(self.event_list + other.event_list))
        self.contact_list = list(set(self.contact_list + other.contact_list))
        other.orgalias_list = []
        other.note_list = []
        other.address_list = []
        other.orgtag_list = []
        other.event_list = []
        other.contact_list = []

        for alias in self.orgalias_list:
            print alias.orgalias_id, alias.org_id, alias.name

        session.delete(other)

    @staticmethod
    def get(orm, name, accept_alias=None, moderation_user=None, public=None):
        name = sanitise_name(name)

        org = None
        try:
            org = orm.query(Org).filter(Org.name == name).one()
        except NoResultFound:
            pass

        if accept_alias:
            try:
                org = orm.query(Org)\
                    .join(Orgalias)\
                    .filter(Orgalias.name == name).one()
            except NoResultFound:
                pass

        if not org:
            org = Org(
                name,
                moderation_user=moderation_user, public=public,
                )
            orm.add(org)

        return org



class Orgalias(Base, MangoEntity):
    __tablename__ = 'orgalias'
    __table_args__ = {
        'sqlite_autoincrement': True,
        "mysql_engine": 'InnoDB',
        }

    orgalias_id = Column(Integer, primary_key=True)

    org_id = Column(Integer, ForeignKey(Org.org_id), nullable=False)
    
    name = Column(Unicode(), nullable=False)

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float(), nullable=False)
    public = Column(Boolean)

    moderation_user = relationship(User, backref='moderation_orgalias_list')

    content = [
        "name",
        ]

    @classproperty
    @classmethod
    def entity_id(cls):
        return cls.orgalias_id

    def __init__(self, name, org, moderation_user=None, public=None):
        self.name = sanitise_name(name)
        self.org = org

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public

    def __unicode__(self):
        return u"<Orgalias-%s (%s) '%s':%d>" % (
            self.orgalias_id or "?",
            {True:"public", False:"private", None: "pending"}[self.public],
            self.name, self.org_id,
            )

    def pprint(self, indent=""):
        o = u"";
        o += u"%sOrgalias: %s %s\n" % (indent, self.orgalias_id, self.name)
        return o

    @staticmethod
    def get(orm, name, org, moderation_user=None, public=None):
        name = sanitise_name(name)
        try:
            orgalias = orm.query(Orgalias)\
                .filter_by(name=name, org_id=org.org_id).one()
        except NoResultFound:
            orgalias = Orgalias(
                name, org,
                moderation_user=moderation_user, public=public,
                )
            orm.add(orgalias)
        return orgalias



class Event(Base, MangoEntity, NotableEntity):
    __tablename__ = 'event'
    __table_args__ = (
        CheckConstraint("end_time > start_time or end_date > start_date"),
        {
            'sqlite_autoincrement': True,
            "mysql_engine": 'InnoDB',
            },
        )
    event_id = Column(Integer, primary_key=True)

    name = Column(Unicode(), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date,
                      CheckConstraint("end_date >= start_date"),
                      nullable=False,
                      )
    description = Column(Unicode())
    start_time = Column(Time)
    end_time = Column(Time)

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float(), nullable=False)
    public = Column(Boolean)

    

    moderation_user = relationship(User, backref='moderation_event_list')
    
    note_list = relationship(
        "Note",
        secondary=event_note,
        backref='event_list',
        single_parent=True,
        cascade="all, delete, delete-orphan",
        )
    address_list = relationship(
        "Address",
        secondary=event_address,
        backref='event_list',
        single_parent=True,
        cascade="all, delete, delete-orphan",
        order_by="Address.latitude.desc()",
        )
    eventtag_list = relationship(
        "Eventtag",
        secondary=event_eventtag,
        backref='event_list',
        cascade="save-update",
        order_by="Eventtag.name",
        )
    contact_list = relationship(
        "Contact",
        secondary=event_contact,
        backref='event_list',
        single_parent=True,
        cascade="all, delete, delete-orphan",
        )

    note_list_public = relationship(
        "Note",
        secondary=event_note,
        primaryjoin="Event.event_id == event_note.c.event_id",
        secondaryjoin=(
            "and_(Note.note_id == event_note.c.note_id, "
            "Note.public==True)"
            ),
        passive_deletes=True,
        )
    address_list_public = relationship(
        "Address",
        secondary=event_address,
        primaryjoin="Event.event_id == event_address.c.event_id",
        secondaryjoin=(
            "and_(Address.address_id == event_address.c.address_id, "
            "Address.public==True)"
            ),
        passive_deletes=True,
        order_by="Address.latitude.desc()",
        )
    eventtag_list_public = relationship(
        "Eventtag",
        secondary=event_eventtag,
        primaryjoin="Event.event_id == event_eventtag.c.event_id",
        secondaryjoin=(
            "and_(Eventtag.eventtag_id == event_eventtag.c.eventtag_id, "
            "Eventtag.public==True)"
            ),
        passive_deletes=True,
        order_by="Eventtag.name",
        )
    org_list_public = relationship(
        "Org",
        secondary=org_event,
        primaryjoin="Event.event_id == org_event.c.event_id",
        secondaryjoin=(
            "and_(Org.org_id == org_event.c.org_id, "
            "Org.public==True)"
            ),
        passive_deletes=True,
        )
    contact_list_public = relationship(
        "Contact",
        secondary=event_contact,
        primaryjoin="Event.event_id == event_contact.c.event_id",
        secondaryjoin=(
            "and_(Contact.contact_id == event_contact.c.contact_id, "
            "Contact.public==True)"
            ),
        passive_deletes=True,
        )

    content = [
        "name",
        "start_date",  # '..._date' causes formatting in 'obj()'
        "end_date",  # '..._date' causes formatting in 'obj()'
        "description",
        "start_time",  # '..._time' causes formatting in 'obj()'
        "end_time",  # '..._time' causes formatting in 'obj()'
        ]

    @classproperty
    @classmethod
    def entity_id(cls):
        return cls.event_id

    def __init__(self,
                 name, start_date, end_date,
                 description=None, start_time=None, end_time=None,
                 moderation_user=None, public=None):
        self.name = sanitise_name(name)
        self.start_date = start_date
        self.end_date = end_date

        self.description = description
        self.start_time = start_time
        self.end_time = end_time

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public

    def __unicode__(self):
        return u"<Event-%s (%s) '%s'>" % (
            self.event_id or "?",
            {True:"public", False:"private", None: "pending"}[self.public],
            self.name,
            )

    def pprint(self, indent=""):
        o = u"";
        o += u"%sEvent: %s %s\n" % (indent, self.event_id, self.name)
        for contact in self.contact_list:
            o += contact.pprint(indent + "  ")
        for eventtag in self.eventtag_list:
            o += eventtag.pprint(indent + "  ")
        for address in self.address_list:
            o += address.pprint(indent + "  ")
        for note in self.note_list:
            o += note.pprint(indent + "  ")
        for org in self.org_list:
            o += u"%sOrg: %s %s...\n" % (indent + "  ", org.org_id, org.name)
        return o

    @staticmethod
    def get(orm, name, moderation_user=None, public=None):
        name = sanitise_name(name)
        try:
            event = orm.query(Event).filter(Event.name == name).one()
        except NoResultFound:
            event = Event(
                name,
                moderation_user=moderation_user, public=public,
                )
            orm.add(event)
        return event



class AddressExtension(MapperExtension):
    def _sanitise(self, instance):
        instance.postal = sanitise_address(instance.postal)
        instance.lookup = sanitise_address(instance.lookup)

    def before_insert(self, mapper, connection, instance):
        self._sanitise(instance)

    def before_update(self, mapper, connection, instance):
        self._sanitise(instance)



class Address(Base, MangoEntity, NotableEntity):
    __tablename__ = 'address'
    __table_args__ = {
        'sqlite_autoincrement': True,
        "mysql_engine": 'InnoDB',
        }
    __mapper_args__ = {'extension': AddressExtension()}

    address_id = Column(Integer, primary_key=True)

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float(), nullable=False)
    public = Column(Boolean)

    postal = Column(Unicode(), nullable=False)
    source = Column(Unicode(), nullable=False)
    lookup = Column(Unicode())
    manual_longitude = Column(Float())
    manual_latitude = Column(Float())
    longitude = Column(Float())
    latitude = Column(Float())

    moderation_user = relationship(User, backref='moderation_address_list')
    
    note_list = relationship(
        "Note",
        secondary=address_note,
        backref='address_list',
        cascade="all, delete",
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
    event_list_public = relationship(
        "Event",
        secondary=event_address,
        primaryjoin="Address.address_id == event_address.c.address_id",
        secondaryjoin=(
            "and_(Event.event_id == event_address.c.event_id, "
            "Event.public==True)"
            ),
        passive_deletes=True,
        )

    content = [
        "postal",
        "source",
        "lookup",
        "manual_longitude",
        "manual_latitude",
        "longitude",
        "latitude",
        ]

    @staticmethod
    def obj_extra(obj):
        return {
            "name": obj["postal"].replace("\n", ", "),
            }

    @classproperty
    @classmethod
    def entity_id(cls):
        return cls.address_id

    def __init__(self,
                 postal, source,
                 lookup=None,
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
        return u"<Addr-%s (%s) '%s' '%s' %s %s>" % (
            self.address_id or "?",
            {True:"public", False:"private", None: "pending"}[self.public],
            self.postal[:10].replace("\n", " "),
            (self.lookup or "")[:10],
            self.repr_coordinates(self.manual_longitude, self.manual_latitude),
            self.repr_coordinates(self.longitude, self.latitude),
            )

    def geocode(self):
        if self.manual_longitude is not None and self.manual_latitude is not None:
            self.longitude = self.manual_longitude
            self.latitude = self.manual_latitude
            return
        
        if self.lookup:
            coords = geo.coords(self.lookup)
            if coords:
                (self.latitude, self.longitude) = coords
        else:
            coords = geo.coords(self.postal)
            if coords:
                (self.latitude, self.longitude) = coords

    def pprint(self, indent=""):
        o = u"";
        o += u"%sAddress: %s %s\n" % (indent, self.address_id, self.postal.split("\n")[0])
        for note in self.note_list:
            o += note.pprint(indent + "  ")
        return o

    @property
    def split(self):
        return filter(None, re.split("(?:\n|,)", self.postal))

    @property
    def name(self):
        return (self.split + [None])[0]

    @staticmethod
    def general(address):
        parts = Address.parts(address)
        for part in reversed(parts):
            if re.search("[\d]", part):
                continue
            return part
        return address

    @staticmethod
    def parts(address):
        return address.split("\n")

    @staticmethod
    def repr_coordinates(longitude, latitude):
        if longitude and latitude:
            return u"%0.2f°%s %0.2f°%s" % (
                abs(latitude), ("S", "", "N")[cmp(latitude, 0.0) + 1],
                abs(longitude), ("W", "", "E")[cmp(longitude, 0.0) + 1],
                )
        return ""
 
    @staticmethod
    def in_geobox(latitude, longitude, geobox):
        if latitude > geobox["latmax"]:
            return False
        if latitude < geobox["latmin"]:
            return False
        if longitude > geobox["lonmax"]:
            return False
        if longitude < geobox["lonmin"]:
            return False
        return True

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



class TagExtension(MapperExtension):
    def _set_name(self, instance):
        parts = instance.name.rsplit("|", 1)
        if len(parts) == 2:
            instance.path, instance.base = [part.strip() for part in parts]
        else:
            instance.path = None
            instance.base = instance.name
        instance.name_short = short_name(instance.name)
        instance.base_short = short_name(instance.base)
        instance.path_short = short_name(instance.path)

    def before_insert(self, mapper, connection, instance):
        self._set_name(instance)

    def before_update(self, mapper, connection, instance):
        self._set_name(instance)



class Orgtag(Base, MangoEntity, NotableEntity):
    u"""
    virtual:  None = normal
              True = virtual
              False = virtual, currently active in an event
    """

    __tablename__ = 'orgtag'
    __table_args__ = (
        UniqueConstraint('base_short'),    
        {
            'sqlite_autoincrement': True,
            "mysql_engine": 'InnoDB',
            }
        )
    __mapper_args__ = {'extension': TagExtension()}

    orgtag_id = Column(Integer, primary_key=True)

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float(), nullable=False)
    public = Column(Boolean)

    name = Column(Unicode(), nullable=False)
    name_short = Column(Unicode(), nullable=False)
    base = Column(Unicode(), nullable=False)
    base_short = Column(UnicodeKey(), nullable=False)
    path = Column(Unicode())
    path_short = Column(Unicode())
    description = Column(Unicode())
    virtual = Column(Boolean)

    moderation_user = relationship(User, backref='moderation_orgtag_list')

    note_list = relationship(
        "Note",
        secondary=orgtag_note,
        backref='orgtag_list',
        cascade="all, delete",
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

    content = [
        "name",
        "description",
        ]

    content_hints = [
        "name_short",
        "base",
        "base_short",
        "path",
        "path_short",
        "virtual",
        ]

    @classproperty
    @classmethod
    def entity_id(cls):
        return cls.orgtag_id

    def __init__(self,
                 name,
                 description=None,
                 moderation_user=None, public=None):
        self.name = sanitise_name(name)
        self.description = description and unicode(description) or None
        self.virtual = None

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public

    def __unicode__(self):
        return u"<Orgtag-%s (%s) '%s'>" % (
            self.orgtag_id or "?",
            {True:"public", False:"private", None: "pending"}[self.public],
            self.name,
            )

    def pprint(self, indent=""):
        o = u"";
        o += u"%sOrgtag: %s %s\n" % (indent, self.orgtag_id, self.name)
        for note in self.note_list:
            o += note.pprint(indent + "  ")
        return o

    @staticmethod
    def get(orm, name, moderation_user=None, public=None):
        try:
            orgtag = orm.query(Orgtag) \
                .filter(Orgtag.name==name) \
                .one()
        except NoResultFound:
            orgtag = Orgtag(
                name,
                moderation_user=moderation_user,
                public=public,
                )
            orm.add(orgtag)
        return orgtag

        

class Eventtag(Base, MangoEntity, NotableEntity):
    u"""
    virtual:  None = normal
              True = virtual
              False = virtual, currently active in an event
    """

    __tablename__ = 'eventtag'
    __table_args__ = (
        UniqueConstraint('base_short'),    
        {
            'sqlite_autoincrement': True,
            "mysql_engine": 'InnoDB',
            }
        )
    __mapper_args__ = {'extension': TagExtension()}

    eventtag_id = Column(Integer, primary_key=True)

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float(), nullable=False)
    public = Column(Boolean)

    name = Column(Unicode(), nullable=False)
    name_short = Column(Unicode(), nullable=False)
    base = Column(Unicode(), nullable=False)
    base_short = Column(UnicodeKey(), nullable=False)
    path = Column(Unicode())
    path_short = Column(Unicode())
    description = Column(Unicode())
    virtual = Column(Boolean)

    moderation_user = relationship(User, backref='moderation_eventtag_list')

    note_list = relationship(
        "Note",
        secondary=eventtag_note,
        backref='eventtag_list',
        cascade="all, delete",
        )

    note_list_public = relationship(
        "Note",
        secondary=eventtag_note,
        primaryjoin="Eventtag.eventtag_id == eventtag_note.c.eventtag_id",
        secondaryjoin=(
            "and_(Note.note_id == eventtag_note.c.note_id, "
            "Note.public==True)"
            ),
        passive_deletes=True,
        )
    event_list_public = relationship(
        "Event",
        secondary=event_eventtag,
        primaryjoin="Eventtag.eventtag_id == event_eventtag.c.eventtag_id",
        secondaryjoin=(
            "and_(Event.event_id == event_eventtag.c.event_id, "
            "Event.public==True)"
            ),
        passive_deletes=True,
        )

    content = [
        "name",
        "description",
        ]

    content_hints = [
        "name_short",
        "base",
        "base_short",
        "path",
        "path_short",
        "virtual",
        ]

    @classproperty
    @classmethod
    def entity_id(cls):
        return cls.eventtag_id

    def __init__(self,
                 name,
                 description=None,
                 moderation_user=None, public=None):
        self.name = sanitise_name(name)
        self.description = description and unicode(description) or None
        self.virtual = None

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public

    def __unicode__(self):
        return u"<Eventtag-%s (%s) '%s'>" % (
            self.eventtag_id or "?",
            {True:"public", False:"private", None: "pending"}[self.public],
            self.name,
            )

    def pprint(self, indent=""):
        o = u"";
        o += u"%sEventtag: %s %s\n" % (indent, self.eventtag_id, self.name)
        for note in self.note_list:
            o += note.pprint(indent + "  ")
        return o

    @staticmethod
    def get(orm, name, moderation_user=None, public=None):
        try:
            eventtag = orm.query(Eventtag) \
                .filter(Eventtag.name==name) \
                .one()
        except NoResultFound:
            eventtag = Eventtag(
                name,
                moderation_user=moderation_user,
                public=public,
                )
            orm.add(eventtag)
        return eventtag

        

class Note(Base, MangoEntity):
    __tablename__ = 'note'
    __table_args__ = {
        'sqlite_autoincrement': True,
        "mysql_engine": 'InnoDB',
        }

    note_id = Column(Integer, primary_key=True)

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float(), nullable=False)
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
    event_list_public = relationship(
        "Event",
        secondary=event_note,
        primaryjoin="Note.note_id == event_note.c.note_id",
        secondaryjoin=(
            "and_(Event.event_id == event_note.c.event_id, "
            "Event.public==True)"
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

    content = [
        "text",
        "source",
        ]

    @classproperty
    @classmethod
    def entity_id(cls):
        return cls.note_id

    def __init__(self,
                 text, source,
                 moderation_user=None, public=None):

        self.text = text
        self.source = source

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public

    def __unicode__(self):
        return u"<Note-%s (%s) '%s' '%s'>" % (
            self.note_id or "?",
            {True:"public", False:"private", None: "pending"}[self.public],
            self.text[:10].replace("\n", " "),
            self.source[:10],
            )

    def pprint(self, indent=""):
        o = u"";
        o += u"%sNote: %s %s\n" % (indent, self.note_id, self.text.split("\n")[0][:32])
        return o



class Contact(Base, MangoEntity):
    __tablename__ = 'contact'
    __table_args__ = {
        'sqlite_autoincrement': True,
        "mysql_engine": 'InnoDB',
        }

    contact_id = Column(Integer, primary_key=True)

    medium_id = Column(Integer, ForeignKey(Medium.medium_id), nullable=False)

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float(), nullable=False)
    public = Column(Boolean)

    text = Column(Unicode(), nullable=False)
    description = Column(Unicode())
    source = Column(Unicode())

    moderation_user = relationship(User, backref='moderation_contact_list')
    
    org_list_public = relationship(
        "Org",
        secondary=org_contact,
        primaryjoin="Contact.contact_id == org_contact.c.contact_id",
        secondaryjoin=(
            "and_(Org.org_id == org_contact.c.org_id, "
            "Org.public==True)"
            ),
        passive_deletes=True,
        )
    event_list_public = relationship(
        "Event",
        secondary=event_contact,
        primaryjoin="Contact.contact_id == event_contact.c.contact_id",
        secondaryjoin=(
            "and_(Event.event_id == event_contact.c.event_id, "
            "Event.public==True)"
            ),
        passive_deletes=True,
        )

    content = [
        "medium_id",
        "text",
        "description",
        "source",
        ]

    @classproperty
    @classmethod
    def entity_id(cls):
        return cls.contact_id

    def __init__(self,
                 medium,
                 text, description=None, source=None,
                 moderation_user=None, public=None):
        
        self.medium = medium

        self.text = sanitise_name(unicode(text))
        self.description = description and unicode(description)
        self.source = source and unicode(source)

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public

    def __unicode__(self):
        return u"<Contact-%s (%s) %s: '%s'>" % (
            self.contact_id or "?",
            {True:"public", False:"private", None: "pending"}[self.public],
            self.medium.name,
            self.text[:10].replace("\n", " "),
            )

    def pprint(self, indent=""):
        o = u"";
        o += u"%sContact: %s %s:%s\n" % (indent, self.contact_id, self.medium.name, self.text[:32])
        return o

    @property
    def name(self):
        return self.text



def attach_search(engine, orm, enabled=True):
    engine.search = None
    if not enabled:
        return
    engine.search = search.get_search()
    if not engine.search:
        return

    search.verify(engine.search, orm, Org, Orgalias)

def org_after_insert_listener(mapper, connection, target):
    if connection.engine.search:
        search.index_org(connection.engine.search, target)

def org_after_update_listener(mapper, connection, target):
    if connection.engine.search:
        search.index_org(connection.engine.search, target)

def org_after_delete_listener(mapper, connection, target):
    if connection.engine.search:
        search.delete_org(connection.engine.search, target)

def orgalias_after_insert_listener(mapper, connection, target):
    if connection.engine.search:
        orm = object_session(target)
        search.index_orgalias(connection.engine.search, target, orm, Orgalias)

def orgalias_after_update_listener(mapper, connection, target):
    if connection.engine.search:
        orm = object_session(target)
        search.index_orgalias(connection.engine.search, target, orm, Orgalias)

def orgalias_after_delete_listener(mapper, connection, target):
    if connection.engine.search:
        orm = object_session(target)
        search.index_orgalias(connection.engine.search, target, orm, Orgalias)

sqlalchemy_event.listen(Org, "after_insert", org_after_insert_listener)
sqlalchemy_event.listen(Org, "after_update", org_after_update_listener)
sqlalchemy_event.listen(Org, "after_delete", org_after_delete_listener)
sqlalchemy_event.listen(Orgalias, "after_insert", orgalias_after_insert_listener)
sqlalchemy_event.listen(Orgalias, "after_update", orgalias_after_update_listener)
sqlalchemy_event.listen(Orgalias, "after_delete", orgalias_after_delete_listener)


virtual_orgtag_list = [
    (
        u"Market | Military export applicant",
        Orgtag.name_short.like(
            u"market|military-export-applicant-to-%-in-%"),
    ),
    (
        u"Market | Military export applicant in 2010",
        Orgtag.name_short.like(
            u"market|military-export-applicant-to-%-in-2010"),
    ),
    (
        u"Market | Military export applicant in 2011",
        Orgtag.name_short.like(
            u"market|military-export-applicant-to-%-in-2011"),
    ),
    (
        u"Market | Military export applicant in 2012",
        Orgtag.name_short.like(
            u"market|military-export-applicant-to-%-in-2012"),
    ),
    (
        u"Exhibitor | DSEi",
        Orgtag.name_short.like(
            u"exhibitor|dsei-%"),
    ),
    (
        u"Activity | Military",
        Orgtag.path_short==u"activity",
    ),
]



def virtual_org_orgtag_all(org):
    if not virtual_orgtag_list:
        return

    orm = object_session(org)
    if not orm:
        raise Exception("Neither org or orgtag attached to session.")

    for virtual_name, filter_search in virtual_orgtag_list:
        log.debug(u"\nVirtual tag: %s" % (virtual_name))
        
        virtual_tag = orm.query(Orgtag) \
            .filter_by(name=virtual_name) \
            .filter_by(virtual=True) \
            .first()

        if not virtual_tag:
            log.debug(u"  Virtual tag does not exist.")
            continue

        has_virtual_tag = orm.query(Orgtag) \
            .join(Org, Orgtag.org_list) \
            .filter(Org.org_id==org.org_id) \
            .filter(Orgtag.virtual==None) \
            .filter(filter_search)

        log.debug(u"  Has %d child tags." % has_virtual_tag.count())
        if log.level == logging.DEBUG:
            for child_tag in has_virtual_tag:
                log.debug(u"    %s" % child_tag.name_short)

        if has_virtual_tag.count():
            if virtual_tag not in org.orgtag_list:
                log.debug(u"  Adding parent tag.")
                # Flag the virtual tag so it doesn't trigger a value error
                virtual_tag.virtual = False
                org.orgtag_list.append(virtual_tag)
            else:
                log.debug(u"  Already has parent tag.")
        else:
            if virtual_tag in org.orgtag_list:
                log.debug(u"  Removing parent tag.")
                # Flag the virtual tag so it doesn't trigger a value error
                virtual_tag.virtual = False
                org.orgtag_list.remove(virtual_tag)
            else:
                log.debug(u"  Doesn't have parent tag.")

    

def virtual_org_orgtag_edit(org, orgtag, add=None):
    """
    Gets called:
      before the orgtag is appended,
      after the orgtag is removed.
    """

    if not virtual_orgtag_list:
        return

    if orgtag.virtual:
        log.warning(u"Cannot edit the membership of a virtual tag (%s).", orgtag.name)
        return

    if orgtag.virtual is False:
        # We're adding a virtual tag for a parent function call
        orgtag.virtual = True
        return

    orm = object_session(org) or object_session(orgtag)
    if not orm:
        raise Exception("Neither org or orgtag attached to session.")

    for virtual_name, filter_search in virtual_orgtag_list:
        virtual_tag = orm.query(Orgtag) \
            .filter_by(name=virtual_name) \
            .filter_by(virtual=True) \
            .first()

        if not virtual_tag:
            continue

        has_virtual_tag_this = orm.query(Orgtag) \
            .filter(Orgtag.orgtag_id==orgtag.orgtag_id) \
            .filter(filter_search)

        has_virtual_tag_others = orm.query(Orgtag) \
            .join(Org, Orgtag.org_list) \
            .filter(Org.org_id==org.org_id) \
            .filter(filter_search)

        if ((add and has_virtual_tag_this.count()) or has_virtual_tag_others.count()):
            if virtual_tag not in org.orgtag_list:
                # Flag the virtual tag so it doesn't trigger a value error
                virtual_tag.virtual = False
                org.orgtag_list.append(virtual_tag)
                return
        else:
            if virtual_tag in org.orgtag_list:
                # Flag the virtual tag so it doesn't trigger a value error
                virtual_tag.virtual = False
                org.orgtag_list.remove(virtual_tag)
                return



def org_orgtag_append_listener(org, orgtag, initiator):
    virtual_org_orgtag_edit(org, orgtag, add=True)

def org_orgtag_remove_listener(org, orgtag, initiator):
    virtual_org_orgtag_edit(org, orgtag, add=False)

sqlalchemy_event.listen(Org.orgtag_list, 'append', org_orgtag_append_listener)
sqlalchemy_event.listen(Org.orgtag_list, 'remove', org_orgtag_remove_listener)



if __name__ == '__main__':
    connection_url = connection_url_admin()
    engine = create_engine(connection_url)
    Base.metadata.create_all(engine)

    database = conf.get(conf_path, u"database", u"database")
            

    



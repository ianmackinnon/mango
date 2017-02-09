#!/usr/bin/env python3

# pylint: disable=invalid-name
# Allow using lambdas for MySQL global column types
# and lowercase association table names for SQLAlchemy declarative

import os
import re
import csv
import math
import time
import argparse
import logging
import datetime
from hashlib import sha1, md5

from sqlalchemy import create_engine
from sqlalchemy import Column, Table, text
from sqlalchemy import ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship, object_session, reconstructor
from sqlalchemy.orm.util import has_identity
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

from sqlalchemy import Boolean, Integer, Float as FloatOrig, Date, Time
from sqlalchemy import Unicode as UnicodeOrig, String as StringOrig
from sqlalchemy.dialects.mysql import LONGTEXT, DOUBLE, VARCHAR
from sqlalchemy import event as sqla_event

from tornado.web import HTTPError

from mysql import mysql

import geo

from search import search



LOG = logging.getLogger('model')

Base = declarative_base()

Float = lambda: FloatOrig
String = lambda: StringOrig
Unicode = lambda: UnicodeOrig
StringKey = lambda: StringOrig
UnicodeKey = lambda: UnicodeOrig
MYSQL_MAX_KEY = 255

CONF_PATH = ".mango.conf"
DATABASE_NAMES = mysql.load_database_names(CONF_PATH)

SYSTEM_USER_ID = -1
IGNORE_ORG_NAME_WORDS = None
IGNORE_ORG_NAME_CSV_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "search/ignore_words.csv"
)



def load_csv():
    global IGNORE_ORG_NAME_WORDS

    with open(IGNORE_ORG_NAME_CSV_PATH, "r", encoding="utf-8") as fp:
        reader = csv.reader(fp)
        IGNORE_ORG_NAME_WORDS = set([v[0] for v in reader if v])



load_csv()



def use_mysql():
    global Float, String, Unicode, StringKey, UnicodeKey
    Float = DOUBLE
    String = lambda: LONGTEXT(charset="latin1", collation="latin1_swedish_ci")
    Unicode = lambda: LONGTEXT(charset="utf8", collation="utf8_bin")
    # MySQL needs a character limit to use a variable-length column as a key.
    StringKey = lambda: VARCHAR(
        length=MYSQL_MAX_KEY,
        charset="latin1", collation="latin1_swedish_ci")
    UnicodeKey = lambda: VARCHAR(
        length=MYSQL_MAX_KEY,
        charset="utf8", collation="utf8_bin")



def main_1():
    LOG.addHandler(logging.StreamHandler())
    search.log.addHandler(logging.StreamHandler())

    parser = argparse.ArgumentParser(
        description="Initialize database.")
    parser.add_argument(
        "--verbose", "-v",
        action="count", default=0,
        help="Print verbose information for debugging.")
    parser.add_argument(
        "--quiet", "-q",
        action="count", default=0,
        help="Suppress warnings.")

    args = parser.parse_args()

    level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[
        max(0, min(3, 1 + args.verbose - args.quiet))]
    LOG.setLevel(level)
    search.log.setLevel(level)

    use_mysql()



if __name__ == '__main__':
    main_1()



def camel_case(text_):
    parts = re.split("_", text_)
    out = parts.pop(0)
    for part in parts:
        out += part[:1].upper()
        out += part[1:].lower()
    return out



def split_words(text_):
    if not text_:
        return set()

    text_ = text_.lower()
    text_ = re.compile(r"\.(\w)", re.U).sub(r"\1", text_)
    text_ = re.compile(r"['`\"]", re.U).sub(r"", text_)
    text_ = re.compile(r"[\W\s]+", re.U).sub(r"-", text_)
    text_ = text_.strip("-")

    words = text_.split("-")

    return set(words)



def short_name(name, allow_end_pipe=False):
    """
    Accept letters and numbers in all alphabets, converting to lower case.
    Reject symbols except '-'.
    Use '|' as a namespace separator.
    """
    if not name:
        return name
    short = name.lower()
    short = re.compile(r"[-_/]", re.U).sub(" ", short)
    short = re.compile(r"[^\w\s\|]", re.U).sub("", short)
    short = re.compile(r"[\s]+", re.U).sub(" ", short)
    short = short.strip()
    short = re.compile(r"[\s]*\|[\s]*", re.U).sub("|", short)
    short = re.compile(r"\|+", re.U).sub("|", short)
    if not allow_end_pipe:
        short = re.compile(r"(^\||\|$)", re.U).sub("", short)
    short = re.compile(r"[\s]", re.U).sub("-", short)
    return short



def sanitise_name(name):
    return re.sub(r"[\s]+", " ", name).strip()



def sanitise_address(address, allow_commas=True):
    if not address:
        return address
    address = re.sub(r"(\r|\n)+", "\n", address)
    address = re.sub(r"(^|\n)[\s,]+", "\n", address)
    address = re.sub(r"[\s,]+($|\n)", "\n", address)
    if (not allow_commas) or ("\n" not in address):
        address = re.sub(r"(,|\n)+", "\n", address)
        address = re.sub(r"(^|\n)[\s,]+", "\n", address)
        address = re.sub(r"[\s,]+($|\n)", "\n", address)
    address = re.sub(r"[ \t]+", " ", address).strip()
    return address



def assert_session_is_fresh(session):
    assert not session.new, \
        "Session has new objects: %s" % repr(session.new)
    assert not session.dirty, \
        "Session has dirty objects: %s" % repr(session.dirty)
    assert not session.deleted, \
        "Session has deleted objects: %s" % repr(session.deleted)



def detach(entity):
    session = object_session(entity)
    if session and not has_identity(entity):
        session.expunge(entity)



def gravatar_hash(plaintext):
    return md5(plaintext.encode("utf-8")).hexdigest()



def generate_hash(plaintext):
    "Generate a pseudorandom 40 digit hexadecimal hash using SHA1"
    return sha1(plaintext.encode("utf-8")).hexdigest()



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
    # pylint: disable=invalid-name
    # Allow lowercase class name for a decorator
    def __get__(self, cls, owner):
        # pylint: disable=no-member
        # (`fget.__get__` is generated)
        return self.fget.__get__(None, owner)()



URL_DIRECTORY = {
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

    # Override in child class
    content = None
    a_time = None
    public = None
    entity_id = None
    entity_v_id = None
    obj_extra = None
    __tablename__ = None

    def __init__(self):
        self.moderation_user = None

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
        name = URL_DIRECTORY[self.__tablename__]
        if not name:
            raise HTTPError(
                500, "No URL space for type '%s'." % self.__tablename__)
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

        if getattr(self, "entity_v_id", None):
            obj.update({
                "vId": self.entity_v_id_value,
                "suggestion": True,
            })

        if bool(kwargs.pop("public", None)):
            obj["public"] = self.public

        for name in self.content + self.content_hints:
            if kwargs.pop(name, None) is False:
                continue
            value = getattr(self, name)
            if name.endswith("_date") and value:
                value = value.strftime("%Y-%m-%d")
            if name.endswith("_time") and value:
                value = value.strftime("%H:%M")

            obj[camel_case(name)] = value

        if getattr(self, "obj_extra", None):
            # pylint: disable=not-callable
            # (`self.obj_extra` may be `None`)
            obj.update(self.obj_extra(obj))

        for name, value in list(kwargs.items()):
            obj[camel_case(name)] = value

        return obj

    @property
    def entity_id_value(self):
        return (getattr(self, "entity_id", None) and
                getattr(self, self.entity_id.key, None))

    @property
    def entity_v_id_value(self):
        return (getattr(self, "entity_v_id", None) and
                getattr(self, self.entity_v_id.key, None))




class NotableEntity(object):

    @property
    def note_list_query(self):
        return object_session(self) \
            .query(Note).with_parent(self, "note_list")

    def note_list_filtered(
            self,
            note_search=None,
            note_order=None,
            all_visible=None,
            note_offset=None,
            note_limit=None
    ):
        query = self.note_list_query
        if not all_visible:
            # pylint: disable=singleton-comparison
            # Cannot use `is` in SQLAlchemy filters
            query = query \
                .filter(Note.public == True)
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

        if note_offset is not None:
            query = query.offset(note_offset)

        count = query.count()

        if note_limit is not None:
            query = query.limit(note_limit)

        return query, count



address_note = Table(
    'address_note', Base.metadata,
    Column('address_id', Integer, ForeignKey('address.address_id'),
           primary_key=True),
    Column('note_id', Integer, ForeignKey('note.note_id'), primary_key=True),
    Column('a_time', Float(), nullable=False, server_default=text("0")),
    mysql_engine='InnoDB',
)



org_note = Table(
    'org_note', Base.metadata,
    Column('org_id', Integer, ForeignKey('org.org_id'), primary_key=True),
    Column('note_id', Integer, ForeignKey('note.note_id'), primary_key=True),
    Column('a_time', Float(), nullable=False, server_default=text("0")),
    mysql_engine='InnoDB',
)



event_note = Table(
    'event_note', Base.metadata,
    Column('event_id', Integer, ForeignKey('event.event_id'), primary_key=True),
    Column('note_id', Integer, ForeignKey('note.note_id'), primary_key=True),
    Column('a_time', Float(), nullable=False, server_default=text("0")),
    mysql_engine='InnoDB',
)



orgtag_note = Table(
    'orgtag_note', Base.metadata,
    Column('orgtag_id', Integer, ForeignKey('orgtag.orgtag_id'),
           primary_key=True),
    Column('note_id', Integer, ForeignKey('note.note_id'), primary_key=True),
    Column('a_time', Float(), nullable=False, server_default=text("0")),
    mysql_engine='InnoDB',
    )



eventtag_note = Table(
    'eventtag_note', Base.metadata,
    Column('eventtag_id', Integer, ForeignKey('eventtag.eventtag_id'),
           primary_key=True),
    Column('note_id', Integer, ForeignKey('note.note_id'), primary_key=True),
    Column('a_time', Float(), nullable=False, server_default=text("0")),
    mysql_engine='InnoDB',
)



org_address = Table(
    'org_address', Base.metadata,
    Column('org_id', Integer, ForeignKey('org.org_id'), primary_key=True),
    Column('address_id', Integer, ForeignKey('address.address_id'),
           primary_key=True),
    Column('a_time', Float(), nullable=False, server_default=text("0")),
    mysql_engine='InnoDB',
)



event_address = Table(
    'event_address', Base.metadata,
    Column('event_id', Integer, ForeignKey('event.event_id'), primary_key=True),
    Column('address_id', Integer, ForeignKey('address.address_id'),
           primary_key=True),
    Column('a_time', Float(), nullable=False, server_default=text("0")),
    mysql_engine='InnoDB',
)



org_orgtag = Table(
    'org_orgtag', Base.metadata,
    Column('org_id', Integer, ForeignKey('org.org_id'), primary_key=True),
    Column('orgtag_id', Integer, ForeignKey('orgtag.orgtag_id'),
           primary_key=True),
    Column('a_time', Float(), nullable=False, server_default=text("0")),
    mysql_engine='InnoDB',
)



event_eventtag = Table(
    'event_eventtag', Base.metadata,
    Column('event_id', Integer, ForeignKey('event.event_id'), primary_key=True),
    Column('eventtag_id', Integer, ForeignKey('eventtag.eventtag_id'),
           primary_key=True),
    Column('a_time', Float(), nullable=False, server_default=text("0")),
    mysql_engine='InnoDB',
)



org_event = Table(
    'org_event', Base.metadata,
    Column('org_id', Integer, ForeignKey('org.org_id'), primary_key=True),
    Column('event_id', Integer, ForeignKey('event.event_id'), primary_key=True),
    Column('a_time', Float(), nullable=False, server_default=text("0")),
    mysql_engine='InnoDB',
)



org_contact = Table(
    'org_contact', Base.metadata,
    Column('org_id', Integer, ForeignKey('org.org_id'), primary_key=True),
    Column('contact_id', Integer, ForeignKey('contact.contact_id'),
           primary_key=True),
    Column('a_time', Float(), nullable=False, server_default=text("0")),
    mysql_engine='InnoDB',
)



event_contact = Table(
    'event_contact', Base.metadata,
    Column('event_id', Integer, ForeignKey('event.event_id'), primary_key=True),
    Column('contact_id', Integer, ForeignKey('contact.contact_id'),
           primary_key=True),
    Column('a_time', Float(), nullable=False, server_default=text("0")),
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
        self.url = str(url)
        self.name_hash = generate_hash(name)
        self.gravatar_hash = gravatar_hash(name)

    @staticmethod
    def get(orm, url, name):
        url = str(url)
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
            "mysql_engine": 'InnoDB',
            }
        )

    user_id = Column(Integer, primary_key=True)
    auth_id = Column(Integer, ForeignKey(Auth.auth_id), nullable=True)

    name = Column(Unicode(), nullable=False)

    moderator = Column(Boolean, nullable=False, server_default=text("0"))

    locked = Column(Boolean, nullable=False, server_default=text("0"))

    auth = relationship(Auth, backref='user_list')

    def __init__(self, auth, name, moderator=False, locked=False):
        self.auth = auth
        self.name = sanitise_name(name)
        self.moderator = moderator
        self.locked = locked

    def verify_auth_name(self, auth_name):
        return verify_hash(auth_name, self.auth.name_hash)

    def gravatar_hash(self):
        return self.auth.gravatar_hash if self.auth \
            else gravatar_hash(str(self.user_id))

    @staticmethod
    def get_from_auth(session, auth_url, auth_name):
        auth_name_hash = generate_hash(auth_name)
        try:
            user = session.query(User).join(Auth).\
                filter_by(url=auth_url).\
                filter_by(name_hash=auth_name_hash).\
                one()
        except NoResultFound:
            user = None
        return user

    @staticmethod
    def get(orm, auth, name):
        name = str(name)

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

    def __init__(self, user,
                 ip_address=None, accept_language=None, user_agent=None):
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
        self.name = str(name)



class Org(Base, MangoEntity, NotableEntity):
    __tablename__ = 'org'
    __table_args__ = {
        "mysql_engine": 'InnoDB',
        }

    org_id = Column(Integer, primary_key=True)

    name = Column(UnicodeKey(), nullable=False, index=True)
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

    @classmethod
    def _dummy(cls, _orm):
        return cls("dummy")

    @reconstructor
    def _reconstruct(self):
        # pylint: disable=attribute-defined-outside-init
        # Called by SQLAlchemy at instantiation

        self._calc_av = None     # Last time of alias visibility calculation.

    def __init__(self,
                 name, description=None, end_date=None,
                 moderation_user=None, public=None):
        super(Org, self).__init__()

        self.name = sanitise_name(name)

        self.description = description and str(description) or None
        self.end_date = end_date

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public

    def __unicode__(self):
        return "<Org-%s (%s) '%s'>" % (
            self.org_id or "?",
            {True:"public", False:"private", None: "pending"}[self.public],
            self.name,
            )

    def pprint(self, indent=""):
        o = ""
        o += "%sOrg: %s %s\n" % (indent, self.org_id, self.name)
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
            o += "%sEvent: %s %s...\n" % (
                indent + "  ", event.event_id, event.name)
        return o

    def merge(self, other, moderation_user):
        "Merge other into self. Does not re-link pending versions."

        session = object_session(self)
        assert session

        print(("[", self.org_id, other.org_id, len(other.orgalias_list), "]"))

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
            print((alias.orgalias_id, alias.org_id, alias.name))

        orgalias = Orgalias.get(
            session, other.name, self, moderation_user, other.public)

        session.add(orgalias)

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
        super(Orgalias, self).__init__()

        self.name = sanitise_name(name)
        self.org = org

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public

    def __unicode__(self):
        return "<Orgalias-%s (%s) '%s':%d>" % (
            self.orgalias_id or "?",
            {True:"public", False:"private", None: "pending"}[self.public],
            self.name, self.org_id,
            )

    def pprint(self, indent=""):
        o = ""
        o += "%sOrgalias: %s %s\n" % (indent, self.orgalias_id, self.name)
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
            "mysql_engine": 'InnoDB',
            },
        )
    event_id = Column(Integer, primary_key=True)

    name = Column(Unicode(), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(
        Date,
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

    @classmethod
    def _dummy(cls, _orm):
        return cls("dummy",
                   datetime.date(1970, 1, 1), datetime.date(1970, 1, 1))

    def __init__(self,
                 name, start_date, end_date,
                 description=None, start_time=None, end_time=None,
                 moderation_user=None, public=None):
        super(Event, self).__init__()

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
        return "<Event-%s (%s) '%s'>" % (
            self.event_id or "?",
            {True:"public", False:"private", None: "pending"}[self.public],
            self.name,
            )

    def pprint(self, indent=""):
        o = ""
        o += "%sEvent: %s %s\n" % (indent, self.event_id, self.name)
        for contact in self.contact_list:
            o += contact.pprint(indent + "  ")
        for eventtag in self.eventtag_list:
            o += eventtag.pprint(indent + "  ")
        for address in self.address_list:
            o += address.pprint(indent + "  ")
        for note in self.note_list:
            o += note.pprint(indent + "  ")
        for org in self.org_list:
            o += "%sOrg: %s %s...\n" % (indent + "  ", org.org_id, org.name)
        return o

    @staticmethod
    def get(orm, name, start_date, end_date, moderation_user=None, public=None):
        name = sanitise_name(name)
        try:
            event = orm.query(Event).filter(Event.name == name).one()
        except NoResultFound:
            event = Event(
                name, start_date, end_date,
                moderation_user=moderation_user, public=public,
                )
            orm.add(event)
        return event



class Address(Base, MangoEntity, NotableEntity):
    __tablename__ = 'address'
    __table_args__ = {
        "mysql_engine": 'InnoDB',
        }

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

    @classmethod
    def _dummy(cls, _orm):
        return cls("dummy", "dummy", "dummy")

    def __init__(self,
                 postal, source,
                 lookup=None,
                 manual_longitude=None, manual_latitude=None,
                 longitude=None, latitude=None,
                 moderation_user=None, public=None):
        super(Address, self).__init__()

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
        return "<Addr-%s (%s) '%s' '%s' %s %s>" % (
            self.address_id or "?",
            {True:"public", False:"private", None: "pending"}[self.public],
            self.postal[:10].replace("\n", " "),
            (self.lookup or "")[:10],
            self.repr_coordinates(self.manual_longitude, self.manual_latitude),
            self.repr_coordinates(self.longitude, self.latitude),
            )

    def geocode(self):
        if (
                self.manual_longitude is not None and
                self.manual_latitude is not None
        ):
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
        o = ""
        o += "%sAddress: %s %s\n" % (
            indent, self.address_id, self.postal.split("\n")[0])
        for note in self.note_list:
            o += note.pprint(indent + "  ")
        return o

    @property
    def split(self):
        return [_f for _f in re.split("(?:\n|,)", self.postal) if _f]

    @property
    def name(self):
        return (self.split + [None])[0]

    @staticmethod
    def general(address):
        parts = Address.parts(address)
        for part in reversed(parts):
            if re.search(r"[\d]", part):
                continue
            return part
        return address

    @staticmethod
    def parts(address):
        return address.split("\n")

    @staticmethod
    def repr_coordinates(longitude, latitude):
        def cmp(a, b):
            return (a > b) - (a < b)
        if longitude and latitude:
            return "%0.2f°%s %0.2f°%s" % (
                abs(latitude), ("S", "", "N")[cmp(latitude, 0.0) + 1],
                abs(longitude), ("W", "", "E")[cmp(longitude, 0.0) + 1],
                )
        return ""

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



class Orgtag(Base, MangoEntity, NotableEntity):
    """
    is_virtual:  None = normal
                 True = virtual
                 False = virtual, currently active in an event
    """

    __tablename__ = 'orgtag'
    __table_args__ = (
        UniqueConstraint('base_short'),
        {
            "mysql_engine": 'InnoDB',
            }
        )

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
    is_virtual = Column(Boolean)

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
        "is_virtual",
        ]

    @classproperty
    @classmethod
    def entity_id(cls):
        return cls.orgtag_id

    def __init__(self,
                 name,
                 description=None,
                 moderation_user=None, public=None):
        super(Orgtag, self).__init__()

        self.name = sanitise_name(name)
        self.description = description and str(description) or None
        self.is_virtual = None

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public

    def __unicode__(self):
        return "<Orgtag-%s (%s) '%s'>" % (
            self.orgtag_id or "?",
            {True:"public", False:"private", None: "pending"}[self.public],
            self.name,
            )

    def pprint(self, indent=""):
        o = ""
        o += "%sOrgtag: %s %s\n" % (indent, self.orgtag_id, self.name)
        for note in self.note_list:
            o += note.pprint(indent + "  ")
        return o

    @staticmethod
    def get(orm, name, moderation_user=None, public=None):
        try:
            orgtag = orm.query(Orgtag) \
                .filter(Orgtag.name == name) \
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
    """
    is_virtual:  None = normal
                 True = virtual
                 False = virtual, currently active in an event
    """

    __tablename__ = 'eventtag'
    __table_args__ = (
        UniqueConstraint('base_short'),
        {
            "mysql_engine": 'InnoDB',
            }
        )

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
    is_virtual = Column(Boolean)

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
        "is_virtual",
        ]

    @classproperty
    @classmethod
    def entity_id(cls):
        return cls.eventtag_id

    def __init__(self,
                 name,
                 description=None,
                 moderation_user=None, public=None):
        super(Eventtag, self).__init__()

        self.name = sanitise_name(name)
        self.description = description and str(description) or None
        self.is_virtual = None

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public

    def __unicode__(self):
        return "<Eventtag-%s (%s) '%s'>" % (
            self.eventtag_id or "?",
            {True:"public", False:"private", None: "pending"}[self.public],
            self.name,
            )

    def pprint(self, indent=""):
        o = ""
        o += "%sEventtag: %s %s\n" % (indent, self.eventtag_id, self.name)
        for note in self.note_list:
            o += note.pprint(indent + "  ")
        return o

    @staticmethod
    def get(orm, name, moderation_user=None, public=None):
        try:
            eventtag = orm.query(Eventtag) \
                .filter(Eventtag.name == name) \
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

    @classmethod
    def _dummy(cls, _orm):
        return cls("dummy", "dummy")

    def __init__(self,
                 text_, source,
                 moderation_user=None, public=None):

        super(Note, self).__init__()

        self.text = text_
        self.source = source

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public

    def __unicode__(self):
        return "<Note-%s (%s) '%s' '%s'>" % (
            self.note_id or "?",
            {True:"public", False:"private", None: "pending"}[self.public],
            self.text[:10].replace("\n", " "),
            self.source[:10],
            )

    def pprint(self, indent=""):
        o = ""
        o += "%sNote: %s %s\n" % (
            indent, self.note_id, self.text.split("\n")[0][:32])
        return o



class Contact(Base, MangoEntity):
    __tablename__ = 'contact'
    __table_args__ = {
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

    @classmethod
    def _dummy(cls, orm):
        medium = orm.query(Medium).first()
        return cls(medium, "dummy")

    def __init__(self,
                 medium,
                 text_, description=None, source=None,
                 moderation_user=None, public=None):

        super(Contact, self).__init__()

        self.medium = medium

        self.text = sanitise_name(str(text_))
        self.description = description and str(description)
        self.source = source and str(source)

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public

    def __unicode__(self):
        return "<Contact-%s (%s) %s: '%s'>" % (
            self.contact_id or "?",
            {True:"public", False:"private", None: "pending"}[self.public],
            self.medium.name,
            self.text[:10].replace("\n", " "),
            )

    def pprint(self, indent=""):
        o = ""
        o += "%sContact: %s %s:%s\n" % (
            indent, self.contact_id, self.medium.name, self.text[:32])
        return o

    @property
    def name(self):
        return self.text



def attach_search(engine, orm, enabled=True, verify=True):
    engine.search = None
    if not enabled:
        return
    engine.search = search.get_search()
    if not engine.search:
        return

    if verify:
        search.verify(engine.search, orm, Org, Orgalias)



VIRTUAL_ORGTAG_LIST = [
    (
        "Market | Military export applicant",
        Orgtag.name_short.like(
            "market|military-export-applicant-to-%-in-%"),
    ),
    (
        "Exhibitor | DSEi",
        Orgtag.name_short.like(
            "exhibitor|dsei-%"),
    ),
    (
        "Exhibitor | Farnborough",
        Orgtag.name_short.like(
            "exhibitor|farnborough-%"),
    ),
    (
        "Activity | Military",
        Orgtag.path_short == "activity",
    ),
]



def virtual_org_orgtag_all(org):
    # pylint: disable=singleton-comparison
    # Cannot use `is` in SQLAlchemy filters

    if not VIRTUAL_ORGTAG_LIST:
        return

    orm = object_session(org)
    if not orm:
        raise Exception("Neither org or orgtag attached to session.")

    for virtual_name, filter_search in VIRTUAL_ORGTAG_LIST:
        LOG.debug("\nVirtual tag: %s", virtual_name)

        virtual_tag = orm.query(Orgtag) \
            .filter_by(name=virtual_name) \
            .filter_by(is_virtual=True) \
            .first()

        if not virtual_tag:
            LOG.debug("  Virtual tag does not exist.")
            continue

        has_virtual_tag = orm.query(Orgtag) \
            .join(Org, Orgtag.org_list) \
            .filter(Org.org_id == org.org_id) \
            .filter(Orgtag.is_virtual == None) \
            .filter(filter_search)

        LOG.debug("  Has %d child tags.", has_virtual_tag.count())
        if LOG.level == logging.DEBUG:
            for child_tag in has_virtual_tag:
                LOG.debug("    %s", child_tag.name_short)

        if has_virtual_tag.count():
            if virtual_tag not in org.orgtag_list:
                LOG.debug("  Adding parent tag.")
                # Flag the virtual tag so it doesn't trigger a value error
                virtual_tag.is_virtual = False
                org.orgtag_list.append(virtual_tag)
            else:
                LOG.debug("  Already has parent tag.")
        else:
            if virtual_tag in org.orgtag_list:
                LOG.debug("  Removing parent tag.")
                # Flag the virtual tag so it doesn't trigger a value error
                virtual_tag.is_virtual = False
                org.orgtag_list.remove(virtual_tag)
            else:
                LOG.debug("  Doesn't have parent tag.")



def virtual_org_orgtag_edit(org, orgtag, add=None):
    """
    Gets called:
      before the orgtag is appended,
      after the orgtag is removed.
    """

    if not VIRTUAL_ORGTAG_LIST:
        return

    if orgtag.is_virtual:
        LOG.warning("Cannot edit the membership of a virtual tag (%s).",
                    orgtag.name)
        return

    if orgtag.is_virtual is False:
        # We're adding a virtual tag for a parent function call
        orgtag.is_virtual = True
        return

    orm = object_session(org) or object_session(orgtag)
    if not orm:
        raise Exception("Neither org or orgtag attached to session.")

    for virtual_name, filter_search in VIRTUAL_ORGTAG_LIST:
        virtual_tag = orm.query(Orgtag) \
            .filter_by(name=virtual_name) \
            .filter_by(is_virtual=True) \
            .first()

        if not virtual_tag:
            continue

        has_virtual_tag_this = orm.query(Orgtag) \
            .filter(Orgtag.orgtag_id == orgtag.orgtag_id) \
            .filter(filter_search)

        has_virtual_tag_others = orm.query(Orgtag) \
            .filter_by(is_virtual=None) \
            .join(Org, Orgtag.org_list) \
            .filter(Org.org_id == org.org_id) \
            .filter(filter_search)


        if (
                (add and has_virtual_tag_this.count()) or
                has_virtual_tag_others.count()
        ):
            if virtual_tag not in org.orgtag_list:
                # Flag the virtual tag so it doesn't trigger a value error
                virtual_tag.is_virtual = False
                org.orgtag_list.append(virtual_tag)
        else:
            if virtual_tag in org.orgtag_list:
                # Flag the virtual tag so it doesn't trigger a value error
                virtual_tag.is_virtual = False
                org.orgtag_list.remove(virtual_tag)



def calculate_orgalias_visibility(org, connection=False):
    """
    `connection` can be supplied if we're being called from within
    a flush (eg. in an event handler).
    Otherwise, changes will be made to models without committing.
    """
    # pylint: disable=protected-access

    if org._calc_av == org.a_time:
        return

    org_words = split_words(org.name)
    orgalias_list = org.orgalias_list

    # Order by public first, then shortest name
    orgalias_list.sort(key=lambda x: (not x.public, len(x.name)))

    for orgalias in orgalias_list:
        if orgalias.public is False:
            continue
        values = {}
        words = split_words(orgalias.name) - IGNORE_ORG_NAME_WORDS
        new_words = words - org_words
        if new_words:
            org_words |= new_words
            if orgalias.public is None:
                LOG.debug(
                    "    Set public `%s` with new words `%s`.",
                    orgalias.name, new_words)
                values["public"] = True
                values["moderation_user_id"] = SYSTEM_USER_ID
        elif (
                orgalias.moderation_user_id == SYSTEM_USER_ID and
                orgalias.public
        ):
            values["public"] = None
            LOG.debug(
                "    Set pending `%s`",
                orgalias.name)

        if values:
            if connection:
                connection.execute(
                    Orgalias.__table__.update().
                    where(Orgalias.orgalias_id == orgalias.orgalias_id).
                    values(values)
                )
            else:
                for key, value in values.items():
                    setattr(orgalias, key, value)

    org._calc_av = org.a_time





def org_after_insert_listener(_mapper, connection, target):
    if connection.engine.search:
        search.index_org(connection.engine.search, target)

def org_after_update_listener(_mapper, connection, target):
    if connection.engine.search:
        search.index_org(connection.engine.search, target)


def org_after_delete_listener(_mapper, connection, target):
    if connection.engine.search:
        search.delete_org(connection.engine.search, target)


def orgalias_listener(_mapper, connection, target):
    calculate_orgalias_visibility(target.org, connection=connection)
    if connection.engine.search:
        orm = object_session(target)
        search.index_orgalias(connection.engine.search, target, orm, Orgalias)


def address_sanitise_listener(_mapper, _connection, address):
    address.postal = sanitise_address(address.postal)
    address.lookup = sanitise_address(address.lookup)


def tag_set_name_listener(_mapper, _connection, tag):
    parts = tag.name.rsplit("|", 1)
    if len(parts) == 2:
        tag.path, tag.base = [part.strip() for part in parts]
    else:
        tag.path = None
        tag.base = tag.name
    tag.name_short = short_name(tag.name)
    tag.base_short = short_name(tag.base)
    tag.path_short = short_name(tag.path)

def org_orgtag_append_listener(org, orgtag, _initiator):
    virtual_org_orgtag_edit(org, orgtag, add=True)

def org_orgtag_remove_listener(org, orgtag, _initiator):
    virtual_org_orgtag_edit(org, orgtag, add=False)


sqla_event.listen(Org, "after_insert", org_after_insert_listener)
sqla_event.listen(Org, "after_update", org_after_update_listener)
sqla_event.listen(Org, "after_delete", org_after_delete_listener)

for event_name in ("after_insert", "after_update", "after_delete"):
    sqla_event.listen(Orgalias, event_name, orgalias_listener)

sqla_event.listen(Address, 'before_insert', address_sanitise_listener)
sqla_event.listen(Address, 'before_update', address_sanitise_listener)

sqla_event.listen(Orgtag, 'before_insert', tag_set_name_listener)
sqla_event.listen(Orgtag, 'before_update', tag_set_name_listener)
sqla_event.listen(Eventtag, 'before_insert', tag_set_name_listener)
sqla_event.listen(Eventtag, 'before_update', tag_set_name_listener)

sqla_event.listen(Org.orgtag_list, 'append', org_orgtag_append_listener)
sqla_event.listen(Org.orgtag_list, 'remove', org_orgtag_remove_listener)




# Main again

def engine_sql_mode(engine, sql_mode=""):
    def set_sql_mode(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("SET sql_mode = '%s'" % sql_mode)
    sqla_event.listen(engine, "first_connect", set_sql_mode, insert=True)
    sqla_event.listen(engine, "connect", set_sql_mode)

def engine_disable_mode(engine, mode):
    def set_sql_mode(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute(
            "SET sql_mode=(SELECT REPLACE(@@sql_mode,'%s',''))" % mode)
    sqla_event.listen(engine, "first_connect", set_sql_mode, insert=True)
    sqla_event.listen(engine, "connect", set_sql_mode)



def main_2():
    connection_url = mysql.connection_url_admin(CONF_PATH)
    engine = create_engine(connection_url)
    engine_disable_mode(engine, "ONLY_FULL_GROUP_BY")
    Base.metadata.create_all(engine)



if __name__ == '__main__':
    main_2()

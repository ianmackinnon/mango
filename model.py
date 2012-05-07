#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import time
import logging

from hashlib import sha1
from optparse import OptionParser

from sqlalchemy import create_engine, MetaData
from sqlalchemy import Column, Table, and_
from sqlalchemy import ForeignKey, ForeignKeyConstraint, UniqueConstraint, CheckConstraint, PrimaryKeyConstraint
from sqlalchemy import Boolean, Integer, Float, Unicode, Numeric, String
from sqlalchemy.orm import sessionmaker, create_session, relationship, backref, object_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

from sqlalchemy.orm.exc import NoResultFound

log = logging.getLogger('model')

Base = declarative_base()



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
    
    UniqueConstraint(auth_id)

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
            user = session.query(User).join(Auth).filter_by(url=auth_url).filter_by(name_hash=auth_name_hash).one()
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

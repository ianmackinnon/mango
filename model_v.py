#!/usr/bin/env python
# -*- coding: utf-8 -*-


from sqlalchemy import Column
from sqlalchemy import ForeignKey, ForeignKeyConstraint, UniqueConstraint, CheckConstraint, PrimaryKeyConstraint

from sqlalchemy import Boolean, Integer, Float as FloatOrig, Numeric, Date, Time
from sqlalchemy import Unicode as UnicodeOrig, String as StringOrig
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import LONGTEXT, DOUBLE

from model import Base, User, MangoEntity

from model import sanitise_name

Float = lambda : FloatOrig
String = lambda : StringOrig
Unicode = lambda : UnicodeOrig

def use_mysql():
    global Float, String, Unicode
    Float = lambda : DOUBLE()
    String = lambda : LONGTEXT(charset="latin1", collation="latin1_swedish_ci")
    Unicode = lambda : LONGTEXT(charset="utf8", collation="utf8_general_ci")



class Org_v(Base, MangoEntity):
    __tablename__ = 'org_v'
    __table_args__ = {'sqlite_autoincrement': True}

    org_v_id = Column(Integer, primary_key=True)
    existence = Column(Boolean)

    org_id = Column(Integer)

    name = Column(Unicode(), nullable=False)
    description = Column(Unicode())

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float(), nullable=False)
    public = Column(Boolean)

    moderation_user = relationship(User, backref='moderation_org_v_list')

    content = [
        "name",
        "description",
        "public",
        ]

    list_url = "/organisation"
    
    def __init__(self,
                 org_id,
                 name, description=None,
                 moderation_user=None, public=None):

        #
        self.org_id = org_id
        self.existence = True
        #

        self.name = sanitise_name(name)

        self.description = description

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public
        
    def obj(self, public=False,
            ):
        obj = {
            "id": self.org_v_id,
            "entity_id": self.org_id,
            "url": self.url,
            "date": self.a_time,
            "name": self.name,
            "description": self.description,
            }
        if public:
            obj["public"] = self.public
        return obj

    @property
    def url(self):
        return "%s/%d" % (self.list_url, self.org_id)

    @property
    def url_v(self):
        return "%s/%d/revision/%d" % (self.list_url, self.org_id, self.org_v_id)






class Orgalias_v(Base):
    __tablename__ = 'orgalias_v'

    orgalias_v_id = Column(Integer, primary_key=True)
    existence = Column(Boolean)

    orgalias_id = Column(Integer, nullable=False)

    org_id = Column(Integer, nullable=False)
    
    name = Column(Unicode(), nullable=False)

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float()(), nullable=False)
    public = Column(Boolean)



class Orgtag_v(Base):
    __tablename__ = 'orgtag_v'

    orgtag_v_id = Column(Integer, primary_key=True)
    existence = Column(Boolean)

    orgtag_id = Column(Integer, nullable=False)

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float(), nullable=False)
    public = Column(Boolean)

    name = Column(Unicode(), nullable=False)
    name_short = Column(Unicode(), nullable=False)
    base = Column(Unicode(), nullable=False)
    base_short = Column(Unicode(), nullable=False)
    path = Column(Unicode())
    path_short = Column(Unicode())



class Event_v(Base):
    __tablename__ = 'event_v'

    event_v_id = Column(Integer, primary_key=True)
    existence = Column(Boolean)

    event_id = Column(Integer, nullable=False)

    name = Column(Unicode(), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    description = Column(Unicode())
    start_time = Column(Time)
    end_time = Column(Time)

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float(), nullable=False)
    public = Column(Boolean)



class Eventtag_v(Base):
    __tablename__ = 'eventtag_v'

    eventtag_v_id = Column(Integer, primary_key=True)
    existence = Column(Boolean)

    eventtag_id = Column(Integer, nullable=False)

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float(), nullable=False)
    public = Column(Boolean)

    name = Column(Unicode(), nullable=False)
    name_short = Column(Unicode(), nullable=False)
    base = Column(Unicode(), nullable=False)
    base_short = Column(Unicode(), nullable=False)
    path = Column(Unicode())
    path_short = Column(Unicode())



class Address_v(Base):
    __tablename__ = 'address_v'

    address_v_id = Column(Integer, primary_key=True)
    existence = Column(Boolean)

    address_id = Column(Integer, nullable=False)

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



class Note_v(Base):
    __tablename__ = 'note_v'

    note_v_id = Column(Integer, primary_key=True)
    existence = Column(Boolean)

    note_id = Column(Integer, nullable=False)

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float(), nullable=False)
    public = Column(Boolean)

    text = Column(Unicode(), nullable=False)
    source = Column(Unicode(), nullable=False)

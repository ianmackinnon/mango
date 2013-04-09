#!/usr/bin/env python
# -*- coding: utf-8 -*-


from sqlalchemy import Column
from sqlalchemy import ForeignKey, ForeignKeyConstraint, UniqueConstraint, CheckConstraint, PrimaryKeyConstraint

from sqlalchemy import Boolean, Integer, Float as FloatOrig, Numeric, Date, Time
from sqlalchemy import Unicode as UnicodeOrig, String as StringOrig
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import LONGTEXT, DOUBLE

import geo

from model import Base, User, MangoEntity

from model import sanitise_name, sanitise_address

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

    org_id = Column(Integer, nullable=False)

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
            note_obj_list=None, note_count=None,
            address_obj_list=None,
            orgtag_obj_list=None, event_obj_list=None,
            orgalias_obj_list=None, alias=None,
            ):
        obj = {
            "v_id": self.org_v_id,
            "id": self.org_id,
            "url": self.url,
            "date": self.a_time,
            "name": self.name,
            "description": self.description,
            }
        if public:
            obj["public"] = self.public
        if note_obj_list is not None:
            obj["note_list"] = note_obj_list
        if note_count is not None:
            obj["note_count"] = note_count
        if address_obj_list is not None:
            obj["address_list"] = address_obj_list
        if orgtag_obj_list is not None:
            obj["orgtag_list"] = orgtag_obj_list
        if event_obj_list is not None:
            obj["event_list"] = event_obj_list
        if orgalias_obj_list is not None:
            obj["orgalias_list"] = orgalias_obj_list
        if alias is not None:
            obj["alias"] = alias;
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
    __table_args__ = {'sqlite_autoincrement': True}

    event_v_id = Column(Integer, primary_key=True)
    existence = Column(Boolean)

    event_id = Column(Integer, nullable=False)

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

    moderation_user = relationship(User, backref='moderation_event_v_list')

    content = [
        "name",
        "start_date",
        "end_date",
        "description",
        "start_time",
        "end_time",
        "public",
        ]

    list_url = "/event"
    
    def __init__(self,
                 event_id,
                 name, start_date, end_date,
                 description=None, start_time=None, end_time=None,
                 moderation_user=None, public=None):

        #
        self.event_id = event_id
        self.existence = True
        #

        self.name = sanitise_name(name)
        self.start_date = start_date
        self.end_date = end_date

        self.description = description
        self.start_time = start_time
        self.end_time = end_time

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public
        
    def obj(self, public=False,
            note_obj_list=None, note_count=None,
            address_obj_list=None,
            eventtag_obj_list=None, org_obj_list=None,
            ):
        obj = {
            "v_id": self.event_v_id,
            "id": self.event_id,
            "url": self.url,
            "date": self.a_time,
            "name": self.name,
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "end_date": self.end_date.strftime("%Y-%m-%d"),
            "description": self.description,
            "start_time": self.start_time and self.start_time.strftime("%H:%M"),
            "end_time": self.end_time and self.end_time.strftime("%H:%M"),
            }
        if public:
            obj["public"] = self.public
        if note_obj_list is not None:
            obj["note_list"] = note_obj_list
        if note_count is not None:
            obj["note_count"] = note_count
        if address_obj_list is not None:
            obj["address_list"] = address_obj_list
        if eventtag_obj_list is not None:
            obj["eventtag_list"] = eventtag_obj_list
        if org_obj_list is not None:
            obj["org_list"] = org_obj_list
        return obj

    @property
    def url(self):
        return "%s/%d" % (self.list_url, self.event_id)

    @property
    def url_v(self):
        return "%s/%d/revision/%d" % (self.list_url, self.event_id, self.event_v_id)



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
    __table_args__ = {'sqlite_autoincrement': True}

    address_v_id = Column(Integer, primary_key=True)
    existence = Column(Boolean)

    address_id = Column(Integer, nullable=False)

    postal = Column(Unicode(), nullable=False)
    source = Column(Unicode(), nullable=False)
    lookup = Column(Unicode())
    manual_longitude = Column(Float())
    manual_latitude = Column(Float())
    longitude = Column(Float())
    latitude = Column(Float())

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float(), nullable=False)
    public = Column(Boolean)

    moderation_user = relationship(User, backref='moderation_address_v_list')

    content = [
        "postal",
        "source",
        "lookup",
        "manual_longitude",
        "manual_latitude",
        "longitude",
        "latitude",
        "public",
        ]

    list_url = "/address"
    
    def __init__(self,
                 address_id,
                 postal=None, source=None, lookup=None,
                 manual_longitude=None, manual_latitude=None,
                 longitude=None, latitude=None,
                 moderation_user=None, public=None):

        #
        self.address_id = address_id
        self.existence = True
        #

        self.postal = sanitise_address(postal)
        self.source = source
        self.lookup = sanitise_address(lookup)
        self.manual_longitude = manual_longitude
        self.manual_latitude = manual_latitude
        self.longitude = longitude
        self.latitude = latitude

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public
        
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

    def obj(self, public=False,
            note_obj_list=None, note_count=None,
            org_obj_list=None, event_obj_list=None,
            ):
        obj = {
            "v_id": self.address_v_id,
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
        if note_count is not None:
            obj["note_count"] = note_count
        if org_obj_list is not None:
            obj["org_list"] = org_obj_list
            obj["entity_list"] = obj.get("entity_list", []) + org_obj_list
        if event_obj_list is not None:
            obj["event_list"] = event_obj_list
            obj["entity_list"] = obj.get("entity_list", []) + event_obj_list
        return obj

    @property
    def url(self):
        return "%s/%d" % (self.list_url, self.address_id)

    @property
    def url_v(self):
        return "%s/%d/revision/%d" % (self.list_url, self.address_id, self.address_v_id)



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

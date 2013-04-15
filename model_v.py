#!/usr/bin/env python
# -*- coding: utf-8 -*-


from sqlalchemy import Column, Table
from sqlalchemy import and_
from sqlalchemy import ForeignKey, ForeignKeyConstraint, UniqueConstraint, CheckConstraint, PrimaryKeyConstraint

from sqlalchemy import Boolean, Integer, Float as FloatOrig, Numeric, Date, Time
from sqlalchemy import Unicode as UnicodeOrig, String as StringOrig
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import LONGTEXT, DOUBLE
from sqlalchemy.orm.exc import NoResultFound

import geo

from model import Base, User, MangoEntity, \
    gravatar_hash, \
    classproperty, \
    Org, Event, Address, \
    org_address, event_address

from model import sanitise_name, sanitise_address

Float = lambda : FloatOrig
String = lambda : StringOrig
Unicode = lambda : UnicodeOrig

def use_mysql():
    global Float, String, Unicode
    Float = lambda : DOUBLE()
    String = lambda : LONGTEXT(charset="latin1", collation="latin1_swedish_ci")
    Unicode = lambda : LONGTEXT(charset="utf8", collation="utf8_general_ci")



org_address_v = Table(
    'org_address_v', Base.metadata,
    Column('org_id', Integer, nullable=False),
    Column('address_id', Integer, nullable=False),
    Column('a_time', Float(), nullable=False),
    Column('existence', Boolean, nullable=False),
    )



event_address_v = Table(
    'event_address_v', Base.metadata,
    Column('event_id', Integer, nullable=False),
    Column('address_id', Integer, nullable=False),
    Column('a_time', Float(), nullable=False),
    Column('existence', Boolean, nullable=False),
    )



def get_history(session, user_id=None, limit=20, offset=0):
    if (user_id):
        user_sql_1 = ""
        user_sql_2 = """
where user.user_id = %d
""" % user_id
    else:
        user_sql_1 = """
, user_id, user.name as user_name, auth.gravatar_hash
""" 
        user_sql_2 = ""
        
    sql = """
select type, entity_id, entity_v_id, existence, existence_v, a_time as date, T.name%s
from
  (
  select "organisation" as type, org_v.org_id as entity_id, org_v_id as entity_v_id, org_v.a_time, org.org_id and 1 as existence, existence as existence_v, org_v.name as name, org_v.moderation_user_id from org_v left outer join org using (org_id)
  union
  select "event" as type, event_v.event_id as entity_id, event_v_id as entity_v_id, event_v.a_time, event.event_id and 1 as existence, existence as existence_v, event_v.name as name, event_v.moderation_user_id from event_v left outer join event using (event_id)
  union
  select "address" as type, address_v.address_id as entity_id, address_v_id as entity_v_id, address_v.a_time, address.address_id and 1 as existence, existence as existence_v, address_v.postal as name, address_v.moderation_user_id from address_v left outer join address using (address_id)
  union
  select "organisation-tag" as type, orgtag_v.orgtag_id as entity_id, orgtag_v_id as entity_v_id, orgtag_v.a_time, orgtag.orgtag_id and 1 as existence, existence as existence_v, orgtag_v.name as name, orgtag_v.moderation_user_id from orgtag_v left outer join orgtag using (orgtag_id)
  union
  select "event-tag" as type, eventtag_v.eventtag_id as entity_id, eventtag_v_id as entity_v_id, eventtag_v.a_time, eventtag.eventtag_id and 1 as existence, existence as existence_v, eventtag_v.name as name, eventtag_v.moderation_user_id from eventtag_v left outer join eventtag using (eventtag_id)
  union
  select "note" as type, note_v.note_id as entity_id, note_v_id as entity_v_id, note_v.a_time, note.note_id and 1 as existence, existence as existence_v, note_v.text as name, note_v.moderation_user_id from note_v left outer join note using (note_id)
  ) as T 
join user on (moderation_user_id = user_id)
left outer join auth using (auth_id)
%s
order by a_time desc
limit %d
offset %d
""" % (
        user_sql_1,
        user_sql_2,
        limit,
        offset
        )

    results = session.connection().execute(sql)

    history = []
    for row in results:
        row_dict = {}
        for column in row.keys():
            row_dict[column] = getattr(row, column)
        if not user_id and not row_dict.get("gravatar_hash", None):
            row_dict["gravatar_hash"] = gravatar_hash(str(row.user_id))
        history.append(row_dict)
    return history



def accept_address_org_v(orm, address_id):
    query = orm.query(org_address_v.c.org_id) \
        .filter(and_(
            org_address_v.c.address_id == address_id,
            org_address_v.c.existence == True,
            )) \
        .order_by(org_address_v.c.a_time.desc()) \
        .limit(1)
    try:
        (org_id, ) = query.one()
    except NoResultFound as e:
        return False
    
    query = orm.query(org_address) \
        .filter(and_(
            org_address.c.address_id == address_id,
            org_address.c.org_id == org_id,
            ))
    if query.count():
        return False

    query = orm.query(Org) \
        .filter(Org.org_id == org_id)

    if not query.count():
        return True

    items = [{
            "address_id": address_id,
            "org_id": org_id,
            "a_time": 0,
            }]
    orm.connection().execute(org_address.insert(), *items)
    return True
        


def accept_address_event_v(orm, address_id):
    query = orm.query(event_address_v.c.event_id) \
        .filter(and_(
            event_address_v.c.address_id == address_id,
            event_address_v.c.existence == True,
            )) \
        .order_by(event_address_v.c.a_time.desc()) \
        .limit(1)
    try:
        (event_id, ) = query.one()
    except NoResultFound as e:
        return False

    query = orm.query(event_address) \
        .filter(and_(
            event_address.c.address_id == address_id,
            event_address.c.event_id == event_id,
            ))
    if query.count():
        return False

    query = orm.query(Event) \
        .filter(Event.event_id == event_id)

    if not query.count():
        return True

    items = [{
            "address_id": address_id,
            "event_id": event_id,
            "a_time": 0,
            }]
    orm.connection().execute(event_address.insert(), *items)
    return True
        
def accept_org_address_v(orm, org_id):
    """
    Take an org ID of a newly accepted (already committed) org.
    Find matching org_address_v (they can only be in the future from the same non-mod as the org).
    If the addresses already exist, create new org_address rows to link them.
    """
    org = orm.query(Org).filter_by(org_id=org_id).first()
    if not org:
        return

    address_id_list = orm.query(org_address_v.c.address_id) \
        .filter(org_address_v.c.org_id == org_id) \
        .distinct()

    for (address_id, ) in address_id_list:
        address = orm.query(Address).filter_by(address_id=address_id).first()
        if not address:
            continue
        if org in address.org_list:
            continue
        address.org_list.append(org)
    orm.commit()

def accept_event_address_v(orm, event_id):
    """
    Take an event ID of a newly accepted (already committed) event.
    Find matching event_address_v (they can only be in the future from the same non-mod as the event).
    If the addresses already exist, create new event_address rows to link them.
    """
    event = orm.query(Event).filter_by(event_id=event_id).first()
    if not event:
        return

    address_id_list = orm.query(event_address_v.c.address_id) \
        .filter(event_address_v.c.event_id == event_id) \
        .distinct()

    for (address_id, ) in address_id_list:
        address = orm.query(Address).filter_by(address_id=address_id).first()
        if not address:
            continue
        if event in address.event_list:
            continue
        address.event_list.append(event)
    orm.commit()



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

    @classproperty
    @classmethod
    def entity_id(cls):
        return cls.org_id

    @classproperty
    @classmethod
    def entity_v_id(cls):
        return cls.org_v_id
    
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
            "suggestion": True,

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
    
    @classproperty
    @classmethod
    def entity_id(cls):
        return cls.event_id

    @classproperty
    @classmethod
    def entity_v_id(cls):
        return cls.event_v_id
    
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
            "suggestion": True,

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
    
    @classproperty
    @classmethod
    def entity_id(cls):
        return cls.address_id

    @classproperty
    @classmethod
    def entity_v_id(cls):
        return cls.address_v_id
    
    def __init__(self,
                 address_id,
                 postal, source,
                 lookup=None,
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
            "suggestion": True,

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
    __table_args__ = {'sqlite_autoincrement': True}

    note_v_id = Column(Integer, primary_key=True)
    existence = Column(Boolean)

    note_id = Column(Integer, nullable=False)

    text = Column(Unicode(), nullable=False)
    source = Column(Unicode(), nullable=False)

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float(), nullable=False)
    public = Column(Boolean)



    moderation_user = relationship(User, backref='moderation_note_v_list')

    content = [
        "text",
        "source",
        "public",
        ]

    list_url = "/note"
    
    @classproperty
    @classmethod
    def entity_id(cls):
        return cls.note_id

    @classproperty
    @classmethod
    def entity_v_id(cls):
        return cls.note_v_id
    
    def __init__(self,
                 note_id,
                 text, source,
                 moderation_user=None, public=None):

        #
        self.note_id = note_id
        self.existence = True
        #

        self.text = text
        self.source = source

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public
        
    def obj(self, public=False,
            org_obj_list=None, event_obj_list=None,
            address_obj_list=None,
            orgtag_obj_list=None, eventtag_obj_list=None
            ):
        obj = {
            "v_id": self.note_v_id,
            "suggestion": True,

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
        if event_obj_list is not None:
            obj["event_list"] = event_obj_list
            linked = (linked or []) + event_obj_list
        if address_obj_list is not None:
            obj["address_list"] = address_obj_list
            linked = (linked or []) + address_obj_list
        if orgtag_obj_list is not None:
            obj["orgtag_list"] = orgtag_obj_list
            linked = (linked or []) + orgtag_obj_list
        if eventtag_obj_list is not None:
            obj["eventtag_list"] = eventtag_obj_list
            linked = (linked or []) + eventtag_obj_list
        if linked is not False:
            obj["linked"] = linked
        return obj

    @property
    def url(self):
        return "%s/%d" % (self.list_url, self.note_id)

    @property
    def url_v(self):
        return "%s/%d/revision/%d" % (self.list_url, self.note_id, self.note_v_id)

#!/usr/bin/env python3

# pylint: disable=invalid-name,no-value-for-parameter
# Allow using lambdas for MySQL global column types
# and lowercase association table names for SQLAlchemy declarative
# Allow calling `insert` on association tables without argument `dml`.

from sqlalchemy import Column, Table
from sqlalchemy import and_
from sqlalchemy import ForeignKey, CheckConstraint

from sqlalchemy import Boolean, Integer, Float as FloatOrig, Date, Time
from sqlalchemy import Unicode as UnicodeOrig, String as StringOrig
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import LONGTEXT, DOUBLE
from sqlalchemy.orm.exc import NoResultFound

import geo

from model import Base, User, Medium, MangoEntity, \
    gravatar_hash, \
    classproperty, \
    Org, Event, Address, Contact, \
    org_address, event_address, \
    org_contact, event_contact

from model import sanitise_name, sanitise_address

Float = lambda: FloatOrig
String = lambda: StringOrig
Unicode = lambda: UnicodeOrig

def use_mysql():
    global Float, String, Unicode
    Float = DOUBLE
    String = lambda: LONGTEXT(charset="latin1", collation="latin1_swedish_ci")
    Unicode = lambda: LONGTEXT(charset="utf8", collation="utf8_general_ci")



def mango_entity_append_suggestion(
        orm, source_list, get_pending, user, source_id, target_id_name):
    for entity_v in get_pending(orm, user, source_id):
        for i, entity in enumerate(source_list):
            if (
                    getattr(entity, target_id_name) ==
                    getattr(entity_v, target_id_name)
            ):
                source_list[i] = entity_v
                break
        else:
            source_list.append(entity_v)




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



org_contact_v = Table(
    'org_contact_v', Base.metadata,
    Column('org_id', Integer, nullable=False),
    Column('contact_id', Integer, nullable=False),
    Column('a_time', Float(), nullable=False),
    Column('existence', Boolean, nullable=False),
    )



event_contact_v = Table(
    'event_contact_v', Base.metadata,
    Column('event_id', Integer, nullable=False),
    Column('contact_id', Integer, nullable=False),
    Column('a_time', Float(), nullable=False),
    Column('existence', Boolean, nullable=False),
    )


def get_history(session, user_id=None, limit=20, offset=None):
    if offset is None:
        offset = 0
    if limit is None:
        limit = 20

    if user_id:
        user_sql_1 = ""
        user_sql_2 = """
where user.user_id = %d
""" % user_id
    else:
        user_sql_1 = """
, user_id, user.name as user_name, auth.gravatar_hash
"""
        user_sql_2 = ""

    core_sql = """
from
  (
  select "organisation" as type, org_v.org_id as entity_id, org_v_id as entity_v_id, org_v.a_time, org.org_id and 1 as existence, existence as existence_v, org_v.name as name, null as parent_id, null as parent_existence, null as parent_name, org_v.moderation_user_id from org_v left outer join org using (org_id)
  union
  select "event" as type, event_v.event_id as entity_id, event_v_id as entity_v_id, event_v.a_time, event.event_id and 1 as existence, existence as existence_v, event_v.name as name, null as parent_id, null as parent_existence, null as parent_name, event_v.moderation_user_id from event_v left outer join event using (event_id)
  union
  select
      "address" as type,
      address_v.address_id as entity_id,
      address_v_id as entity_v_id,
      address_v.a_time,
      address.address_id and 1 as existence,
      existence as existence_v,
      address_v.postal as name,
      org.org_id as parent_id,
      org.org_id and 1 as parent_existence,
      org.name as parent_name,
      address_v.moderation_user_id
    from address_v
    left outer join address using (address_id)
    left outer join org_address on (address.address_id = org_address.address_id)
    left outer join org on (org_address.org_id = org.org_id)
  union
  select
      "contact" as type,
      contact_v.contact_id as entity_id,
      contact_v_id as entity_v_id,
      contact_v.a_time,
      contact.contact_id and 1 as existence,
      existence as existence_v,
      contact_v.text as name,
      org.org_id as parent_id,
      org.org_id and 1 as parent_existence,
      org.name as parent_name,
      contact_v.moderation_user_id
    from contact_v
    left outer join contact using (contact_id)
    left outer join org_contact on (contact.contact_id = org_contact.contact_id)
    left outer join org on (org_contact.org_id = org.org_id)
  union
  select "organisation-tag" as type, orgtag_v.orgtag_id as entity_id, orgtag_v_id as entity_v_id, orgtag_v.a_time, orgtag.orgtag_id and 1 as existence, existence as existence_v, orgtag_v.name as name, null as parent_id, null as parent_existence, null as parent_name, orgtag_v.moderation_user_id from orgtag_v left outer join orgtag using (orgtag_id)
  union
  select
      "organisation-tag" as type,
      orgtag.orgtag_id as entity_id,
      -1 as entity_v_id,
      org_orgtag.a_time,
      orgtag.orgtag_id and 1 as existence,
      null as existence_v,
      orgtag.name as name,
      org.org_id as parent_id,
      org.org_id and 1 as parent_existence,
      org.name as parent_name,
      null as moderation_user_id
    from org_orgtag
    left outer join orgtag using (orgtag_id)
    left outer join org using (org_id)
  union
  select "event-tag" as type, eventtag_v.eventtag_id as entity_id, eventtag_v_id as entity_v_id, eventtag_v.a_time, eventtag.eventtag_id and 1 as existence, existence as existence_v, eventtag_v.name as name, null as parent_id, null as parent_existence, null as parent_name, eventtag_v.moderation_user_id from eventtag_v left outer join eventtag using (eventtag_id)
  union
  select
      "event-tag" as type,
      eventtag.eventtag_id as entity_id,
      -1 as entity_v_id,
      event_eventtag.a_time,
      eventtag.eventtag_id and 1 as existence,
      null as existence_v,
      eventtag.name as name,
      event.event_id as parent_id,
      event.event_id and 1 as parent_existence,
      event.name as parent_name,
      null as moderation_user_id
    from event_eventtag
    left outer join eventtag using (eventtag_id)
    left outer join event using (event_id)
  union
  select
      "note" as type,
      note_v.note_id as entity_id,
      note_v_id as entity_v_id,
      note_v.a_time,
      note.note_id and 1 as existence,
      existence as existence_v,
      note_v.text as name,
      org.org_id as parent_id,
      org.org_id and 1 as parent_existence,
      org.name as parent_name,
      note_v.moderation_user_id
    from note_v
    left outer join note using (note_id)
    left outer join org_note on (note.note_id = org_note.note_id)
    left outer join org on (org_note.org_id = org.org_id)
  ) as T
left outer join user on (moderation_user_id = user_id)
left outer join auth using (auth_id)
%s
""" % (
    user_sql_2,
)

    count_sql = """select count(*)
%s
""" % (
    core_sql,
)

    data_sql = """
select
  type,
  entity_id,
  entity_v_id,
  existence,
  existence_v,
  parent_id,
  parent_existence,
  parent_name,
  a_time as date,
  T.name%s
  %s
order by a_time desc
limit %d
offset %d
""" % (
    user_sql_1,
    core_sql,
    limit,
    offset
)

    for row in session.connection().execute(count_sql):
        count = row[0]

    results = session.connection().execute(data_sql)

    history = {
        "offset": offset,
        "limit": limit,
        "count": count,
        "items": []
    }
    for row in results:
        row_dict = {}
        for column in list(row.keys()):
            row_dict[column] = getattr(row, column)
        if not user_id and not row_dict.get("gravatar_hash", None):
            row_dict["gravatar_hash"] = gravatar_hash(str(row.user_id))
        history["items"].append(row_dict)
    return history



def accept_address_org_v(orm, address_id):
    # pylint: disable=singleton-comparison
    # Cannot use `is` in SQLAlchemy filters

    # Need to clarify the return status of this function

    query = orm.query(org_address_v.c.org_id) \
        .filter(and_(
            org_address_v.c.address_id == address_id,
            org_address_v.c.existence == True,
            )) \
        .order_by(org_address_v.c.a_time.desc()) \
        .limit(1)
    try:
        (org_id, ) = query.one()
    except NoResultFound:
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
    orm.connection().engine.execute(org_address.insert(), *items)
    orm.commit()
    return True



def accept_address_event_v(orm, address_id):
    # pylint: disable=singleton-comparison
    # Cannot use `is` in SQLAlchemy filters

    query = orm.query(event_address_v.c.event_id) \
        .filter(and_(
            event_address_v.c.address_id == address_id,
            event_address_v.c.existence == True,
            )) \
        .order_by(event_address_v.c.a_time.desc()) \
        .limit(1)
    try:
        (event_id, ) = query.one()
    except NoResultFound:
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
    orm.commit()
    return True

def accept_org_address_v(orm, org_id):
    """
    Take an org ID of a newly accepted (already committed) org.
    Find matching org_address_v (they can only be in the future
    from the same non-mod as the org).
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
    Find matching event_address_v (they can only be in the future
    from the same non-mod as the event).
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



def accept_contact_org_v(orm, contact_id):
    # pylint: disable=singleton-comparison
    # Cannot use `is` in SQLAlchemy filters
    query = orm.query(org_contact_v.c.org_id) \
        .filter(and_(
            org_contact_v.c.contact_id == contact_id,
            org_contact_v.c.existence == True,
            )) \
        .order_by(org_contact_v.c.a_time.desc()) \
        .limit(1)
    try:
        (org_id, ) = query.one()
    except NoResultFound:
        return False

    query = orm.query(org_contact) \
        .filter(and_(
            org_contact.c.contact_id == contact_id,
            org_contact.c.org_id == org_id,
            ))
    if query.count():
        return False

    query = orm.query(Org) \
        .filter(Org.org_id == org_id)

    if not query.count():
        return True

    items = [{
        "contact_id": contact_id,
        "org_id": org_id,
        "a_time": 0,
    }]
    orm.connection().execute(org_contact.insert(), *items)
    orm.commit()
    return True



def accept_contact_event_v(orm, contact_id):
    # pylint: disable=singleton-comparison
    # Cannot use `is` in SQLAlchemy filters

    query = orm.query(event_contact_v.c.event_id) \
        .filter(and_(
            event_contact_v.c.contact_id == contact_id,
            event_contact_v.c.existence == True,
            )) \
        .order_by(event_contact_v.c.a_time.desc()) \
        .limit(1)
    try:
        (event_id, ) = query.one()
    except NoResultFound:
        return False

    query = orm.query(event_contact) \
        .filter(and_(
            event_contact.c.contact_id == contact_id,
            event_contact.c.event_id == event_id,
            ))
    if query.count():
        return False

    query = orm.query(Event) \
        .filter(Event.event_id == event_id)

    if not query.count():
        return True

    items = [{
        "contact_id": contact_id,
        "event_id": event_id,
        "a_time": 0,
    }]
    orm.connection().execute(event_contact.insert(), *items)
    orm.commit()
    return True

def accept_org_contact_v(orm, org_id):
    """
    Take an org ID of a newly accepted (already committed) org.
    Find matching org_contact_v (they can only be in the future
    from the same non-mod as the org).
    If the contactes already exist, create new org_contact rows to link them.
    """
    org = orm.query(Org).filter_by(org_id=org_id).first()
    if not org:
        return

    contact_id_list = orm.query(org_contact_v.c.contact_id) \
        .filter(org_contact_v.c.org_id == org_id) \
        .distinct()

    for (contact_id, ) in contact_id_list:
        contact = orm.query(Contact).filter_by(contact_id=contact_id).first()
        if not contact:
            continue
        if org in contact.org_list:
            continue
        contact.org_list.append(org)
    orm.commit()

def accept_event_contact_v(orm, event_id):
    """
    Take an event ID of a newly accepted (already committed) event.
    Find matching event_contact_v (they can only be in the future
    from the same non-mod as the event).
    If the contactes already exist, create new event_contact rows to link them.
    """
    event = orm.query(Event).filter_by(event_id=event_id).first()
    if not event:
        return

    contact_id_list = orm.query(event_contact_v.c.contact_id) \
        .filter(event_contact_v.c.event_id == event_id) \
        .distinct()

    for (contact_id, ) in contact_id_list:
        contact = orm.query(Contact).filter_by(contact_id=contact_id).first()
        if not contact:
            continue
        if event in contact.event_list:
            continue
        contact.event_list.append(event)
    orm.commit()



class Org_v(Base, MangoEntity):
    __tablename__ = 'org_v'
    __table_args__ = {'sqlite_autoincrement': True}

    org_v_id = Column(Integer, primary_key=True)
    existence = Column(Boolean)

    org_id = Column(Integer, nullable=False)

    name = Column(Unicode(), nullable=False)
    description = Column(Unicode())
    end_date = Column(Date)

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float(), nullable=False)
    public = Column(Boolean)

    moderation_user = relationship(User, backref='moderation_org_v_list')

    content = [
        "name",
        "description",
        "end_date",
        ]

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
                 name, description=None, end_date=None,
                 moderation_user=None, public=None):
        super(Org_v, self).__init__()

        # Start setting version variables
        self.org_id = org_id
        self.existence = True
        # End setting version variables

        self.name = sanitise_name(name)

        self.description = description
        self.end_date = end_date

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public



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
    description = Column(Unicode())
    virtual = Column(Boolean)



class Event_v(Base, MangoEntity):
    __tablename__ = 'event_v'
    __table_args__ = {'sqlite_autoincrement': True}

    event_v_id = Column(Integer, primary_key=True)
    existence = Column(Boolean)

    event_id = Column(Integer, nullable=False)

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

    moderation_user = relationship(User, backref='moderation_event_v_list')

    content = [
        "name",
        "start_date",
        "end_date",
        "description",
        "start_time",
        "end_time",
        ]

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
        super(Event_v, self).__init__()

        # Start setting version variables
        self.event_id = event_id
        self.existence = True
        # End setting version variables

        self.name = sanitise_name(name)
        self.start_date = start_date
        self.end_date = end_date

        self.description = description
        self.start_time = start_time
        self.end_time = end_time

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public



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
    description = Column(Unicode())
    virtual = Column(Boolean)



class Address_v(Base, MangoEntity):
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
        ]

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
        super(Address_v, self).__init__()

        # Start setting version variables
        self.address_id = address_id
        self.existence = True
        # End setting version variables

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



class Note_v(Base, MangoEntity):
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
        ]

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
        super(Note_v, self).__init__()

        # Start setting version variables
        self.note_id = note_id
        self.existence = True
        # End setting version variables

        self.text = text
        self.source = source

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public



class Contact_v(Base, MangoEntity):
    __tablename__ = 'contact_v'
    __table_args__ = {'sqlite_autoincrement': True}

    contact_v_id = Column(Integer, primary_key=True)
    existence = Column(Boolean)

    contact_id = Column(Integer, nullable=False)
    medium_id = Column(Integer, ForeignKey(Medium.medium_id), nullable=False)

    text = Column(Unicode(), nullable=False)
    description = Column(Unicode())
    source = Column(Unicode())

    moderation_user_id = Column(Integer, ForeignKey(User.user_id))
    a_time = Column(Float(), nullable=False)
    public = Column(Boolean)

    moderation_user = relationship(User, backref='moderation_contact_v_list')
    medium = relationship(Medium)

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

    @classproperty
    @classmethod
    def entity_v_id(cls):
        return cls.contact_v_id

    def __init__(self,
                 contact_id,
                 medium,
                 text, description=None, source=None,
                 moderation_user=None, public=None):
        super(Contact_v, self).__init__()

        # Start setting version variables
        self.contact_id = contact_id
        self.existence = True
        # End setting version variables

        if medium:
            self.medium = medium
        else:
            self.medium_id = 0

        self.text = sanitise_name(str(text))
        self.description = description and str(description)
        self.source = source and str(source)

        self.moderation_user = moderation_user
        self.a_time = 0
        self.public = public

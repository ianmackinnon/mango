# -*- coding: utf-8 -*-

from tornado.web import HTTPError
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import exists, and_, or_

from base import BaseHandler, authenticated
from model import User
from model import Org, Event, Address, Contact
from model_v import Org_v, Event_v, Address_v, Contact_v
from model_v import org_address_v, event_address_v, org_contact_v, event_contact_v
from model_v import get_history



def get_user_pending_org(orm, user):
    Org_v_all = aliased(Org_v)
    Org_v_new = aliased(Org_v)
    
    query = orm.query(Org_v_all) \
        .outerjoin((
            Org, 
            Org.org_id == Org_v_all.org_id
            )) \
        .filter(Org_v_all.moderation_user_id==user.user_id) \
        .filter(~exists().where(and_(
                Org_v_new.org_id == Org_v_all.org_id,
                Org_v_new.a_time > Org_v_all.a_time,
                ))) \
        .filter(or_(
                Org.a_time == None,
                Org_v_all.a_time > Org.a_time,
                )) \
         .order_by(Org_v_all.a_time.desc()) \

    return query.all()



def get_user_pending_event(orm, user):
    Event_v_all = aliased(Event_v)
    Event_v_new = aliased(Event_v)

    query = orm.query(Event_v_all) \
        .outerjoin((
            Event,
            Event.event_id == Event_v_all.event_id
            )) \
        .filter(Event_v_all.moderation_user_id==user.user_id) \
        .filter(~exists().where(and_(
                Event_v_new.event_id == Event_v_all.event_id,
                Event_v_new.a_time > Event_v_all.a_time,
                ))) \
        .filter(or_(
                Event.a_time == None,
                Event_v_all.a_time > Event.a_time,
                )) \
        .order_by(Event_v_all.a_time.desc()) \

    return query.all()



def get_user_pending_address(orm, user):
    Address_v_all = aliased(Address_v)
    Address_v_new = aliased(Address_v)

    query = orm.query(Address_v_all) \
        .outerjoin((
            Address,
            Address.address_id == Address_v_all.address_id
            )) \
        .filter(Address_v_all.moderation_user_id==user.user_id) \
        .filter(~exists().where(and_(
                Address_v_new.address_id == Address_v_all.address_id,
                Address_v_new.a_time > Address_v_all.a_time,
                ))) \
        .filter(or_(
                Address.a_time == None,
                Address_v_all.a_time > Address.a_time,
                )) \
        .order_by(Address_v_all.a_time.desc()) \

    return query.all()



def get_user_pending_org_address(orm, user, org_id):
    Address_v_all = aliased(Address_v)
    Address_v_new = aliased(Address_v)

    query = orm.query(Address_v_all) \
        .outerjoin((
            Address,
            Address.address_id == Address_v_all.address_id
            )) \
        .join((
            org_address_v,
            and_(
                org_address_v.c.address_id == Address_v_all.address_id,
                org_address_v.c.org_id == org_id,
                org_address_v.c.existence == 1,
                )
            )) \
        .filter(Address_v_all.moderation_user_id==user.user_id) \
        .filter(~exists().where(and_(
                Address_v_new.address_id == Address_v_all.address_id,
                Address_v_new.a_time > Address_v_all.a_time,
                ))) \
        .filter(or_(
                Address.a_time == None,
                Address_v_all.a_time > Address.a_time,
                )) \
        .order_by(Address_v_all.a_time.desc())

    return query.all()



def get_user_pending_address_org(orm, user, address_id):
    Org_v_all = aliased(Org_v)
    Org_v_new = aliased(Org_v)

    query = orm.query(Org_v_all) \
        .outerjoin((
            Org,
            Org.org_id == Org_v_all.org_id
            )) \
        .join((
            org_address_v,
            and_(
                org_address_v.c.org_id == Org_v_all.org_id,
                org_address_v.c.address_id == address_id,
                org_address_v.c.existence == 1,
                )
            )) \
        .filter(Org_v_all.moderation_user_id==user.user_id) \
        .filter(~exists().where(and_(
                Org_v_new.org_id == Org_v_all.org_id,
                Org_v_new.a_time > Org_v_all.a_time,
                ))) \
        .filter(or_(
                Org.a_time == None,
                Org_v_all.a_time > Org.a_time,
                )) \
        .order_by(Org_v_all.a_time.desc()) \

    return query.all()



def get_user_pending_address_event(orm, user, address_id):
    Event_v_all = aliased(Event_v)
    Event_v_new = aliased(Event_v)

    query = orm.query(Event_v_all) \
        .outerjoin((
            Event,
            Event.event_id == Event_v_all.event_id
            )) \
        .join((
            event_address_v,
            and_(
                event_address_v.c.event_id == Event_v_all.event_id,
                event_address_v.c.address_id == address_id,
                event_address_v.c.existence == 1,
                )
            )) \
        .filter(Event_v_all.moderation_user_id==user.user_id) \
        .filter(~exists().where(and_(
                Event_v_new.event_id == Event_v_all.event_id,
                Event_v_new.a_time > Event_v_all.a_time,
                ))) \
        .filter(or_(
                Event.a_time == None,
                Event_v_all.a_time > Event.a_time,
                )) \
        .order_by(Event_v_all.a_time.desc()) \

    return query.all()



def get_user_pending_event_address(orm, user, event_id):
    Address_v_all = aliased(Address_v)
    Address_v_new = aliased(Address_v)

    query = orm.query(Address_v_all) \
        .outerjoin((
            Address,
            Address.address_id == Address_v_all.address_id
            )) \
        .join((
            event_address_v,
            and_(
                event_address_v.c.address_id == Address_v_all.address_id,
                event_address_v.c.event_id == event_id,
                event_address_v.c.existence == 1,
                )
            )) \
        .filter(Address_v_all.moderation_user_id==user.user_id) \
        .filter(~exists().where(and_(
                Address_v_new.address_id == Address_v_all.address_id,
                Address_v_new.a_time > Address_v_all.a_time,
                ))) \
        .filter(or_(
                Address.a_time == None,
                Address_v_all.a_time > Address.a_time,
                )) \
        .order_by(Address_v_all.a_time.desc()) \

    return query.all()



def get_user_pending_org_contact(orm, user, org_id):
    Contact_v_all = aliased(Contact_v)
    Contact_v_new = aliased(Contact_v)

    query = orm.query(Contact_v_all) \
        .outerjoin((
            Contact,
            Contact.contact_id == Contact_v_all.contact_id
            )) \
        .join((
            org_contact_v,
            and_(
                org_contact_v.c.contact_id == Contact_v_all.contact_id,
                org_contact_v.c.org_id == org_id,
                org_contact_v.c.existence == 1,
                )
            )) \
        .filter(Contact_v_all.moderation_user_id==user.user_id) \
        .filter(~exists().where(and_(
                Contact_v_new.contact_id == Contact_v_all.contact_id,
                Contact_v_new.a_time > Contact_v_all.a_time,
                ))) \
        .filter(or_(
                Contact.a_time == None,
                Contact_v_all.a_time > Contact.a_time,
                )) \
        .order_by(Contact_v_all.a_time.desc())

    return query.all()



def get_user_pending_contact_org(orm, user, contact_id):
    Org_v_all = aliased(Org_v)
    Org_v_new = aliased(Org_v)

    query = orm.query(Org_v_all) \
        .outerjoin((
            Org,
            Org.org_id == Org_v_all.org_id
            )) \
        .join((
            org_contact_v,
            and_(
                org_contact_v.c.org_id == Org_v_all.org_id,
                org_contact_v.c.contact_id == contact_id,
                org_contact_v.c.existence == 1,
                )
            )) \
        .filter(Org_v_all.moderation_user_id==user.user_id) \
        .filter(~exists().where(and_(
                Org_v_new.org_id == Org_v_all.org_id,
                Org_v_new.a_time > Org_v_all.a_time,
                ))) \
        .filter(or_(
                Org.a_time == None,
                Org_v_all.a_time > Org.a_time,
                )) \
        .order_by(Org_v_all.a_time.desc()) \

    return query.all()



def get_user_pending_event_contact(orm, user, event_id):
    Contact_v_all = aliased(Contact_v)
    Contact_v_new = aliased(Contact_v)

    query = orm.query(Contact_v_all) \
        .outerjoin((
            Contact,
            Contact.contact_id == Contact_v_all.contact_id
            )) \
        .join((
            event_contact_v,
            and_(
                event_contact_v.c.contact_id == Contact_v_all.contact_id,
                event_contact_v.c.event_id == event_id,
                event_contact_v.c.existence == 1,
                )
            )) \
        .filter(Contact_v_all.moderation_user_id==user.user_id) \
        .filter(~exists().where(and_(
                Contact_v_new.contact_id == Contact_v_all.contact_id,
                Contact_v_new.a_time > Contact_v_all.a_time,
                ))) \
        .filter(or_(
                Contact.a_time == None,
                Contact_v_all.a_time > Contact.a_time,
                )) \
        .order_by(Contact_v_all.a_time.desc())

    return query.all()



def get_user_pending_contact_event(orm, user, contact_id):
    Event_v_all = aliased(Event_v)
    Event_v_new = aliased(Event_v)

    query = orm.query(Event_v_all) \
        .outerjoin((
            Event,
            Event.event_id == Event_v_all.event_id
            )) \
        .join((
            event_contact_v,
            and_(
                event_contact_v.c.event_id == Event_v_all.event_id,
                event_contact_v.c.contact_id == contact_id,
                event_contact_v.c.existence == 1,
                )
            )) \
        .filter(Event_v_all.moderation_user_id==user.user_id) \
        .filter(~exists().where(and_(
                Event_v_new.event_id == Event_v_all.event_id,
                Event_v_new.a_time > Event_v_all.a_time,
                ))) \
        .filter(or_(
                Event.a_time == None,
                Event_v_all.a_time > Event.a_time,
                )) \
        .order_by(Event_v_all.a_time.desc()) \

    return query.all()



class UserListHandler(BaseHandler):
    @authenticated
    def get(self):
        if not self.current_user.moderator:
            raise HTTPError(404)

        user_list = self.orm.query(User) \
            .order_by(
                (User.user_id==-1).desc(),
                User.moderator.desc(),
                User.locked.asc(),
                User.name,
            ) \
            .all()
        self.render(
            'user-list.html',
            user_list=user_list
            )

class UserHandler(BaseHandler):
    @authenticated
    def get(self, user_id):
        if user_id == "self":
            user_url = "/user/%d" % self.current_user.user_id
            return self.redirect_next(user_url)

        try:
            user = self.orm.query(User).filter_by(user_id=user_id).one()
        except sqlalchemy.orm.exc.NoResultFound:
            raise HTTPError(404, "%d: No such user" % user_id)

        is_json = self.content_type("application/json")
        offset = self.get_argument_int("offset", None, json=is_json)

        submissions = {}
        history = None

        if self.moderator:
            history = get_history(self.orm, user.user_id, offset=offset, limit=50)
        else:
            if user != self.current_user:
                raise HTTPError(404)

            submissions["org"] = get_user_pending_org(
                self.orm, self.current_user)
            submissions["event"] = get_user_pending_event(
                self.orm, self.current_user)
            submissions["address"] = get_user_pending_address(
                self.orm, self.current_user)

        self.render(
            'user.html',
            user=user,
            history=history,
            submissions=submissions,
            )




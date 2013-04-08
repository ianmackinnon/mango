# -*- coding: utf-8 -*-

from tornado.web import HTTPError
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import exists, and_, or_

from base import BaseHandler, authenticated
from model import User, get_history

from model import Org, Event
from model_v import Org_v, Event_v



class UserListHandler(BaseHandler):
    @authenticated
    def get(self):
        if not self.current_user.moderator:
            raise HTTPError(404)

        user_list = self.orm.query(User).all()
        self.render(
            'user_list.html',
            user_list=user_list
            )

class UserHandler(BaseHandler):
    @authenticated
    def get(self, user_id_string):
        if user_id_string == "self":
            user_url = "/user/%d" % self.current_user.user_id
            return self.redirect_next(user_url)

        user_id = int(user_id_string)
            
        try:
            user = self.orm.query(User).filter_by(user_id=user_id).one()
        except sqlalchemy.orm.exc.NoResultFound:
            raise HTTPError(404, "%d: No such user" % user_id)

        submissions = {}
        history = None

        if self.moderator:
            history = get_history(self.orm, user.user_id)
        else:
            if user != self.current_user:
                raise HTTPError(404)

            Org_v_all = aliased(Org_v)
            Org_v_new = aliased(Org_v)

            query = self.orm.query(Org_v_all) \
                .outerjoin((Org, Org.org_id == Org_v_all.org_id)) \
                .filter(Org_v_all.moderation_user_id==self.current_user.user_id) \
                .filter(~exists().where(and_( \
                        Org_v_new.org_id == Org_v_all.org_id,
                        Org_v_new.a_time > Org_v_all.a_time,
                        ))) \
                .filter(or_(
                        Org.a_time == None,
                        Org_v_all.a_time > Org.a_time,
                        )) \
                .order_by(Org_v_all.a_time.desc()) \

            submissions["org"] = query.all()

            Event_v_all = aliased(Event_v)
            Event_v_new = aliased(Event_v)

            query = self.orm.query(Event_v_all) \
                .outerjoin((Event, Event.event_id == Event_v_all.event_id)) \
                .filter(Event_v_all.moderation_user_id==self.current_user.user_id) \
                .filter(~exists().where(and_( \
                        Event_v_new.event_id == Event_v_all.event_id,
                        Event_v_new.a_time > Event_v_all.a_time,
                        ))) \
                .filter(or_(
                        Event.a_time == None,
                        Event_v_all.a_time > Event.a_time,
                        )) \
                .order_by(Event_v_all.a_time.desc()) \

            submissions["event"] = query.all()

        self.render(
            'user.html',
            user=user,
            history=history,
            submissions=submissions,
            )




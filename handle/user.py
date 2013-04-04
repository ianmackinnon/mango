# -*- coding: utf-8 -*-

from tornado.web import HTTPError

from base import BaseHandler, authenticated
from model import User, get_history



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

        if user != self.current_user:
            if not self.current_user.moderator:
                raise HTTPError(404)

        history = get_history(self.orm, user.user_id)

        self.render(
            'user.html',
            user=user,
            history=history,
            )




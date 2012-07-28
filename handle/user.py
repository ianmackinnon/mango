# -*- coding: utf-8 -*-

from base import BaseHandler, authenticated

from model import User



class UserListHandler(BaseHandler):
    @authenticated
    def get(self):
        user_list = self.orm.query(User).all()
        self.render(
            'user_list.html',
            user_list=user_list
            )

class UserHandler(BaseHandler):
    @authenticated
    def get(self, user_id_string):
        user_id = int(user_id_string)
        try:
            user = self.orm.query(User).filter_by(user_id=user_id).one()
        except sqlalchemy.orm.exc.NoResultFound:
            return self.error(404, "%d: No such user" % user_id)
        self.render(
            'user.html',
            user=user,
            )




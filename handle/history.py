# -*- coding: utf-8 -*-

from base import BaseHandler, authenticated



class HistoryHandler(BaseHandler):
    @authenticated
    def get(self):
        sql = """
select type, entity_id, entity_v_id, a_time as date, user_id, user.name, auth.gravatar_hash
from
  (
  select "org" as type, org_id as entity_id, org_v_id as entity_v_id, a_time, moderation_user_id from org_v
  union
  select "org" as type, org_id as entity_id, null as entity_v_id, a_time, moderation_user_id from org
  union
  select "address" as type, address_id as entity_id, address_v_id as entity_v_id, a_time, moderation_user_id from address_v
  union
  select "address" as type, address_id as entity_id, null as entity_v_id, a_time, moderation_user_id from address
  union
  select "orgtag" as type, orgtag_id as entity_id, orgtag_v_id as entity_v_id, a_time, moderation_user_id from orgtag_v
  union
  select "orgtag" as type, orgtag_id as entity_id, null as entity_v_id, a_time, moderation_user_id from orgtag
  union
  select "note" as type, note_id as entity_id, note_v_id as entity_v_id, a_time, moderation_user_id from note_v
  union
  select "note" as type, note_id as entity_id, null as entity_v_id, a_time, moderation_user_id from note
  ) as T 
join user on (moderation_user_id = user_id)
join auth using (auth_id)
order by a_time desc
limit 20
"""
        history = self.orm.connection().execute(sql)

        self.render(
            'history.html',
            history=history,
            )



        



# -*- coding: utf-8 -*-

from base import BaseHandler, authenticated
from note import BaseNoteHandler

from model import OrganisationTag, Note



class BaseOrganisationTagHandler(BaseHandler):
    def _get_arguments(self):
        if self.content_type("application/x-www-form-urlencoded"):
            name = self.get_argument("name")
            note_e_list = [
                int(note_id) for note_id in self.get_arguments("note_id")
                ]
        elif self.content_type("application/json"):
            name = self.get_json_argument("name")
            note_e_list = self.get_json_argument("note_id", [])
        else:
            raise tornado.web.HTTPError(400, "'content-type' required.")

        return name, note_e_list



class OrganisationTagListHandler(BaseOrganisationTagHandler):
    def get(self):
        name = self.get_argument("name", None)
        short = self.get_argument("short", None)

        tag_list = OrganisationTag.query_latest(self.orm)

        if name:
            tag_list = tag_list.filter_by(name=name)

        if short:
            tag_list = tag_list.filter_by(short=short)

        tag_list = tag_list.all()

        if self.accept_type("json"):
            self.write_json([tag.obj() for tag in tag_list])
        else:
            self.render('organisation_tag_list.html',
                        current_user=self.current_user,
                        uri=self.request.uri,
                        organisation_tag_list=tag_list,
                        xsrf=self.xsrf_token
                        )

    def post(self):
        name, note_e_list = BaseOrganisationTagHandler._get_arguments(self)

        organisation_tag = OrganisationTag(name, moderation_user=self.current_user)
        self.orm.add(organisation_tag)
        self.orm.commit()
        
        # Setting organisation_tag_e in a trigger, so we have to update manually.
        self.orm.refresh(organisation_tag)
        
        self.redirect(organisation_tag.url)



class OrganisationTagHandler(BaseOrganisationTagHandler):
    def get(self, organisation_tag_e_string, organisation_tag_id_string):
        organisation_tag_e = int(organisation_tag_e_string)
        organisation_tag_id = \
            organisation_tag_id_string and int(organisation_tag_id_string) or None
        
        if organisation_tag_id:
            if not self.current_user:
                return self.error(404, "Not found")
            query = self.orm.query(OrganisationTag).\
                filter_by(organisation_tag_e=organisation_tag_e).\
                filter_by(organisation_tag_id=organisation_tag_id)
            error = "%d, %d: No such organisation_tag, version" % (
                organisation_tag_e, organisation_tag_id
                )
        else:
            query = OrganisationTag.query_latest(self.orm).\
                filter_by(organisation_tag_e=organisation_tag_e)
            error = "%d: No such organisation_tag" % organisation_tag_e

        try:
            organisation_tag = query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            return self.error(404, error)

        if self.accept_type("json"):
            self.write_json(
                    organisation_tag.obj(),
                    )
        else:
            self.render('organisation_tag.html',
                        current_user=self.current_user,
                        uri=self.request.uri,
                        xsrf=self.xsrf_token,
                        organisation_tag=organisation_tag
                        )

    @authenticated
    def put(self, organisation_tag_e_string, organisation_tag_id_string):
        if organisation_tag_id_string:
            return self.error(405, "Cannot edit revisions.")

        organisation_tag_e = int(organisation_tag_e_string)

        query = OrganisationTag.query_latest(self.orm).filter_by(organisation_tag_e=organisation_tag_e)

        try:
            organisation_tag = query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            return self.error(404, "%d: No such organisation_tag" % organisation_tag_e)

        name, note_e_list = BaseOrganisationTagHandler._get_arguments(self)

        if organisation_tag.name == name and \
                set(note_e_list) == set([note.note_e for note in organisation_tag.note_list()]):
            self.redirect(organisation_tag.url)
            return
            
        new_organisation_tag = organisation_tag.copy(moderation_user=self.current_user)
        new_organisation_tag.name = name
        del new_organisation_tag.note_entity_list[:]

        if note_e_list:
            note_list = Note.query_latest(self.orm)\
                .filter(Note.note_e.in_(note_e_list))\
                .all()
            for note in note_list:
                new_organisation_tag.note_entity_list.append(note)

        self.orm.commit()
        self.redirect(new_organisation_tag.url)



class OrganisationTagNoteListHandler(BaseNoteHandler):
    @authenticated
    def post(self, organisation_tag_e_string, organisation_tag_id_string):
        if organisation_tag_id_string:
            return self.error(405, "Cannot edit revisions.")

        organisation_tag_e = int(organisation_tag_e_string)

        query = OrganisationTag.query_latest(self.orm).filter_by(organisation_tag_e=organisation_tag_e)

        try:
            organisation_tag = query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            return self.error(404, "%d: No such organisation_tag" % organisation_tag_e)

        text, source = BaseNoteHandler._get_arguments(self)

        new_note = Note(text, source,
                        moderation_user=self.current_user)
        self.orm.add(new_note)
        self.orm.flush()
        # Setting note_e in a trigger, so we have to update manually.
        self.orm.refresh(new_note)
        assert new_note.note_e

        new_organisation_tag = organisation_tag.copy(
            moderation_user=self.current_user)
        self.orm.add(new_organisation_tag)
        new_organisation_tag.note_entity_list.append(new_note)
        self.orm.commit()
        self.redirect(new_organisation_tag.url)


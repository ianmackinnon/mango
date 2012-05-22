# -*- coding: utf-8 -*-

from sqlalchemy.orm.exc import NoResultFound

from base import BaseHandler, authenticated
from note import BaseNoteHandler
from address import BaseAddressHandler

from model import Organisation, Note, Address, OrganisationTag, organisation_organisation_tag



class OrganisationListHandler(BaseHandler):
    def get(self):
        name = self.get_argument("name", None)
        tag = self.get_argument("tag", None)

        organisation_list = Organisation.query_latest(self.orm)\
            .filter(Organisation.visible==True)

        if name:
            organisation_list = organisation_list.filter_by(name=name)

        if tag:
            tag_list = OrganisationTag.query_latest(self.orm)\
                .filter_by(short=tag).subquery()

            organisation_list = organisation_list.join(
                (organisation_organisation_tag, organisation_organisation_tag.c.organisation_id == Organisation.organisation_id)
                ).join(
                (tag_list, organisation_organisation_tag.c.organisation_tag_e == tag_list.c.organisation_tag_e)
                )

        organisation_list = organisation_list.limit(10).all()

        if self.accept_type("json"):
            self.write_json(
                    [organisation.obj() for organisation in organisation_list],
                    )
        else:
            self.render('organisation_list.html',
                        organisation_list=organisation_list,
                        )

    def post(self):
        if self.content_type("application/x-www-form-urlencoded"):
            name = self.get_argument("name")
        elif self.content_type("application/json"):
            name = self.get_json_argument("name")
        else:
            raise tornado.web.HTTPError(400, "'content-type' required.")

        organisation = Organisation(name, moderation_user=self.current_user)
        self.orm.add(organisation)
        self.orm.commit()

        # Setting organisation_e in a trigger, so we have to update manually.
        self.orm.refresh(organisation)

        self.redirect(organisation.url)


class OrganisationHandler(BaseHandler):
    def get(self, organisation_e_string, organisation_id_string):
        organisation_e = int(organisation_e_string)
        organisation_id = \
            organisation_id_string and int(organisation_id_string) or None
        
        if organisation_id:
            if not self.current_user:
                return self.error(404, "Not found")
            query = self.orm.query(Organisation).\
                filter_by(organisation_e=organisation_e).\
                filter_by(organisation_id=organisation_id)
            error = "%d, %d: No such organisation, version" % (
                organisation_e, organisation_id)
        else:
            query = Organisation.query_latest(self.orm).\
                filter_by(organisation_e=organisation_e)
            if not self.current_user:
                query = query.filter(Organisation.visible==True)
            error = "%d: No such organisation" % organisation_e

        try:
            organisation = query.one()
        except NoResultFound:
            return self.error(404, error)

        if self.accept_type("json"):
            self.write_json(
                    organisation.obj(),
                    )
        else:
            self.render('organisation.html',
                        organisation=organisation,
                        )

    @authenticated
    def delete(self, organisation_e_string, organisation_id_string):
        if organisation_id_string:
            return self.error(405, "Cannot delete revisions.")

        organisation_e = int(organisation_e_string)
        
        query = Organisation.query_latest(self.orm).filter_by(organisation_e=organisation_e).filter(Organisation.visible==True)

        try:
            organisation = query.one()
        except NoResultFound:
            return self.error(404, "%d: No such organisation" % organisation_e)

        new_organisation = organisation.copy(moderation_user=self.current_user, visible=False)
        self.orm.add(new_organisation)
        self.orm.commit()
        self.redirect("/organisation")
        
    @authenticated
    def put(self, organisation_e_string, organisation_id_string):
        if organisation_id_string:
            return self.error(405, "Cannot edit revisions.")

        organisation_e = int(organisation_e_string)

        query = Organisation.query_latest(self.orm).filter_by(organisation_e=organisation_e)

        try:
            organisation = query.one()
        except NoResultFound:
            return self.error(404, "%d: No such organisation" % organisation_e)

        if self.content_type("application/x-www-form-urlencoded"):
            name = self.get_argument("name")
            note_e_list = [
                int(note_id) for note_id in self.get_arguments("note_id")
                ]
            address_e_list = [
                int(address_id) for address_id in self.get_arguments("address_id")
                ]
            tag_e_list = [
                int(tag_id) for tag_id in self.get_arguments("tag_id")
                ]
        elif self.content_type("application/json"):
            name = self.get_json_argument("name")
            note_e_list = self.get_json_argument("note_id", [])
            address_e_list = self.get_json_argument("address_id", [])
            tag_e_list = self.get_json_argument("tag_id", [])
        else:
            raise tornado.web.HTTPError(400, "'content-type' required.")

        if organisation.name == name and \
                set(note_e_list) == set([note.note_e for note in organisation.note_list()]) and \
                set(address_e_list) == set([address.address_e for address in organisation.address_list()]) and \
                set(tag_e_list) == set([organisation_tag.organisation_tag_e for organisation_tag in organisation.tag_list()]):
            self.redirect(organisation.url)
            return
            
        new_organisation = organisation.copy(moderation_user=self.current_user, visible=True)
        self.orm.add(new_organisation)
        new_organisation.name = name
        del new_organisation.note_entity_list[:]
        del new_organisation.address_entity_list[:]
        del new_organisation.organisation_tag_entity_list[:]

        # Do want to be able to share tags with other organisations
        if note_e_list:
            note_list = Note.query_latest(self.orm)\
                .filter(Note.note_e.in_(note_e_list))\
                .all()
            for note in note_list:
                new_organisation.note_entity_list.append(note)
        
        # Don't want to be able to share addresses with other organisations
        for address in organisation.address_list():
            if address.address_e in address_e_list:
                new_organisation.address_entity_list.append(address)

        # Do want to be able to share tags with other organisations
        if tag_e_list:
            tag_list = OrganisationTag.query_latest(self.orm)\
                .filter(OrganisationTag.organisation_tag_e.in_(tag_e_list))\
                .all()
            for tag in tag_list:
                new_organisation.organisation_tag_entity_list.append(tag)
        
        self.orm.commit()
        self.redirect(new_organisation.url)
        


class OrganisationAddressListHandler(BaseAddressHandler):
    @authenticated
    def post(self, organisation_e_string, organisation_id_string):
        if organisation_id_string:
            return self.error(405, "Cannot edit revisions.")

        organisation_e = int(organisation_e_string)

        query = Organisation.query_latest(self.orm).\
            filter_by(organisation_e=organisation_e)

        try:
            organisation = query.one()
        except NoResultFound:
            return self.error(404, "%d: No such organisation" % organisation_e)

        postal, source, lookup, manual_longitude, manual_latitude, note_e_list = \
            BaseAddressHandler._get_arguments(self)

        new_address = Address(postal, source, lookup,
                          manual_longitude=manual_longitude,
                          manual_latitude=manual_latitude,
                          moderation_user=self.current_user)
        self.orm.add(new_address)
        new_address.geocode()
        self.orm.flush()
        # Setting address_e in a trigger, so we have to update manually.
        self.orm.refresh(new_address)
        assert new_address.address_e

        new_organisation = organisation.copy(
            moderation_user=self.current_user, visible=True
            )
        self.orm.add(new_organisation)
        new_organisation.address_entity_list.append(new_address)
        self.orm.commit()
        self.redirect(new_organisation.url)



class OrganisationNoteListHandler(BaseNoteHandler):
    @authenticated
    def post(self, organisation_e_string, organisation_id_string):
        if organisation_id_string:
            return self.error(405, "Cannot edit revisions.")

        organisation_e = int(organisation_e_string)

        query = Organisation.query_latest(self.orm)\
            .filter_by(organisation_e=organisation_e)

        try:
            organisation = query.one()
        except NoResultFound:
            return self.error(404, "%d: No such organisation" % organisation_e)

        text, source = BaseNoteHandler._get_arguments(self)

        new_note = Note(text, source,
                        moderation_user=self.current_user)
        self.orm.add(new_note)
        self.orm.flush()
        # Setting note_e in a trigger, so we have to update manually.
        self.orm.refresh(new_note)
        assert new_note.note_e

        new_organisation = organisation.copy(
            moderation_user=self.current_user, visible=True)
        self.orm.add(new_organisation)
        new_organisation.note_entity_list.append(new_note)
        self.orm.commit()
        self.redirect(new_organisation.url)




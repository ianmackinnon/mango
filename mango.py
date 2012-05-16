#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import errno
import logging

from mako.template import Template
from mako.lookup import TemplateLookup
from mako import exceptions

import tornado.auth
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado.options import define, options

import sqlalchemy.orm.exc
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine, func, and_


from model import Auth, User, Session, Note, Organisation, Address, OrganisationTag, organisation_organisation_tag



define("port", default=8802, help="Run on the given port", type=int)



class Application(tornado.web.Application):

    session_cookie_name = "s"

    def load_cookie_secret(self):
        try:
            self.cookie_secret = open(".xsrf", "r").read().strip()
        except IOError as e:
            sys.stderr.write(
                "Could not open XSRF key. Run 'make' to generate one.\n"
                )
            sys.exit(1)

    def path_is_authenticated(self, path):
        for key, value in self.handler_list:
            if re.match(key, path) and hasattr(value, "get"):
                if hasattr(value.get, "authenticated") and \
                        value.get.authenticated == True:
                    return True
        return False
                
        
    def __init__(self):

        self.load_cookie_secret()

        settings = dict(
            xsrf_cookies=True,
            cookie_secret=self.cookie_secret,
            login_url="/auth/login",
            )

        re_id = "([1-9][0-9]*)"
        re_e_id = "([1-9][0-9]*)(?:,([1-9][0-9]*))?"

        self.handler_list = [
            (r"/", HomeHandler),

            (r"/user", UserListHandler),
            (r"/user/%s" % re_id , UserHandler),

            (r"/note", NoteListHandler),
            (r"/note/%s" % re_e_id, NoteHandler),

            (r"/organisation", OrganisationListHandler),
            (r"/organisation/%s" % re_e_id, OrganisationHandler),
            (r"/organisation/%s/address" % re_e_id, OrganisationAddressListHandler),

            (r"/address", AddressListHandler),
            (r"/address/%s" % re_e_id, AddressHandler),

            (r"/organisation-tag", OrganisationTagListHandler),
            (r"/organisation-tag/%s" % re_e_id, OrganisationTagHandler),

            (r"/auth/login", AuthLoginHandler),
            (r"/auth/login/google", AuthLoginGoogleHandler),
            (r"/auth/login/local", AuthLoginLocalHandler),
            (r"/auth/logout", AuthLogoutHandler),
            ]

        connection_url = 'sqlite:///mango.db'
    
        engine = create_engine(connection_url)

        self.orm = scoped_session(sessionmaker(bind=engine, autocommit=False))

        self.lookup = TemplateLookup(directories=['template'],
                                     input_encoding='utf-8',
                                     output_encoding='utf-8',
                                     default_filters=["unicode", "h"],
                                     )

        log_location = "log/arms_map.py.log"
        log_max_bytes = 1048576

        try:
            os.mkdir(os.path.dirname(log_location))
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise e
            

        logger = logging.getLogger()
        handler = logging.handlers.RotatingFileHandler(
            log_location, maxBytes=log_max_bytes)
        logging.getLogger().addHandler(handler)

        settings["xsrf_cookies"] = False
        
        tornado.web.Application.__init__(self, self.handler_list, **settings)



def newline(text):
    return text.replace("\n", "<br />")



class BaseHandler(tornado.web.RequestHandler):

    def _execute(self, transforms, *args, **kwargs):
        method = self.get_argument("_method", None)
        if method and self.request.method.lower() == "post":
            self.request.method = method.upper()
        tornado.web.RequestHandler._execute(self, transforms, *args, **kwargs)

    @property
    def orm(self):
        return self.application.orm

    def content_type(self, name):
        if "Content-Type" in self.request.headers:
            return self.request.headers["Content-Type"].lower() == name.lower()
        return False

    def accept_type(self, name):
        if "Accept" in self.request.headers:
            return name.lower() in self.request.headers["Accept"].lower()
        return False

    def is_local(self):
        if "X-Forwarded-For" in self.request.headers:
            return False
        return self.request.remote_ip == "127.0.0.1"

    def get_remote_ip(self):
        if "X-Forwarded-For" in self.request.headers:
            return self.request.headers["X-Forwarded-For"]
        return self.request.remote_ip

    def get_accept_language(self):
        if "Accept-Language" in self.request.headers:
            return self.request.headers["Accept-Language"]
        return u""

    def get_user_agent(self):
        return self.request.headers["User-Agent"]

    def start_session(self, value):
        self.set_secure_cookie(self.application.session_cookie_name, value);
        # Sets a cookie value to the base64 plaintext session_id, 
        #   but is protected by tornado's _xsrf cookie.
        # Retrieved by BaseHandler.get_current_user()

    def end_session(self):
        self.clear_cookie(self.application.session_cookie_name)

    def render(self, template_name, **kwargs):
        template = self.application.lookup.get_template(template_name)
        kwargs["newline"] = newline
        try:
            self.write(template.render(**kwargs))
        except:
            self.write(exceptions.html_error_template().render())
        if self.orm.new or self.orm.dirty or self.orm.deleted:
            print self.orm.new or self.orm.dirty or self.orm.deleted
            self.orm.rollback()

    def get_session(self):
        session_id = self.get_secure_cookie(self.application.session_cookie_name)
        try:
            session = self.orm.query(Session).\
                filter_by(session_id=session_id).one()
        except sqlalchemy.orm.exc.NoResultFound:
            self.end_session()
            return None
        if session.d_time is not None:
            self.end_session()
            return None
        session.touch_commit()
        return session

    # required by tornado auth
    def get_current_user(self):
        session = self.get_session()
        if session:
            return session.user
        return None

    def error(self, status_code, message):
        self.status_code = status_code
        self.render('error.html',
                    current_user=self.current_user, uri=self.request.uri,
                    status_code=self.status_code, message=message,
                    )

    _ARG_DEFAULT_MANGO = []
    def get_argument_float(self, name, default=_ARG_DEFAULT_MANGO, strip=True):
        value = self.get_argument(name, default, strip)
        if value == default:
            if default is self._ARG_DEFAULT_MANGO:
                raise tornado.web.HTTPError(400, "Missing argument %s" % name)
            return value

        try:
            return float(value)
        except ValueError as e:
            raise tornado.web.HTTPError(
                400,
                "Cannot convert argument %s to a floating point number." % name
                )

    def get_json_data(self):
        if hasattr(self, "json_data") and self.json_data:
            return
        try:
            self.json_data = json.loads(self.request.body)
        except ValueError as e:
            raise tornado.web.HTTPError(400, "Could not decode JSON data.")

    def get_json_argument(self, name, default=_ARG_DEFAULT_MANGO):
        self.get_json_data()

        if not name in self.json_data:
            if default is self._ARG_DEFAULT_MANGO:
                raise tornado.web.HTTPError(400, "Missing argument %s" % name)
            return default

        return self.json_data[name]

    def get_json_argument_float(self, name, default=_ARG_DEFAULT_MANGO):
        value = self.get_json_argument(name, default)
        if value == default:
            if default is self._ARG_DEFAULT_MANGO:
                raise tornado.web.HTTPError(400, "Missing argument %s" % name)
            return value

        try:
            return float(value)
        except ValueError as e:
            raise tornado.web.HTTPError(
                400,
                "Cannot convert argument %s to a floating point number." % name
                )
        


def authenticated(f):
    decorated = tornado.web.authenticated(f)
    decorated.authenticated = True;
    return decorated



class HomeHandler(BaseHandler):
    def get(self):
        self.render('home.html',
                    current_user=self.current_user, uri=self.request.uri,
                    )



class NoteListHandler(BaseHandler):
    def get(self):

        note_list = Note.query_latest(self.orm).all()

        self.render(
            'note_list.html',
            current_user=self.current_user,
            uri=self.request.uri,
            note_list=note_list,
            xsrf=self.xsrf_token
            )

    def post(self):
        if self.content_type("application/x-www-form-urlencoded"):
            text = self.get_argument("text")
            source = self.get_argument("source")
        elif self.content_type("application/json"):
            text = self.get_json_argument("text")
            source = self.get_json_argument("source")
        else:
            raise tornado.web.HTTPError(400, "'content-type' required.")

        note = Note(text, source, moderation_user=self.current_user)
        self.orm.add(note)
        self.orm.commit()

        # Setting note_e in a trigger, so we have to update manually.
        self.orm.refresh(note)

        self.redirect(note.url)



class NoteHandler(BaseHandler):
    def get(self, note_e_string, note_id_string):
        note_e = int(note_e_string)
        note_id = note_id_string and int(note_id_string) or None
        
        if note_id:
            if not self.current_user:
                return self.error(404, "Not found")
            query = self.orm.query(Note).filter_by(note_e=note_e).filter_by(note_id=note_id)
            error = "%d, %d: No such note, version" % (note_e, note_id)
        else:
            query = Note.query_latest(self.orm).filter_by(note_e=note_e)
            error = "%d: No such note" % note_e

        try:
            note = query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            return self.error(404, error)

        if self.accept_type("json"):
            self.write(json.dumps(
                    note.obj(),
                    indent=2,
                    ))
        else:
            self.render(
                'note.html',
                current_user=self.current_user,
                uri=self.request.uri,
                xsrf=self.xsrf_token,
                note=note
                )

    @authenticated
    def put(self, note_e_string, note_id_string):
        if note_id_string:
            return self.error(405, "Cannot edit revisions.")

        note_e = int(note_e_string)

        query = Note.query_latest(self.orm).filter_by(note_e=note_e)

        try:
            note = query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            return self.error(404, "%d: No such note" % note_e)

        if self.content_type("application/x-www-form-urlencoded"):
            text = self.get_argument("text")
            source = self.get_argument("source")
        elif self.content_type("application/json"):
            text = self.get_json_argument("text")
            source = self.get_json_argument("source")
        else:
            raise tornado.web.HTTPError(400, "'content-type' required.")

        new_note = note.copy(moderation_user=self.current_user)
        new_note.text = text
        new_note.source = source
        self.orm.commit()
        self.redirect(new_note.url)
        


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


        organisation_list = organisation_list.all()

        if self.accept_type("json"):
            self.write(json.dumps(
                    [organisation.obj() for organisation in organisation_list],
                    indent=2,
                    ))
        else:
            self.render('organisation_list.html',
                        current_user=self.current_user,
                        uri=self.request.uri,
                        organisation_list=organisation_list,
                        xsrf=self.xsrf_token,
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
        except sqlalchemy.orm.exc.NoResultFound:
            return self.error(404, error)

        if self.accept_type("json"):
            self.write(json.dumps(
                    organisation.obj(),
                    indent=2,
                    ))
        else:
            self.render('organisation.html',
                        current_user=self.current_user,
                        uri=self.request.uri,
                        xsrf=self.xsrf_token,
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
        except sqlalchemy.orm.exc.NoResultFound:
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
        except sqlalchemy.orm.exc.NoResultFound:
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
        


class OrganisationAddressListHandler(BaseHandler):
    @authenticated
    def post(self, organisation_e_string, organisation_id_string):
        if organisation_id_string:
            return self.error(405, "Cannot edit revisions.")

        organisation_e = int(organisation_e_string)

        query = Organisation.query_latest(self.orm).filter_by(organisation_e=organisation_e)

        try:
            organisation = query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            return self.error(404, "%d: No such organisation" % organisation_e)

        if self.content_type("application/x-www-form-urlencoded"):
            postal = self.get_argument("postal")
            lookup = self.get_argument("lookup", None)
            manual_longitude = self.get_argument_float("manual_longitude", None)
            manual_latitude = self.get_argument_float("manual_latitude", None)
        elif self.content_type("application/json"):
            postal = self.get_json_argument("postal")
            lookup = self.get_json_argument("lookup", None)
            manual_longitude = self.get_json_argument_float("manual_longitude", None)
            manual_latitude = self.get_json_argument_float("manual_latitude", None)
        else:
            raise tornado.web.HTTPError(400, "'content-type' required.")

        new_address = Address(postal, lookup,
                          manual_longitude=manual_longitude,
                          manual_latitude=manual_latitude,
                          moderation_user=self.current_user)
        self.orm.add(new_address)
        new_address.geocode()
        self.orm.flush()
        self.orm.refresh(new_address)  # Setting address_e in a trigger, so we have to update manually.

        assert new_address.address_e

        new_organisation = organisation.copy(moderation_user=self.current_user, visible=True)
        self.orm.add(new_organisation)
        for address in organisation.address_list():
            new_organisation.address_entity_list.append(address)
        new_organisation.address_entity_list.append(new_address)

        self.orm.commit()
        self.redirect(new_organisation.url)


class AddressListHandler(BaseHandler):
    def get(self):

        address_list = Address.query_latest(self.orm).all()

        self.render(
            'address_list.html',
            current_user=self.current_user,
            uri=self.request.uri,
            address_list=address_list,
            xsrf=self.xsrf_token,
            )



class AddressHandler(BaseHandler):
    def get(self, address_e_string, address_id_string):
        address_e = int(address_e_string)
        address_id = address_id_string and int(address_id_string) or None

        if address_id:
            if not self.current_user:
                return self.error(404, "Not found")
            query = self.orm.query(Address).filter_by(address_e=address_e).filter_by(address_id=address_id)
            error = "%d, %d: No such address, version" % (address_e, address_id)
        else:
            query = Address.query_latest(self.orm).filter_by(address_e=address_e)
            error = "%d: No such address" % address_e

        try:
            address = query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            return self.error(404, error)

        if self.accept_type("json"):
            self.write(json.dumps(
                    address.obj(),
                    indent=2,
                    ))
        else:
            self.render(
                'address.html',
                current_user=self.current_user,
                uri=self.request.uri,
                xsrf=self.xsrf_token,
                address=address
                )

    @authenticated
    def put(self, address_e_string, address_id_string):
        if address_id_string:
            return self.error(405, "Cannot edit revisions.")

        address_e = int(address_e_string)

        query = Address.query_latest(self.orm).filter_by(address_e=address_e)

        try:
            address = query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            return self.error(404, "%d: No such address" % address_e)

        if self.content_type("application/x-www-form-urlencoded"):
            postal = self.get_argument("postal")
            lookup = self.get_argument("lookup", None)
            manual_longitude = self.get_argument_float("manual_longitude", None)
            manual_latitude = self.get_argument_float("manual_latitude", None)
            note_e_list = [
                int(note_id) for note_id in self.get_arguments("note_id")
                ]
        elif self.content_type("application/json"):
            postal = self.get_json_argument("postal")
            lookup = self.get_json_argument("lookup", None)
            manual_longitude = self.get_json_argument_float("manual_longitude", None)
            manual_latitude = self.get_json_argument_float("manual_latitude", None)
            note_e_list = self.get_json_argument("note_id", [])
        else:
            raise tornado.web.HTTPError(400, "'content-type' required.")

        if address.name == name and \
                set(note_e_list) == set([note.note_e for note in address.note_list()]):
            self.redirect(address.url)
            return
            
        new_address = address.copy(moderation_user=self.current_user)
        new_address.postal = postal
        new_address.lookup = lookup
        new_address.manual_longitude = manual_longitude
        new_address.manual_latitude = manual_latitude
        del new_address.note_entity_list[:]

        if note_e_list:
            note_list = Note.query_latest(self.orm)\
                .filter(Note.note_e.in_(note_e_list))\
                .all()
            for note in note_list:
                new_address.note_entity_list.append(note)

        new_address.geocode()
        self.orm.commit()
        self.redirect(new_address.url)



class OrganisationTagListHandler(BaseHandler):
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
            self.write(json.dumps(
                    [tag.obj() for tag in tag_list],
                    indent=2,
                    ))
        else:
            self.render('organisation_tag_list.html',
                        current_user=self.current_user,
                        uri=self.request.uri,
                        organisation_tag_list=tag_list,
                        xsrf=self.xsrf_token
                        )

    def post(self):
        if self.content_type("application/x-www-form-urlencoded"):
            name = self.get_argument("name")
        elif self.content_type("application/json"):
            name = self.get_json_argument("name")
        else:
            raise tornado.web.HTTPError(400, "'content-type' required.")

        organisation_tag = OrganisationTag(name, moderation_user=self.current_user)
        self.orm.add(organisation_tag)
        self.orm.commit()
        
        # Setting organisation_tag_e in a trigger, so we have to update manually.
        self.orm.refresh(organisation_tag)
        
        self.redirect(organisation_tag.url)



class OrganisationTagHandler(BaseHandler):
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
            self.write(json.dumps(
                    organisation_tag.obj(),
                    indent=2,
                    ))
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



class UserListHandler(BaseHandler):
    @authenticated
    def get(self):
        user_list = self.orm.query(User).all()
        self.render('user_list.html', current_user=self.current_user, uri=self.request.uri, user_list=user_list)

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
            current_user=self.current_user,
            uri=self.request.uri,
            xsrf=self.xsrf_token,
            user=user
            )



# Authentication pages



class AuthLoginHandler(BaseHandler):
    def get(self):
        self.render(
            'login.html',
            user=self.current_user,
            uri=self.request.uri,
            next=self.get_argument("next", "/")
            )



class AuthLoginLocalHandler(BaseHandler):
    def get(self):
        if not self.is_local():
            raise tornado.web.HTTPError(500, "Auth failed")

        user = self.orm.query(User).filter_by(user_id=-1).one()
        session = Session(
                user,
                self.get_remote_ip(),
                self.get_accept_language(),
                self.get_user_agent(),
                )
        self.orm.add(session)
        self.orm.flush()
        self.start_session(str(session.session_id))
        self.redirect(self.get_argument("next", "/"))



class AuthLoginGoogleHandler(BaseHandler, tornado.auth.GoogleMixin):

    openid_url = u"https://www.google.com/accounts/o8/id"
    
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect()
    
    def _on_auth(self, auth_user):
        """
        Called after we receive authorisation information from Google.
        auth_user dict is either empty or contains 'locale', 'first_name', 'last_name', 'name' and 'email'.
        """

        if not auth_user:
            raise tornado.web.HTTPError(500, "Google auth failed")

        auth_name = auth_user["email"]

        user = User.get_from_auth(self.orm, self.openid_url, auth_name)

        if not user:
            raise tornado.web.HTTPError(
                404, "%s %s: No account found" % (self.openid_url, auth_name)
                )

        session = Session(
                user,
                self.get_remote_ip(),
                self.get_accept_language(),
                self.get_user_agent(),
                )
        self.orm.add(session)
        self.orm.flush()
        self.start_session(str(session.session_id))

        self.redirect(self.get_argument("next", "/"))



class AuthLogoutHandler(BaseHandler):
    def get(self):
        session = self.get_session()
        if session:
            session.close_commit()
        self.end_session()
        self.clear_cookie("_xsrf")
        next_path = self.get_argument("next", "/")
        if self.application.path_is_authenticated(next_path):
            next_path = "/"
        self.redirect(next_path)



def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-

import re
import json
import codecs
import hashlib
import httplib
import markdown
import datetime
import urlparse
from urllib import urlencode
from collections import namedtuple

from bs4 import BeautifulSoup
from sqlalchemy import and_, or_, not_
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import IntegrityError
from mako import exceptions
from tornado.web import authenticated as tornado_authenticated, RequestHandler, HTTPError

import geo

from model import Session, Address



md_safe = markdown.Markdown(
    safe_mode=True,
    )



def sha1_concat(*parts):
    sha1 = hashlib.sha1()
    for part in parts:
        sha1.update(part)
    return sha1.hexdigest()



def authenticated(f):
    decorated = tornado_authenticated(f)
    decorated.authenticated = True;
    return decorated



def newline(text):
    return text.replace("\n", "<br />")



def newline_comma(text):
    return text.replace("\n", ", ")



def nbsp(text):
    text = re.sub("[\s]+", "&nbsp;", text)
    text = text.replace("-", "&#8209;")
    return text



def markdown_safe(text):
    return md_safe.convert(text)



def form_date(date):
    return date or ""



def form_time(time):
    return time and str(time) or ""



def page_date(date, format_="%a %d %b %Y"):
    return date and datetime.datetime.strptime(date, "%Y-%m-%d").date().strftime(format_) or ""



def page_date_format(format_="%a %d %b %Y"):
    def filter(date):
        return page_date(date, format_)
    return filter



def page_time(time):
    return time and str(time) or ""



def page_period(obj):
    s = page_date(obj["start_date"])
    if obj["start_time"]:
        s += ", %s" % page_time(obj["start_time"])
    elif obj["end_time"]:
        s += ", ??:??"
    s += " "
    if (obj["end_date"] and obj["end_date"] != obj["start_date"]) or obj["end_time"]:
        s += " -"
    if obj["end_date"] and obj["end_date"] != obj["start_date"]:
        s += " %s" % page_date(obj["end_date"])
    if obj["end_time"]:
        if obj["end_date"] and obj["end_date"] != obj["start_date"]:
            s += ","
        s += " %s" % page_time(obj["end_time"])
    return s



def has_link_parent(soup):
    if not soup.parent:
        return False
    if soup.parent.name == "a":
        return True
    return has_link_parent(soup.parent)



def convert_links(text, quote="\""):
    soup = BeautifulSoup(text, "html.parser")
    for t in soup.findAll(text=True):
        if has_link_parent(t):
            continue
        split = re.split("(?:(https?://)|(www\.))([\S]+\.[^\s<>\"\']+)", t)
        r = u""
        n = 0
        split = [s or u"" for s in split]
        while split:
            if n % 2 == 0:
                r += split[0]
                split.pop(0)
            else:
                r += u"<a href=%shttp://%s%s%s>%s%s%s</a>" % (
                    quote, split[1], split[2], quote, split[0], split[1], split[2]
                    )
                split.pop(0)
                split.pop(0)
                split.pop(0)
            n += 1

        t.replaceWith(BeautifulSoup(r, "html.parser"))
    return unicode(soup)



class BaseHandler(RequestHandler):

    def __init__(self, *args, **kwargs):
        self.messages = []
        self.scripts = []
        RequestHandler.__init__(self, *args, **kwargs)
        self.has_javascript = bool(self.get_cookie("j"))
        self.set_parameters()
        self.next = self.get_argument("next", None)

    def _execute(self, transforms, *args, **kwargs):
        method = self.get_argument("_method", None)
        if method and self.request.method.lower() == "post":
            self.request.method = method.upper()
        try:
            RequestHandler._execute(self, transforms, *args, **kwargs)
        except IOError as e:
            print 'ioerror'
            raise e
        except AssertionError as e:
            print 'assertionerror'
            raise e
            

    def write_error(self, status_code, **kwargs):
        if 'exc_info' in kwargs:
            exc_info = kwargs.pop('exc_info')
            if exc_info:
                exception = exc_info[1]
                if hasattr(exception, "log_message"):
                    message = exception.log_message
                    status_message = httplib.responses[status_code]
                    self.render("error.html",
                                status_code=status_code,
                                status_message=status_message,
                                message=message,
                                )
                    self.finish()
                    return
        RequestHandler.write_error(self, status_code, **kwargs)

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

    @staticmethod
    def geo_in(latitude, longitude, geobox):
        if not geobox:
            return True
        if latitude < geobox["latmin"] or latitude > geobox["latmax"]:
            return False
        if longitude < geobox["lonmin"] or longitude > geobox["lonmax"]:
            return False
        return True

    def query_rewrite(self, options):
        arguments = self.request.arguments.copy()
        arguments.update(options)
        uri = self.request.path
        if uri.startswith("/"):
            uri = self.application.url_root + uri[1:]
        uri += "?" + urlencode(arguments, True)
        return uri

    def url_rewrite(self, uri, options=None, parameters=None, next_=None):
        """
        Rewrites URLs to:
            prepend url_root to absolute paths if it's not already there
            add parameters, optionally overwritten.

        uri:      an URL without the url root
        options:  optional parameters to write over self.parameters

        query priority:
            next_
            options
            uri query string
            parameters
        """

        if options is None:
            options = {}
        
        if parameters is None:
            parameters = self.parameters
        
        scheme, netloc, path, query, fragment = urlparse.urlsplit(uri)

        if path.startswith("/"):
            path = self.application.url_root + path[1:]

        arguments = parameters.copy()

        for key, value in urlparse.parse_qs(query, keep_blank_values=False).items():
            arguments[key] = value
            if value is None:
                del arguments[key]
                continue

        for key, value in options.items():
            arguments[key] = value
            if value is None:
                del arguments[key]
                continue

        if next_:
            arguments["next"] = self.url_rewrite(next_, parameters={})

        query = urlencode(arguments, True)

        uri = urlparse.urlunsplit((scheme, netloc, path, query, fragment))
        return uri

    def redirect_next(self, default_url=None):
        """
        Redirects to self.next if supplied, else the default url, else '/'.

        Does not terminate handle execution, so usual syntax should be:

            return self.redirect_next()

        self.next:
            *should* include url_root when used on pages
            *shouldn't* include url_root when used in handlers
            *should* include important query options everywhere
            *shouln't* include duplicate parameters anywhere
        """
        self.redirect(self.url_rewrite(
                self.next or default_url or '/'
                ))

    def render(self, template_name, **kwargs):
        mako_template = self.application.lookup.get_template(template_name)

        kwargs.update({
                "geo_in": self.geo_in,
                "next": self.next,
                "messages": self.messages,
                "scripts": self.scripts,
                "newline": newline,
                "newline_comma": newline_comma,
                "nbsp": nbsp,
                "form_date": form_date,
                "form_time": form_time,
                "page_date": page_date,
                "page_date_format": page_date_format,
                "page_time": page_time,
                "page_period": page_period,
                "markdown_safe": markdown_safe,
                "convert_links": convert_links,
                "current_user": self.current_user,
                "moderator": self.moderator,
                "uri": self.request.uri,
                "xsrf": self.xsrf_token,
                "json_dumps": json.dumps,
                "query_rewrite": self.query_rewrite,
                "url_rewrite": self.url_rewrite,
                "parameters": self.parameters,
                "parameters_json": json.dumps(self.parameters),
                "url_root": self.application.url_root,
                "skin_variables": self.application.skin_variables,
                })

        try:
            self.write(mako_template.render(**kwargs))
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
        except NoResultFound:
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



    # Arguments

    _ARG_DEFAULT_MANGO = []

    def get_argument_restricted(self, name, fn, message,
                                default=_ARG_DEFAULT_MANGO, json=False):
        value = self.get_argument(name, default, json)

        if value == default:
            if default is self._ARG_DEFAULT_MANGO:
                raise HTTPError(400, "Missing argument %s" % name)
            return value

        try:
            value = fn(value)
        except ValueError:
            raise HTTPError(400, repr(value) + " " + message)
        return value

    def get_argument_allowed(self, name, allowed, default=_ARG_DEFAULT_MANGO, json=False):
        def test(value, allowed):
            if not value in allowed:
                raise ValueError
            return value
        return self.get_argument_restricted(
            name,
            lambda value: test(value, allowed),
            "'%s' value is not in the allowed set (%s)." % (name, [repr(v) for v in allowed]),
            default,
            json)

    def get_argument_int(self, name, default=_ARG_DEFAULT_MANGO, json=False):
        return self.get_argument_restricted(
            name,
            lambda value: int(value),
            "Value must be an integer number",
            default,
            json)

    def get_argument_bool(self, name, default=_ARG_DEFAULT_MANGO, json=False):
        def helper(value):
            value = value.strip().lower()
            if value.strip() in ['yes', 'y', 'true', 't', '1']:
                return True
            if value.strip() in ['no', 'n', 'false', 'f', '0']:
                return False
            raise ValueError
            
        return self.get_argument_restricted(
            name,
            helper,
            "Value must be a boolean, eg. True, y, 1, f, no, 0, etc.",
            default,
            json)

    def get_argument_float(self, name, default=_ARG_DEFAULT_MANGO, json=False):
        return self.get_argument_restricted(
            name,
            lambda value: float(value),
            "Value must be a floating point number",
            default,
            json)

    def get_argument_date(self, name, default=_ARG_DEFAULT_MANGO, json=False):
        return self.get_argument_restricted(
            name,
            lambda value: datetime.datetime.strptime(value, "%Y-%m-%d").date(),
            "Value must be in the format 'YYYY-MM-DD', eg. 2012-02-17",
            default,
            json)

    def get_argument_time(self, name, default=_ARG_DEFAULT_MANGO, json=False):
        return self.get_argument_restricted(
            name,
            lambda value: datetime.datetime.strptime(value, "%H:%M").time(),
            "Value must be in the 24-hour format 'HH:MM, eg. 19:30",
            default,
            json)

    def get_argument_order(self, name, default=_ARG_DEFAULT_MANGO, json=False):
        return self.get_argument_allowed(
            name, ("asc", "desc"), default,
            json)

    def get_argument_public(self, name="public", default=_ARG_DEFAULT_MANGO, json=False):
        table = {
            "null": None,
            "true": True, 
            "false": False,
            None: None,
            True: True, 
            False: False,
            }
        value = self.get_argument_allowed(
            name, table.keys(), default,
            json)
        return table[value]

    def get_argument_visibility(self, json=False):
        if not self.moderator:
            return None
        return self.get_argument_allowed(
            "visibility", ("pending", "all", "private", "public"), None, json)

    def get_argument_view(self, json=False):
        if not self.current_user:
            return None
        return self.get_argument_allowed(
            "view", ("browse", "edit"), None, json)

    def get_argument_geobox(self, name, default=_ARG_DEFAULT_MANGO, json=False):
        value = self.get_argument(name, default, json)

        if value == default:
            if default is self._ARG_DEFAULT_MANGO:
                raise HTTPError(400, "Missing argument %s" % name)
            return value

        try:
            return geo.Geobox(value)
        except ValueError:
            pass

        try:
            return geo.bounds(value)
        except ValueError:
            pass

        raise HTTPError(400, "Could not decode %s value %s" % (name, value))



    # End arguments




    def get_json_data(self):
        if hasattr(self, "json_data") and self.json_data:
            return
        if self.request.body:
            try:
                self.json_data = json.loads(self.request.body)
            except ValueError as e:
                raise HTTPError(400, "Could not decode JSON data.")
        else:
            self.json_data = {}

    def get_argument(self, name, default=_ARG_DEFAULT_MANGO, json=False):
        if not json:
            if default is self._ARG_DEFAULT_MANGO:
                default = RequestHandler._ARG_DEFAULT
            return RequestHandler.get_argument(self, name, default)

        self.get_json_data()

        if not name in self.json_data:
            if default is self._ARG_DEFAULT_MANGO:
                raise HTTPError(400, "Missing argument %s" % name)
            return default

        return self.json_data[name]

    def get_arguments(self, name, strip=True, json=False):
        if not json:
            return RequestHandler.get_arguments(self, name, strip)

        self.get_json_data()
        return self.json_data.get(name)

    def get_arguments_multi(self, name, delimiter=",", json=False):
        ret = []
        args = self.get_arguments(name, strip=True, json=json)
        if not args:
            return ret
        for arg in args:
            ret += [value.strip() for value in arg.split(delimiter)]
        return ret

    def get_arguments_int(self, name):
        return [int(value) for value in self.get_arguments(name)]




    def dump_json(self, obj):
        return json.dumps(obj, indent=2)

    def write_json(self, obj):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(self.dump_json(obj))

    def has_geo_arguments(self):
        self.lookup = self.get_argument("lookup", None)
        return bool(
            self.get_argument_geobox(default=None) or \
                self.get_argument_latlon("latlon", None) or \
                self.lookup
            )

    def get_geobox(self):
        geobox = self.get_argument_geobox(default=None)
        if geobox:
            return geobox
        latlon = self.get_argument_latlon("latlon", None)
        distance = self.get_argument_float("distance", 25)
        if not latlon:
            lookup = self.get_argument("lookup", None)
            if lookup:
                latlon = geo.geocode(lookup)
                if not latlon:
                    self.messages.append(("WARNING", "Could not find address: '%s'." % lookup))
                    return None
        if not latlon:
            return None
        return Address.geobox(latlon[0], latlon[1], distance)

    def geo_address_query(self):
        query = self.orm.query(Address)
        geobox = self.get_geobox()
        return Address.filter_geobox(query, geobox)

    def filter_geo(self, address_list, limit=10):
        geobox = self.get_argument_geobox(default=None)
        latlon = self.get_argument_latlon("latlon", None)
        if geobox:
            return Address.filter_geobox(address_list, geobox), geobox, latlon

        # Find geobox around the center that includes at least 10 matches
        if not latlon:
            lookup = self.get_argument("lookup", None)
            if lookup:
                latlon = geo.geocode(lookup)
                if not latlon:
                    self.messages.append(("WARNING", "Could not find address: '%s'." % lookup))
        if not latlon:
            return address_list.limit(limit), geobox, latlon

        address_list_2 = Address.order_distance(address_list, latlon)
        address_list_2 = address_list_2.limit(limit)
        max_dist = Address.max_distance(
            self.orm, address_list_2, latlon[0], latlon[1])
        max_dist *= 1.1

        scale = Address.scale(latlon[0])

        values = (
            latlon[0] - max_dist,
            latlon[0] + max_dist,
            max(latlon[1] - max_dist / max(scale, 0.01), -180),
            min(latlon[1] + max_dist / max(scale, 0.01), 180),
            )
        geobox = dict(zip(["latmin", "latmax", "lonmin", "lonmax"], values))
        return Address.filter_geobox(address_list, geobox), geobox, latlon

    def filter_visibility(self, query, Entity, visibility=None,
                          secondary=False, null_column=False):
        """
        visibility:  "public", "pending", "private", "all". Unknown = "public".
        """

        if secondary:
            if visibility in ["pending", "private"]:
                visibility = "all"
        filter_args = []
        if null_column:
            filter_args.append(null_column==None)
        if self.moderator and visibility:
            if visibility == "pending":
                filter_args.append(Entity.public==None)
            elif visibility == "all":
                filter_args = []
            elif visibility == "private":
                filter_args.append(Entity.public==False)
            else:
                filter_args.append(Entity.public==True)
        else:
            filter_args.append(Entity.public==True)
        if filter_args:
            return query.filter(or_(*filter_args))
        return query

    def set_parameters(self):
        self.parameters = {}
        is_json = self.content_type("application/json")
        visibility = self.get_argument_visibility(json=is_json)
        if visibility:
            self.parameters["visibility"] = visibility
        view = self.get_argument_view(json=is_json)
        if view:
            self.parameters["view"] = view
        

    def deep_visible(self):
        return self.parameters.get("visibility", None) in ["pending", "private", "all"]
    
    def orm_commit(self):
        try:
            self.orm.commit()
        except IntegrityError as e:
            raise HTTPError(500, e.message)
        self.application.increment_cache()

    @property
    def moderator(self):
        return bool(self.current_user and self.current_user.moderator)

    @property
    def orm(self):
        return self.application.orm

    @property
    def cache(self):
        return self.application.cache

    @property
    def url_root(self):
        return self.application.url_root



HistoryEntity = namedtuple(
    "HistoryEntity",
    [
        "type",
        "entity_id",
        "entity_v_id",
        "date",
        "existence",
        "existence_v",
        "is_latest",
        "public",
        "name",
        "user_id",
        "user_name",
        "user_moderator",
        "gravatar_hash",
        "url",
        "url_v",
        ]
    )
        


class MangoBaseEntityHandlerMixin(RequestHandler):
    def _create_revision(self):
        is_json = self.content_type("application/json")

        if self.moderator:
            public = self.get_argument_public("public", json=is_json)
        else:
            public = None
        moderation_user = self.current_user

        return public, moderation_user

    def _history_query(self,
                       Entity, entity_id,
                       Entity_v,
                       id_string):
        id_ = int(id_string)

        entity_query = self.orm.query(Entity) \
            .filter(getattr(Entity, entity_id) == id_)

        try:
            entity = entity_query.one()
        except NoResultFound:
            entity = None

        entity_v_query = self.orm.query(Entity_v) \
            .filter(getattr(Entity_v, entity_id) == id_)

        if not self.moderator:
            if entity:
                filters = or_(
                    and_(
                        Entity_v.moderation_user_id == self.current_user.user_id,
                        Entity_v.a_time > entity.a_time,
                        ),
                    and_(
                        Entity_v.a_time == entity.a_time,
                        Entity_v.public == True,
                        ),
                    )
            else:
                filters = Entity_v.moderation_user_id == self.current_user.user_id
            entity_v_query = entity_v_query \
                .filter(filters)

        return entity_v_query, entity



    def _get_entity(self,
                    Entity, entity_type, entity_id,
                    Entity_v, entity_v_type, entity_v_id,
                    id_string,
                    required=True, future_version=None,
                    ):
        """
        future_version = True: prefer future versions
        future_version = None: accept future versions
        future_version = False: ignore future versions

        future versions with existence == False are always ignored.
        """

        id_ = int(id_string)

        entity = None

        query = self.orm.query(Entity) \
            .filter(getattr(Entity, entity_id) == id_)
        
        try:
            entity_any = query.one()
        except NoResultFound:
            entity_any = None
            
        if self.current_user and not self.moderator and future_version is True:
            query = self.orm.query(Entity_v) \
                .filter(getattr(Entity_v, entity_id) == id_) \
                .filter(Entity_v.moderation_user_id==self.current_user.user_id) \
                .order_by(Entity_v.a_time.desc()) \
                .limit(1)

            try:
                entity_v = query.one()
            except NoResultFound:
                entity_v = None

            if entity_v and not (entity_v.existence and (entity_any is None or entity_v.a_time > entity_any.a_time)):
                entity_v = None

            if entity_v:
                entity = entity_v

        if not entity:
            query = self.orm.query(Entity) \
                .filter(getattr(Entity, entity_id) == id_)

            if not self.moderator:
                query = query \
                    .filter_by(public=True)

            try:
                entity = query.one()
            except NoResultFound:
                entity = None

        if not entity and self.current_user:
            if self.moderator:
                if required:
                    query = self.orm.query(Entity_v) \
                        .filter(getattr(Entity_v, entity_id) == id_)
                    if query.count():
                        self.next = "%s/%d/revision" % (Entity.list_url, id_)
                        return self.redirect_next()
            elif future_version is not False:
                query = self.orm.query(Entity_v) \
                    .filter(getattr(Entity_v, entity_id) == id_) \
                    .filter(Entity_v.moderation_user_id==self.current_user.user_id) \
                    .order_by(Entity_v.a_time.desc()) \
                    .limit(1)
                
                try:
                    entity_v = query.one()
                except NoResultFound:
                    entity_v = None

                if entity_v and not (entity_v.existence and (entity_any is None or entity_v.a_time > entity_any.a_time)):
                    entity_v = None

                if entity_v:
                    entity = entity_v

        if required and not entity:
            raise HTTPError(404, "%d: No such %s" % (id_, entity_type))

        return entity



class MangoEntityHandlerMixin(RequestHandler):
    def _get_entity(self,
                    Entity, entity_type, entity_id,
                    id_string, query_options, required=True):
        print "MangoEntityHandlerMixin._get_entity"
        id_ = int(id_string)

        query = self.orm.query(Entity) \
            .filter(
            Entity.get(entity_id) == id_
            )

        if options:
            query = query \
                .options(*options)

        if not self.moderator:
            query = query \
                .filter_by(public=True)

        try:
            entity = query.one()
        except NoResultFound:
            entity = None

        if required and not entity:
            raise HTTPError(404, "%d: No such %s" % (id_, entity_type))

        return entity

    def _before_delete(self, entity):
        pass

    @authenticated
    def delete(self, entity_id_string):
        if not self.moderator:
            raise HTTPError(404)

        entity = self._get(entity_id_string)
        if self._before_delete:
            self._before_delete(entity)
        self.orm.delete(entity)
        self.orm_commit()
        return self.redirect_next(entity.list_url)
        
    @authenticated
    def put(self, entity_id_string):
        old_entity = self._get(entity_id_string, required=False)
        ignore_list = None
        if self.moderator:
            new_entity = self._create(id_=int(entity_id_string))
        else:
            new_entity = self._create_v(id_=int(entity_id_string))
            ignore_list = ["public"]
        if old_entity:
            if old_entity.content_same(new_entity, ignore_list):
                return self.redirect_next(old_entity.url)
            if self.moderator:
                old_entity.content_copy(
                    new_entity, self.current_user, ignore_list)
                self.orm_commit()
                return self.redirect_next(old_entity.url)
        self.orm.add(new_entity)
        self.orm_commit()
        return self.redirect_next(new_entity.url)



class MangoEntityListHandlerMixin(RequestHandler):
    @authenticated
    def post(self):
        new_entity = self._create()
        self.orm.add(new_entity)
        self.orm_commit()
        if self.moderator:
            return self.redirect_next(new_entity.url)

        id_ = getattr(new_entity, self.entity_id)

        self.orm.delete(new_entity)
        self.orm_commit()

        self.orm.query(self.Entity_v) \
            .filter(getattr(self.Entity_v, self.entity_id)==id_) \
            .delete()
        self.orm_commit()

        new_entity_v = self._create_v(id_)
        self.orm.add(new_entity_v)
        self.orm_commit()
        return self.redirect_next(new_entity_v.url)



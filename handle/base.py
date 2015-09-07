# -*- coding: utf-8 -*-

import re
import json
import time
import codecs
import bleach
import hashlib
import httplib
import markdown
import datetime
import urlparse
import functools
from urllib import urlencode
from collections import namedtuple

from bs4 import BeautifulSoup
from sqlalchemy import and_, or_, not_
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.expression import exists, and_, or_
from mako import exceptions

from tornado.web import RequestHandler, HTTPError
# from tornado.web import authenticated as tornado_authenticated

# For _execute replacement
from tornado.concurrent import Future, is_future
from tornado import gen
from tornado.web import _has_stream_request_body

import geo

from model import Session, Address, User, camel_case

from base_moderation import has_pending, has_address_not_found



md = markdown.Markdown()



def sha1_concat(*parts):
    sha1 = hashlib.sha1()
    for part in parts:
        sha1.update(part)
    return sha1.hexdigest()



def authenticated(method):
    u"Replaces tornado decorator."

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        login = self.get_argument_bool("login", None)

        if not (self.current_user or login):
            raise HTTPError(404, "Not found")

        return method(self, *args, **kwargs)
    wrapper.authenticated = True;
    return wrapper



def newline(text):
    return text.replace("\n", "<br>")



def newline_comma(text):
    return text.replace("\n", ", ")



def nbsp(text):
    text = re.sub("[\s]+", "&nbsp;", text)
    text = text.replace("-", "&#8209;")
    return text



def markdown_safe(text):
    markdown = md.convert(text)
    clean = bleach.clean(
        markdown,
        tags=[
            "a",
            "p",
            "ul",
            "ol",
            "li",
            "em",
            "img",
            "strong",
        ],
        attributes=[
            "href",
            "src",
            "alt",
        ]
    )
    return clean



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
    s = page_date(obj["startDate"])
    if obj["startTime"]:
        s += ", %s" % page_time(obj["startTime"])
    elif obj["endTime"]:
        s += ", ??:??"
    s += " "
    if (obj["endDate"] and obj["endDate"] != obj["startDate"]) or obj["endTime"]:
        s += " -"
    if obj["endDate"] and obj["endDate"] != obj["startDate"]:
        s += " %s" % page_date(obj["endDate"])
    if obj["endTime"]:
        if obj["endDate"] and obj["endDate"] != obj["startDate"]:
            s += ","
        s += " %s" % page_time(obj["endTime"])
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
        if len(split) == 1:
            continue
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



def url_rewrite_static(uri, root=None, options=None, parameters=None, next_=None):
        """
        Rewrites URLs to:
            prepend url_root to absolute paths if it's not already there
            add parameters, optionally overwritten.

        Query parameter precedence:
            next_
            options
            uri query string
            parameters
        """

        if options is None:
            options = {}
        
        if parameters is None:
            parameters = {}
        
        if root is None:
            root = "/"
        
        scheme, netloc, path, query, fragment = urlparse.urlsplit(uri)

        if path.startswith("/") and not path.startswith(root):
            path = root + path[1:]

        arguments = parameters.copy()

        for key, value in urlparse.parse_qs(query, keep_blank_values=False).items():
            arguments[key] = value
            if value is None:
                del arguments[key]

        for key, value in options.items():
            arguments[key] = value
            if value is None:
                del arguments[key]

        if next_:
            arguments["next"] = url_rewrite_static(next_, root)

        query = urlencode(arguments, True)

        uri = urlparse.urlunsplit((scheme, netloc, path, query, fragment))
        return uri




class BaseHandler(RequestHandler):

    _unsupported_method_error = (403, "Method Not Allowed")

    def __init__(self, *args, **kwargs):
        self.SUPPORTED_METHODS += ("TOUCH", )
        self.messages = []
        self.scripts = []
        RequestHandler.__init__(self, *args, **kwargs)
        self.orm = self.application.orm()
        self.url_root = self.request.headers.get(u"X-Forwarded-Root", "/")
        self.has_javascript = bool(self.get_cookie("j"))
        self.set_parameters()
        self.next_ = self.get_argument("next", None)
        self.load_map = False

    def prepare(self):
        self.start = time.time()

    def on_finish(self):
        if hasattr(self, "start"):
            self.application.log_uri.info("%s, %s, %s, %s, %0.3f" % (
                    str(time.time()),
                    self.request.uri,
                    self.request.remote_ip,
                    repr(self.request.headers.get("User-Agent", "User-Agent")),
                    time.time() - self.start
                    ))
        self.application.orm.remove()

    def initialize(self, **kwargs):
        self.arg_type_handlers = kwargs.get("types", [])

    def _mango_extra_methods(self):
        method = self.get_argument("_method", None)
        if method and self.request.method.lower() == "post":
            self.request.method = method.upper()
        
    def _mango_check_user(self):
        if self.current_user:
            if self.current_user.locked:
                self.delete_current_user()
                self.end_session()
                raise HTTPError(400, "User account is locked.")

    def _mango_handle_args(self):
        if self.arg_type_handlers:
            if len(self.path_args) != len(self.arg_type_handlers):
                raise HTTPError(500, "Bad args/type handlers combination")

            self.path_args = list(self.path_args)
            for i, (value, type_handler) in enumerate(zip(self.path_args, self.arg_type_handlers)):
                if self.arg_type_handlers[i]:
                    self.path_args[i] = self.arg_type_handlers[i](value)
            self.path_args = tuple(self.path_args)

    # Copied from tornado.web. Keep updated
    @gen.coroutine
    def _execute(self, transforms, *args, **kwargs):
        """Executes this request with the given output transforms."""
        self._transforms = transforms

        # mango start
        self._mango_extra_methods()
        # mango end
        
        try:
            # mango start
            if (self.request.method not in self.SUPPORTED_METHODS) or \
               (hasattr(self, "_unsupported_methods") and (
                   True in self._unsupported_methods or \
                   self.request.method.lower() in self._unsupported_methods
               )):
                code, message = self._unsupported_method_error
                raise HTTPError(code, message)
            self._mango_check_user()
            # mango end
            
            self.path_args = [self.decode_argument(arg) for arg in args]
            self.path_kwargs = dict((k, self.decode_argument(v, name=k))
                                    for (k, v) in kwargs.items())

            # mango end
            self._mango_handle_args()
            # mango start
            
            # If XSRF cookies are turned on, reject form submissions without
            # the proper cookie
            if self.request.method not in ("GET", "HEAD", "OPTIONS") and \
                    self.application.settings.get("xsrf_cookies"):
                self.check_xsrf_cookie()

            result = self.prepare()
            if is_future(result):
                result = yield result
            if result is not None:
                raise TypeError("Expected None, got %r" % result)
            if self._prepared_future is not None:
                # Tell the Application we've finished with prepare()
                # and are ready for the body to arrive.
                self._prepared_future.set_result(None)
            if self._finished:
                return

            if _has_stream_request_body(self.__class__):
                # In streaming mode request.body is a Future that signals
                # the body has been completely received.  The Future has no
                # result; the data has been passed to self.data_received
                # instead.
                try:
                    yield self.request.body
                except iostream.StreamClosedError:
                    return

            method = getattr(self, self.request.method.lower())
            result = method(*self.path_args, **self.path_kwargs)
            if is_future(result):
                result = yield result
            if result is not None:
                raise TypeError("Expected None, got %r" % result)
            if self._auto_finish and not self._finished:
                self.finish()

        # mango start - Think this is to catch MySQL errors?
        except IOError as e:
            print 'ioerror'
            raise e
        except AssertionError as e:
            print 'assertionerror'
            raise e
        # mango end
        
        except Exception as e:
            self._handle_request_exception(e)
            if (self._prepared_future is not None and
                    not self._prepared_future.done()):
                # In case we failed before setting _prepared_future, do it
                # now (to unblock the HTTP server).  Note that this is not
                # in a finally block to avoid GC issues prior to Python 3.4.
                self._prepared_future.set_result(None)

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

    def delete_current_user(self):
        self._current_user = None

    def content_type(self, name):
        if "Content-Type" in self.request.headers:
            return self.request.headers["Content-Type"].lower() == name.lower()
        return False

    def accept_type(self, name):
        if "Accept" in self.request.headers:
            return name.lower() in self.request.headers["Accept"].lower()
        return False

    def is_local(self):
        return self.request.remote_ip == "127.0.0.1"

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

    def query_rewrite(self, options):
        arguments = self.request.arguments.copy()
        arguments.update(options)
        uri = self.request.path
        if uri.startswith("/"):
            uri = self.url_root + uri[1:]
        uri += "?" + urlencode(arguments, True)
        return uri

    def url_rewrite(self, uri, options=None, parameters=None, next_=None):
        if parameters is None:
            parameters = self.parameters

        return url_rewrite_static(uri, self.url_root, options, parameters, next_)

    def redirect_next(self, default_url=None):
        """
        Redirects to self.next_ if supplied, else the default url, else '/'.

        Does not terminate handle execution, so usual syntax should be:

            return self.redirect_next()

        self.next_:
            *should* include url_root when used on pages
            *shouldn't* include url_root when used in handlers
            *should* include important query options everywhere
            *shouln't* include duplicate parameters anywhere
        """
        self.redirect(self.url_rewrite(
                self.next_ or default_url or '/'
                ))

    def static_url(self, path, include_host=None):


        return self.url_root[:-1] + "/static/" + path


        url = RequestHandler.static_url(self, path, include_host)
        return self.url_root[:-1] + url

    def render(self, template_name, **kwargs):
        def purge(a, b):
            if b:
                a[:] = filter(lambda x: x not in b, a)

        # vendro
        scripts1 = ["jquery.min.js", "jquery-ui/jquery-ui.min.js", "tag-it.js", "underscore-min.js", "backbone-min.js", "markdown.js", "jquery.history.js", "jquery.ui.timepicker.js", "markerclusterer.js"]
        # before page js variables
        scripts2 = ["geobox.js", "template.js", "mango.js"]
        # after page js variables
        scripts3 = ["address.js", "tag.js", "entity.js", "event.js", "org.js"]
        if self.load_map:
            scripts3 = ["map.js"] + scripts3
        stylesheets = ["jquery-ui/jquery-ui.css", "tag-it.css", "jquery.ui.timepicker.css", "style.css"]
        purge(scripts1, self.application.skin.scripts())
        purge(stylesheets, self.application.skin.stylesheets())

        components = self.application.skin.load(
            static_url=self.static_url,
            url_root=self.url_root,
            stylesheets=stylesheets,
            protocol=self.request.protocol,
            offsite=self.application.offsite,
            header_function=True,
            load_nav=True,
            )

        mako_template = self.application.lookup.get_template(template_name)

        kwargs.update({
            "url_root": self.url_root,
            "protocol": self.request.protocol,
            "static_url": self.static_url,
            "scripts1": scripts1,
            "scripts2": scripts2,
            "scripts3": scripts3,
            "header": components["header"],
            "footer": components["footer"],

            "load_map": self.load_map,
            "next_": self.next_,
            "messages": self.messages,
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
            "camel_case": camel_case,
            "current_user": self.current_user,
            "moderator": self.moderator,
            "contributor": self.contributor,
            "uri": self.request.uri,
            "xsrf": self.xsrf_token,
            "events_enabled": self.application.events,
            "json_dumps": json.dumps,
            "query_rewrite": self.query_rewrite,
            "url_rewrite": self.url_rewrite,
            "parameters": self.parameters,
            "parameters_json": json.dumps(self.parameters),
        })

        if self.moderator:
            kwargs.update({
                "has_queue": has_pending(self.orm),
                "has_address_not_found": has_address_not_found(self.orm),
            })

        try:
            self.write(mako_template.render(**kwargs))
        except:
            self.write(exceptions.html_error_template().render())
        if self.orm.new or self.orm.dirty or self.orm.deleted:
            print self.orm.new or self.orm.dirty or self.orm.deleted
            self.orm.rollback()

    def compare_session(self, session):
        # Returns falsy if equal, truthy if different
        return \
            cmp(session.ip_address, self.request.remote_ip) or \
            cmp(session.accept_language, self.get_accept_language()) or \
            cmp(session.user_agent, self.get_user_agent())

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

        if self.compare_session(session):
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


    # Entities

    @staticmethod
    def _get_autoincrement(orm, table):
        sql_get = u"""
select auto_increment
  from information_schema.tables
  where table_name = '%s'
  and table_schema = database( );
""" % table
        (value, ) = orm.execute(sql_get).fetchone()
        return value

    @staticmethod
    def _set_autoincrement(orm, Entity, entity_id, auto_id):
        entity = Entity._dummy(orm)
        setattr(entity, entity_id, auto_id)
        orm.add(entity)
        # Updating auto_increment is permanent even after rollback
        orm.flush()
        orm.rollback()

    def _update_entity_autoincrement(self, Entity, Entity_v, entity_id):
        # MySQL resets InnoDB auto_increment to the highest ID + 1 on restart,
        # so we need to update autoincrement in case any pending versions
        # have a higher ID (ie. if the DB has been reset and the last entity
        # added was not approved by a moderator yet).
        # This is still susceptible to race conditions but not by so much.
        attr_id = getattr(Entity_v, entity_id)
        auto_id = self._get_autoincrement(self.orm, Entity.__table__)
        (max_id, ) = self.orm.query(attr_id) \
            .order_by(attr_id.desc()) \
            .first()
        # print Entity.__table__, auto_id, max_id
        if max_id >= auto_id:
            self._set_autoincrement(self.orm, Entity, entity_id, max_id)
        auto_id = self._get_autoincrement(self.orm, Entity.__table__)
        # print auto_id


    # Arguments

    _ARG_DEFAULT_MANGO = []

    def get_argument_restricted(self, name, fn, message,
                                default=_ARG_DEFAULT_MANGO, json=False):
        value = self.get_argument(name, default, json)
        if value == "":
            value = default

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

    def get_argument_geobox(self, name, min_radius=None, default=_ARG_DEFAULT_MANGO, json=False):
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
            return geo.bounds(value, min_radius=min_radius)
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
        for arg in args:
            for value in arg.split(delimiter):
                value = unicode(value.strip())
                if value:
                    ret.append(value)
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
    def contributor(self):
        return bool(self.current_user and not self.current_user.moderator)

    @property
    def cache(self):
        return self.application.cache



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
            # Suggestions will be created pending
            public = None
        moderation_user = self.current_user

        return public, moderation_user

    def _history_query(self,
                       Entity, entity_id,
                       Entity_v,
                       id_):

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
                    Entity, entity_id,
                    entity_type,
                    id_,
                    required=True,
                    ):

        query = self.orm.query(Entity) \
            .filter(getattr(Entity, entity_id) == id_)
        
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


    def _get_entity_v(self,
                      Entity, entity_id,
                      Entity_v, entity_v_id,
                      entity_type,
                      id_,
                      ):
        if not self.current_user:
            raise HTTPError(404)
        
        entity_v_mod = self.orm.query(Entity_v) \
            .join((User, Entity_v.moderation_user)) \
            .filter(getattr(Entity_v, entity_id) == id_) \
            .filter(User.moderator == True) \
            .subquery()

        query = self.orm.query(Entity_v) \
            .filter(getattr(Entity_v, entity_id) == id_)
        
        if not self.moderator:
            query = query \
                .filter(Entity_v.moderation_user_id==self.current_user.user_id)
        query = query \
            .filter(~exists().where(
                entity_v_mod.c.a_time >= Entity_v.a_time
                )) \
            .order_by(getattr(Entity_v, entity_v_id).desc()) \
            .limit(1)

        try:
            entity_v = query.one()
        except NoResultFound:
            entity_v = None

        if entity_v and not entity_v.existence:
            entity_v = None

        return entity_v


    def _touch_entity(self,
                      Entity, entity_id,
                      entity_type,
                      decline_v,
                      id_,
                  ):
        """
        Moderators only already checked
        Return: entity or entity_v, exists
        """

        query = self.orm.query(Entity) \
            .filter(getattr(Entity, entity_id) == id_)
        
        try:
            entity = query.one()
        except NoResultFound:
            entity = None
            
        if entity:
            entity.a_time = 0;
            entity.moderation_user = self.current_user
            return entity, True

        declined_entity_v = decline_v(id_, self.current_user)
        self.orm.add(declined_entity_v)
        return declined_entity_v, False


    def _touch_pending_child_entities(
            self, Entity, entity_id_attr, entity_type, declined_parent_id, 
            get_pending_parent_entity_id, decline_v):

        for row in get_pending_parent_entity_id(self.orm):
            parent_id, parent_desc, parent_exists = row[:3]
            entity_id, entity_desc_new, entity_exists, entity_desc_old, user_name = row[3:]
            if parent_id == declined_parent_id:
                MangoBaseEntityHandlerMixin._touch_entity(
                    self, Entity, entity_id_attr, entity_type, decline_v, entity_id)


        


class MangoEntityHandlerMixin(RequestHandler):
    def _before_delete(self, entity):
        pass

    def _before_set(self, entity):
        pass

    def _after_accept_new(self, entity):
        pass

    def get_note_arguments(self):
        is_json = self.content_type("application/json")
        note_search = self.get_argument("note_search", None, json=is_json)
        note_order = self.get_argument_order("note_order", None, json=is_json)
        note_offset = self.get_argument_int("note_offset", None, json=is_json)
        return note_search, note_order, note_offset

    @authenticated
    def delete(self, entity_id):
        if not self.moderator:
            raise HTTPError(405)

        entity = self._get(entity_id)
        if self._before_delete:
            self._before_delete(entity)
        self.orm.delete(entity)
        self.orm_commit()
        return self.redirect_next()
        
    @authenticated
    def touch(self, entity_id):
        if not self.moderator:
            raise HTTPError(405)

        (entity_or_v, exists) = self._touch(entity_id)
        self.orm.commit()

        if exists:
            return self.redirect_next(entity_or_v.url)
        else:
            return self.redirect_next("%s/revision" % entity_or_v.url)
        
        
    @authenticated
    def put(self, entity_id):
        old_entity = self._get(entity_id, required=False)
        pre_entity = self._get_v(entity_id)
        
        if self.moderator:
            new_entity = self._create(id_=entity_id)
        else:
            new_entity = self._create_v(entity_id)
        if self._before_set:
            self._before_set(new_entity)

        if self.moderator and old_entity:
            if old_entity.content_same(new_entity):
                if not pre_entity:
                    return self.redirect_next(old_entity.url)
                old_entity.a_time = 0
                self.orm_commit()
            else:
                old_entity.content_copy(new_entity, self.current_user)
                self.orm_commit()
            return self.redirect_next(old_entity.url)
        if self.contributor:
            if pre_entity:
                if pre_entity.content_same(new_entity, public=False):
                    return self.redirect_next(new_entity.url)
            elif old_entity and old_entity.content_same(new_entity, public=False):
                return self.redirect_next(new_entity.url)
        self.orm.add(new_entity)
        self.orm_commit()
        if self.moderator and self._after_accept_new:
            self._after_accept_new(new_entity)
        return self.redirect_next(new_entity.url)



class MangoEntityListHandlerMixin(RequestHandler):
    def _before_set(self, entity):
        pass

    @authenticated
    def post(self):
        # Fix MySQL autoincrement reset
        self._update_entity_autoincrement(
            self.Entity, self.Entity_v, self.entity_id)

        new_entity = self._create()
        if self._before_set:
            self._before_set(new_entity)
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
        if self._before_set:
            self._before_set(new_entity_v)
        self.orm.add(new_entity_v)
        self.orm_commit()
        return self.redirect_next(new_entity_v.url)


class MarkdownSafeHandler(RequestHandler):
    def post(self):
        text = self.get_argument("text", "")
        autolinks = self.get_argument("convertLinks", None)
        
        html_safe = markdown_safe(text)

        if autolinks:
            html_safe = convert_links(html_safe)
            
        self.write(html_safe)

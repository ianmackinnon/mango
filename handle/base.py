# -*- coding: utf-8 -*-

import re
import json
import codecs
import hashlib
import httplib
import markdown
import datetime
import urlparse
import tornado.web

from urllib import urlencode
from bs4 import BeautifulSoup
from sqlalchemy import or_, not_
from sqlalchemy.orm.exc import NoResultFound
from mako import exceptions

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
    decorated = tornado.web.authenticated(f)
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



def page_date(date):
    return date and datetime.datetime.strptime(date, "%Y-%m-%d").date().strftime("%a %d %b %Y") or ""



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



class BaseHandler(tornado.web.RequestHandler):

    def __init__(self, *args, **kwargs):
        self.messages = []
        self.scripts = []
        tornado.web.RequestHandler.__init__(self, *args, **kwargs)
        self.has_javascript = bool(self.get_cookie("j"))
        self.set_parameters()
        self.next = self.get_argument("next", None)

    def _execute(self, transforms, *args, **kwargs):
        method = self.get_argument("_method", None)
        if method and self.request.method.lower() == "post":
            self.request.method = method.upper()
        tornado.web.RequestHandler._execute(self, transforms, *args, **kwargs)

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
        tornado.web.RequestHandler.write_error(self, status_code, **kwargs)

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
        arguments = self.request.arguments
        arguments.update(options)
        uri = self.request.path
        if uri.startswith("/"):
            uri = self.application.url_root + uri[1:]
        uri += "?" + urlencode(arguments, True)
        return uri

    def url_rewrite(self, uri, options=None):
        if options is None:
            options = {}
        scheme, netloc, path, query, fragment = urlparse.urlsplit(uri)

        arguments = urlparse.parse_qs(query, keep_blank_values=False)

        if path.startswith("/"):
            path = self.application.url_root + path[1:]

        for key, value in options.items():
            arguments[key] = value
            if value is None:
                del arguments[key]
                continue

        query = urlencode(arguments, True)

        uri = urlparse.urlunsplit((scheme, netloc, path, query, fragment))
        return uri

    def redirect_next(self, url):
        self.redirect(self.next or self.url_root[:-1] + url)        

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
                "page_time": page_time,
                "page_period": page_period,
                "markdown_safe": markdown_safe,
                "convert_links": convert_links,
                "current_user": self.current_user,
                "uri": self.request.uri,
                "xsrf": self.xsrf_token,
                "json_dumps": json.dumps,
                "query_rewrite": self.query_rewrite,
                "url_rewrite": self.url_rewrite,
                "parameters": self.parameters,
                "header1": None,
                "header2": None,
                "footer": None,
                "url_root": self.application.url_root,
                })

        if self.application.caat:
            kwargs["header1"], kwargs["header2"], kwargs["footer"] = \
            self.application.caat_header_footer()

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
                raise tornado.web.HTTPError(400, "Missing argument %s" % name)
            return value

        try:
            value = fn(value)
        except ValueError:
            raise tornado.web.HTTPError(400, repr(value) + " " + message)
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
        if not self.current_user:
            return None
        return self.get_argument_allowed(
            "visibility", ("pending", "all", "private", "public"), None, json)

    def get_argument_geobox(self, name, default=_ARG_DEFAULT_MANGO, json=False):
        value = self.get_argument(name, default, json)

        if value == default:
            if default is self._ARG_DEFAULT_MANGO:
                raise tornado.web.HTTPError(400, "Missing argument %s" % name)
            return value

        try:
            return geo.Geobox(value)
        except ValueError:
            pass

        try:
            return geo.bounds(value)
        except ValueError:
            pass

        raise tornado.web.HTTPError(400, "Could not decode %s value %s" % (name, value))



    # End arguments




    def get_json_data(self):
        if hasattr(self, "json_data") and self.json_data:
            return
        if self.request.body:
            try:
                self.json_data = json.loads(self.request.body)
            except ValueError as e:
                raise tornado.web.HTTPError(400, "Could not decode JSON data.")
        else:
            self.json_data = {}

    def get_argument(self, name, default=_ARG_DEFAULT_MANGO, json=False):
        if not json:
            if default is self._ARG_DEFAULT_MANGO:
                default = tornado.web.RequestHandler._ARG_DEFAULT
            return tornado.web.RequestHandler.get_argument(self, name, default)

        self.get_json_data()

        if not name in self.json_data:
            if default is self._ARG_DEFAULT_MANGO:
                raise tornado.web.HTTPError(400, "Missing argument %s" % name)
            return default

        return self.json_data[name]

    def get_arguments(self, name, strip=True, json=False):
        if not json:
            return tornado.web.RequestHandler.get_arguments(self, name, strip)

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
        if self.current_user and visibility:
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
        self.parameters["visibility"] = self.get_argument_visibility(json=is_json)

    def deep_visible(self):
        return self.parameters["visibility"] in ["pending", "private", "all"]
    
    @property
    def orm(self):
        return self.application.orm

    @property
    def cache(self):
        return self.application.cache

    @property
    def url_root(self):
        return self.application.url_root



class MangoEntityHandlerMixin(tornado.web.RequestHandler):
    @authenticated
    def delete(self, entity_id_string):
        entity = self._get(entity_id_string)
        if self._before_delete:
            self._before_delete(entity)
        self.orm.delete(entity)
        self.orm.commit()
        self.application.increment_cache()
        self.redirect_next(entity.list_url)
        
    @authenticated
    def put(self, entity_id_string):
        old_entity = self._get(entity_id_string)
        new_entity = self._create()
        if not old_entity.content_same(new_entity):
            old_entity.content_copy(new_entity, self.current_user)
            self.orm.commit()
            self.application.increment_cache()
        self.redirect_next(old_entity.url)



class MangoEntityListHandlerMixin(tornado.web.RequestHandler):
    @authenticated
    def post(self):
        new_entity = self._create()
        self.orm.add(new_entity)
        self.orm.commit()
        self.application.increment_cache()
        self.redirect_next(new_entity.url)


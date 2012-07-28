# -*- coding: utf-8 -*-

import os
import re
import time
import stat
import hashlib
import datetime
import mimetypes
import email.utils

from subprocess import Popen, PIPE
from tornado.web import StaticFileHandler, HTTPError

class GenerateHandler(StaticFileHandler):
    def get(self, path, include_body=True):
        path = self.parse_url_path(path)
        abspath = os.path.abspath(os.path.join(self.root, path))
        # os.path.abspath strips a trailing /
        # it needs to be temporarily added back for requests to root/
        if not (abspath + os.path.sep).startswith(self.root):
            raise HTTPError(403, "%s is not in root static directory", path)
        if os.path.isdir(abspath) and self.default_filename is not None:
            # need to look at the request.path here for when path is empty
            # but there is some prefix to the path that was already
            # trimmed by the routing
            if not self.request.path.endswith("/"):
                self.redirect(self.request.path + "/")
                return
            abspath = os.path.join(abspath, self.default_filename)

        #---
        if not os.path.exists(abspath):
            self.generate(path, abspath)
        #---

        if not os.path.exists(abspath):
            raise HTTPError(404)
        if not os.path.isfile(abspath):
            raise HTTPError(403, "%s is not a file", path)

        stat_result = os.stat(abspath)
        modified = datetime.datetime.fromtimestamp(stat_result[stat.ST_MTIME])

        self.set_header("Last-Modified", modified)

        mime_type, encoding = mimetypes.guess_type(abspath)
        if mime_type:
            self.set_header("Content-Type", mime_type)

        cache_time = self.get_cache_time(path, modified, mime_type)
        if cache_time > 0:
            self.set_header("Expires", datetime.datetime.utcnow() + \
                                       datetime.timedelta(seconds=cache_time))
            self.set_header("Cache-Control", "max-age=" + str(cache_time))
        else:
            self.set_header("Cache-Control", "public")

        self.set_extra_headers(path)

        # Check the If-Modified-Since, and don't send the result if the
        # content has not been modified
        ims_value = self.request.headers.get("If-Modified-Since")
        if ims_value is not None:
            date_tuple = email.utils.parsedate(ims_value)
            if_since = datetime.datetime.fromtimestamp(time.mktime(date_tuple))
            if if_since >= modified:
                self.set_status(304)
                return

        with open(abspath, "rb") as file:
            data = file.read()

            #---
            if not hasattr(self, "etag") or self.etag:
                hasher = hashlib.sha1()
                hasher.update(data)
                self.set_header("Etag", '"%s"' % hasher.hexdigest())
            #---

            if include_body:
                self.write(data)
            else:
                assert self.request.method == "HEAD"
                self.set_header("Content-Length", len(data))


class GenerateMarkerHandler(GenerateHandler):
    etag = False

    def compute_etag(self):
        return None

    def get_cache_time(self, path, modified, mime_type):
        return 60 * 60 * 24 * 30  # 30 days

    def render(self, template_name, **kwargs):
        mako_template = self.application.lookup.get_template(template_name)
        try:
            return mako_template.render(**kwargs)
        except:
            self.write(exceptions.html_error_template().render())

    def generate(self, path, abspath):
        if not path.endswith(".png"):
            raise HTTPError(404)

        if path.startswith("circle-"): 
            template = 'map-marker-circle.svg'
            path = path[:-4]
            form = path[7:].split("-")
        elif path.startswith("pin-"): 
            template = 'map-marker-pin.svg'
            path = path[:-4]
            form = path[4:].split("-")
        else:
            raise HTTPError(404)

        if len(form) != 2:
            raise HTTPError(404)
        fill, text = form
        if not re.match("[0-9a-zA-Z?]$", text):
            raise HTTPError(404)
        if not re.match("[0-9a-fA-F]{6}$", fill):
            raise HTTPError(404)
        svg = self.render(template,
                    text=text,
                    fill="#" + fill,
                    )

        cmd = ["convert", "-background", "none", "svg:-", abspath]
        process = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        (stdout, stderr) = process.communicate(svg)
        return

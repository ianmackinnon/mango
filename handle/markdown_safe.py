# -*- coding: utf-8 -*-

import re

import tornado.web

import bleach

import markdown

from bs4 import BeautifulSoup



md = markdown.Markdown()



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



class MarkdownSafeHandler(tornado.web.RequestHandler):
    def post(self):
        text = self.get_argument("text", "")
        autolinks = self.get_argument("convertLinks", None)

        html_safe = markdown_safe(text)

        if autolinks:
            html_safe = convert_links(html_safe)

        self.write(html_safe)
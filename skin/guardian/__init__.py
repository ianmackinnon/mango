# -*- coding: utf-8 -*-

from tornado.template import Loader


def load(**kwargs):
    loader = Loader("skin/guardian")

    def header(title=None):
        return loader.load(u"header.html").generate(
            static_url=kwargs.get("static_url", None),
            title=title or "",
            stylesheets=kwargs["stylesheets"],
            ).decode("utf-8")
    footer = loader.load(u"footer.html").generate()

    return {
        "header": header,
        "footer": footer,
        }
    


def scripts():
    None

def stylesheets():
    None

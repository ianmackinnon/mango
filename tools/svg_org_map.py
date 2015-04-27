#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import math
import logging
from optparse import OptionParser

from sqlalchemy import create_engine, func, or_, and_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from mako.template import Template
from mako.lookup import TemplateLookup

sys.path.append(".")

from model import connection_url_app, attach_search
from model import Org, Orgtag, Address
from model import org_orgtag, org_address
from model import log as log_model



log = logging.getLogger('merge')



def svg_map(orm, orgtag_name_short):
    uk_south = 49.87
    uk_north = 62.81
    uk_west = -6.38
    uk_east = 1.77

    query = orm.query(Org.name, Org.org_id) \
        .filter(
            orm.query(Orgtag) \
            .join(org_orgtag, org_orgtag.c.orgtag_id==Orgtag.orgtag_id) \
            .filter(org_orgtag.c.org_id==Org.org_id) \
            .filter(Orgtag.name_short==orgtag_name_short) \
            .exists()
        ) \
        .join(org_address, org_address.c.org_id==Org.org_id) \
        .join(Address, Address.address_id==org_address.c.address_id) \
        .add_columns(Address.address_id, Address.latitude, Address.longitude) \
        .filter(and_(
            Address.latitude != None,
            Address.longitude != None,
            Address.latitude >= uk_south,
            Address.latitude <= uk_north,
            Address.longitude >= uk_west,
            Address.longitude <= uk_east,
        ))
        
    lookup = TemplateLookup(
            directories=['tools'],
            input_encoding='utf-8',
            output_encoding='utf-8',
            default_filters=["unicode", "x"],
            )

    template = lookup.get_template("map.svg")

    log.info("%d results" % query.count())

    results = query.all()

    sys.stdout.write(template.render(**{
        "width": 512,
        "height": 512,
        "results": results,
        "math": math,
    }))



if __name__ == "__main__":
    log.addHandler(logging.StreamHandler())
    log_model.addHandler(logging.StreamHandler())

    usage = """%prog [tag]

Dump an SVG map of Public organisation addresses in the UK.

tag:   Tag to filter by."""

    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", dest="verbose",
                      help="Print verbose information for debugging.", default=0)
    parser.add_option("-q", "--quiet", action="count", dest="quiet",
                      help="Suppress warnings.", default=0)

    (options, args) = parser.parse_args()

    log_level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG,)[max(0, min(3, 1 + options.verbose - options.quiet))]

    log.setLevel(log_level)
    log_model.setLevel(log_level)

    connection_url = connection_url_app()
    engine = create_engine(connection_url)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    orm = Session()
    attach_search(engine, orm)


    if len(args) != 1:
        parser.print_usage()
        sys.exit(1)

    (orgtag_name_short, ) = args
    orgtag_name_short = unicode(orgtag_name_short)

    svg_map(orm, orgtag_name_short)

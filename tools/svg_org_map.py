#!/usr/bin/env python3

import sys
import math
import logging
import argparse

from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker

from mako.lookup import TemplateLookup

from model import mysql, CONF_PATH, attach_search
from model import Org, Orgtag, Address
from model import org_orgtag, org_address
from model import LOG as LOG_MODEL



LOG = logging.getLogger('merge')



def svg_map(orm, orgtag_name_short):
    uk_south = 49.87
    uk_north = 62.81
    uk_west = -6.38
    uk_east = 1.77

    query = orm.query(Org.name, Org.org_id) \
        .filter(
            orm.query(Orgtag) \
            .join(org_orgtag, org_orgtag.c.orgtag_id == Orgtag.orgtag_id) \
            .filter(org_orgtag.c.org_id == Org.org_id) \
            .filter(Orgtag.name_short == orgtag_name_short) \
            .exists()
        ) \
        .join(org_address, org_address.c.org_id == Org.org_id) \
        .join(Address, Address.address_id == org_address.c.address_id) \
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

    LOG.info("%d results", query.count())

    results = query.all()

    sys.stdout.write(template.render(**{
        "width": 512,
        "height": 512,
        "results": results,
        "math": math,
    }))



def main():
    LOG.addHandler(logging.StreamHandler())
    LOG_MODEL.addHandler(logging.StreamHandler())

    parser = argparse.ArgumentParser(
        description="Dump an SVG map of Public "
        "organisation addresses in the UK.")
    parser.add_argument(
        "--verbose", "-v",
        action="count", default=0,
        help="Print verbose information for debugging.")
    parser.add_argument(
        "--quiet", "-q",
        action="count", default=0,
        help="Suppress warnings.")

    parser.add_argument(
        "orgtag_name_short", metavar="TAG",
        help="Tag to filter by.")

    args = parser.parse_args()

    log_level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG,)[
        max(0, min(3, 1 + args.verbose - args.quiet))]

    LOG.setLevel(log_level)
    LOG_MODEL.setLevel(log_level)

    connection_url = mysql.connection_url_app(CONF_PATH)
    engine = create_engine(connection_url)
    session_factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False)
    orm = session_factory()
    attach_search(engine, orm)

    svg_map(orm, args.orgtag_name_short)



if __name__ == "__main__":
    main()

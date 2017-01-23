#!/usr/bin/env python3

import re
import sys
import logging
import argparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from model import mysql, CONF_PATH
from model import User, Address



LOG = logging.getLogger('sanitize_addresses')



def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {
        "yes": True,
        "ye": True,
        "y": True,
        "no": False,
        "n": False
    }
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "\
                             "(or 'y' or 'n').\n")


RE_CODE = re.compile(r"([^\W\d]\d|\d[^\W\d])", re.UNICODE)

def split_postcode(line):
    def is_code(text):
        return bool(RE_CODE.search(text))

    ret = [[]]
    last_code = None
    for part in line.split():
        this_code = is_code(part)
        if len(ret[0]) and this_code != last_code:
            ret.append([])
        ret[-1].append(part)
        last_code = this_code
    for p, part in enumerate(ret):
        ret[p] = " ".join(part)
    return ret

def suspicious_postcodes(orm):

    print("Suspicious postcodes")
    print()

    for address in orm.query(Address):
        parts = Address.parts(address.postal)
        for part in parts[len(parts) // 2:]:
            if RE_CODE.search(part):
                split = split_postcode(part)
                if len(split) > 1:
                    print()
                    print((address.url))
                    print((repr(part)))
                    print(split)





def sanitise_addresses(orm):
    user = orm.query(User).filter_by(user_id=-1).one()

    for address in orm.query(Address):
        a = address.postal
        b = address.sanitise_address(address.postal)
        if a != b:
            if "," not in b:
                address.postal = b
                print(b)
                print()
                orm.commit()
                continue
            b = address.sanitise_address(address.postal, False)
            print()
            print(a)
            print()
            print(b)
            print()
            if query_yes_no("replace?", default=None):
                address.postal = b
                address.moderation_user = user
                orm.commit()



def main():
    LOG.addHandler(logging.StreamHandler())

    parser = argparse.ArgumentParser(
        description="Sanitise addresses in the database.")
    parser.add_argument(
        "--verbose", "-v",
        action="count", default=0,
        help="Print verbose information for debugging.")
    parser.add_argument(
        "--quiet", "-q",
        action="count", default=0,
        help="Suppress warnings.")

    args = parser.parse_args()

    log_level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG,)[
        max(0, min(3, 1 + args.verbose - args.quiet))]
    LOG.setLevel(log_level)

    connection_url = mysql.connection_url_app(CONF_PATH)
    engine = create_engine(connection_url,)
    session_factory = sessionmaker(
        bind=engine, autocommit=False, autoflush=False)
    orm = session_factory()

#    sanitise_addresses(orm)

    suspicious_postcodes(orm)



if __name__ == "__main__":
    main()

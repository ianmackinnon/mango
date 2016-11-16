#!/usr/bin/env python3

import sys
import logging
import argparse
import configparser



LOG = logging.getLogger('conf')

ARG_DEFAULT = []



def get(ini_path, section, key, default=ARG_DEFAULT):
    # pylint: disable=dangerous-default-value
    # Using `[]` as default value in `get`

    config = configparser.ConfigParser()
    config.read(ini_path)

    try:
        value = config.get(section, key)
    except configparser.NoOptionError:
        if default == ARG_DEFAULT:
            raise
        return default

    return value



def main():
    LOG.addHandler(logging.StreamHandler())

    parser = argparse.ArgumentParser(
        description="Read configuration INI and print result.")

    parser.add_argument(
        "--verbose", "-v",
        action="count", default=0,
        help="Print verbose information for debugging.")
    parser.add_argument(
        "--quiet", "-q",
        action="count", default=0,
        help="Suppress warnings.")

    parser.add_argument(
        "ini_path", metavar="INI",
        help="Path to INI configuration file.")
    parser.add_argument(
        "section", metavar="SECTION",
        help="Configuration section.")
    parser.add_argument(
        "key", metavar="KEY",
        help="Configuration key.")

    args = parser.parse_args()

    level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[
        max(0, min(3, 1 + args.verbose - args.quiet))]
    LOG.setLevel(level)

    value = get(args.ini_path, args.section, args.key)
    sys.stdout.write(value + "\n")



if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import os
import sys
import getpass
import logging
import configparser
from hashlib import sha1
from optparse import OptionParser
from collections import namedtuple

import pymysql



LOG = logging.getLogger('mysql')

Options = namedtuple(
    "Options",
    [
        "database",
        "app_username",
        "app_password",
        "admin_username",
        "admin_password",
        ]
    )



def verify(string, section, name):
    if not re.match("[0-9A-Za-z_]*$", string):
        LOG.error("Error: '%s' is invalid.", string)
        LOG.error(
            "%s:%s should only contain digits, ASCII letters and underscores.",
            section, name)
        LOG.error(
            "Anything else can cause problems for some versions of MySQL.")
        sys.exit(1)
    if len(string) > 16:
        LOG.error(
            "Error: %s:%s may be a maximum of 16 characters.", section, name)
        LOG.error(
            "Anything else can cause problems for some versions of MySQL.")
        sys.exit(1)



def get_conf(path):
    if not os.path.isfile(path):
        LOG.error("%s: File not found", path)
        sys.exit(1)
    config = configparser.ConfigParser()
    config.read(path)

    database = config.get("mysql", "database")
    app_username = config.get("mysql-app", "username")
    app_password = config.get("mysql-app", "password")
    admin_username = config.get("mysql-admin", "username")
    admin_password = config.get("mysql-admin", "password")

    verify(database, "mysql", "database")
    verify(app_username, "mysql-app", "username")
    verify(app_password, "mysql-app", "password")
    verify(admin_username, "mysql-admin", "username")
    verify(admin_password, "mysql-admin", "password")

    options = Options(
        database,
        app_username,
        app_password,
        admin_username,
        admin_password,
        )

    return options



def connection_url_app(path):
    options = get_conf(path)
    return 'mysql+pymysql://%s:%s@localhost/%s?charset=utf8' % (
        options.app_username, options.app_password, options.database)



def connection_url_admin(path):
    options = get_conf(path)
    return 'mysql+pymysql://%s:%s@localhost/%s?charset=utf8' % (
        options.admin_username, options.admin_password, options.database)



def root_cursor():
    mysql_root_password = getpass.getpass("MySQL root password: ")

    try:
        db = pymysql.connect(
            host="localhost",
            user="root",
            passwd=mysql_root_password,
            )
    except pymysql.OperationalError as e:
        LOG.error("Could not connect with supplied root password.")
        print(e)
        sys.exit(1)

    cursor = db.cursor()

    return cursor



def admin_cursor(options):
    try:
        db = pymysql.connect(
            host="localhost",
            user=options.admin_username,
            passwd=options.admin_password,
            )
    except pymysql.OperationalError as e:
        LOG.error("Could not connect with admin credentials.")
        print(e)
        sys.exit(1)

    cursor = db.cursor()
    cursor.execute("use %s;" % options.database)

    return cursor



def app_cursor(options):
    try:
        db = pymysql.connect(
            host="localhost",
            user=options.app_username,
            passwd=options.app_password,
            )
    except pymysql.OperationalError as e:
        LOG.error("Could not connect with app credentials.")
        print(e)
        sys.exit(1)

    cursor = db.cursor()
    cursor.execute("use %s;" % options.database)

    return cursor



def drop_user(cursor, username):
    try:
        cursor.execute("drop user '%s'@'localhost';" % username)
        LOG.debug("User %s dropped.", username)
    except pymysql.OperationalError as e:
        if e.args[0] != 1396:
            raise e
        LOG.debug("User %s did not exist.", username)



def create_user(cursor, privileges, username, password):
    drop_user(cursor, username)
    cursor.execute("grant %s on * to '%s'@'localhost' identified by '%s';" % (privileges, username, password))
    # cursor.execute("grant reload on *.* to '%s'@'localhost';" % (username))
    LOG.debug("User %s created with permissions.", username)



def drop_database(cursor, name):
    try:
        cursor.execute("drop database %s;" % name)
        LOG.debug("Databse %s dropped.", name)
    except pymysql.OperationalError as e:
        if e.args[0] != 1008:
            raise e
        LOG.debug("Database %s did not exist.", name)



def mysql_drop(options):
    cursor = root_cursor()
    drop_user(cursor, options.admin_username)
    drop_user(cursor, options.app_username)
    drop_database(cursor, options.database)



# Checksum

def database_hash(conf_path):
    options = get_conf(conf_path)
    cursor = app_cursor(options)

    hasher = sha1()
    cursor.execute("show tables;")
    result = cursor.fetchall()
    for (table, ) in result:
        cursor.execute("checksum table %s extended;" % table)
        result2 = cursor.fetchone()
        if not result2:
            break
        (_table_path, checksum, ) = result2

        hasher.update(("%s=%s;" % (table, checksum)).encode())

    return hasher.hexdigest()



# Configuration



def mysql_generate_conf(options, account=None, dump=False):
    if account is None:
        account = "admin"
    assert account in ("admin", "app")

    if dump:
        sys.stdout.write( \
"""[client]
user=%s
password=%s
""" % (
    getattr(options, account + "_username"),
    getattr(options, account + "_password")
))
    else:
        sys.stdout.write( \
"""[client]
database=%s
user=%s
password=%s
""" % (
    options.database,
    getattr(options, account + "_username"),
    getattr(options, account + "_password")
))



def mysql_create(options):
    if mysql_test(options):
        LOG.info("Database and users already correctly set up. Nothing to do.")
        return

    cursor = root_cursor()

    try:
        cursor.execute("use %s;" % options.database)
    except pymysql.OperationalError as e:
        if e.args[0] != 1049:
            raise e

        LOG.debug("Database %s does not exist.", options.database)

        cursor.execute("""create database %s
DEFAULT CHARACTER SET = utf8
DEFAULT COLLATE = utf8_bin;""" % options.database)

        cursor.execute("use %s;" % options.database)

    LOG.debug("Database %s exists.", options.database)

    create_user(cursor, "all privileges",
                options.admin_username, options.admin_password)
    create_user(cursor, "select, insert, update, delete",
                options.app_username, options.app_password)



def mysql_test(options):
    """Returns True if successful, False if unsuccessful."""
    status = True

    try:
        pymysql.connect(
            host="localhost",
            user=options.app_username,
            passwd=options.app_password,
            db=options.database,
            )
    except pymysql.OperationalError:
        status = False
        LOG.debug("Could not connect as app user.")

    try:
        pymysql.connect(
            host="localhost",
            user=options.admin_username,
            passwd=options.admin_password,
            db=options.database,
            )
    except pymysql.OperationalError:
        status = False
        LOG.debug("Could not connect as admin user.")

    return status



def drop_database_tables(cursor):
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    while True:
        cursor.execute("show full tables where table_type = 'VIEW';")
        result = cursor.fetchone()
        if not result:
            break
        (name, _type) = result
        cursor.execute("drop view %s;" % name)
        LOG.debug("Dropped view %s.", name)
    while True:
        cursor.execute("show full tables where table_type = 'BASE TABLE';")
        result = cursor.fetchone()
        if not result:
            break
        (name, _type) = result
        cursor.execute("drop table %s;" % name)
        LOG.debug("Dropped table %s.", name)
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")



def drop_database_triggers(cursor, database):
    LOG.warning("DROP ALL TRIGGERS")
    cursor.execute("""select trigger_name
from information_schema.triggers
where trigger_schema = '%s';""", database)
    result = cursor.fetchall()
    for (trigger, ) in result:
        cursor.execute("drop trigger %s;" % trigger)
        LOG.debug("Dropped trigger %s.", trigger)



def mysql_empty(options):
    cursor = admin_cursor(options)
    drop_database_tables(cursor)



def mysql_drop_triggers(options):
    cursor = admin_cursor(options)
    drop_database_triggers(cursor, options.database)



def mysql_source(options, source):
    cursor = admin_cursor(options)
    sql = open(source).read()
    cursor.execute(sql)



def main2(
        conf_path,
        key=None, purge=False, empty=False, drop_triggers=False,
        account=None, generate=False, generate_dump=False, test=False,
        source=None):
    # pylint: disable=too-many-return-statements

    options = get_conf(conf_path)

    if key:
        print(getattr(options, key))
        return

    if source:
        return mysql_source(options, source)

    if purge:
        return mysql_drop(options)

    if empty:
        return mysql_empty(options)

    if drop_triggers:
        return mysql_drop_triggers(options)

    if generate or generate_dump:
        return mysql_generate_conf(
            options, account=account, dump=generate_dump)

    if test:
        if mysql_test(options):
            pass
        else:
            LOG.error("Database and users not correctly set up.")
            sys.exit(1)

    return mysql_create(options)



def main():
    LOG.addHandler(logging.StreamHandler())

    usage = """%prog

Create MySQL database and users.
"""

    parser = OptionParser(usage=usage)
    parser.add_option(
        "-v", "--verbose", dest="verbose",
        action="count", default=0,
        help="Print verbose information for debugging.")
    parser.add_option(
        "-q", "--quiet", dest="quiet",
        action="count", default=0,
        help="Suppress warnings.")
    parser.add_option(
        "-k", "--key", action="store", dest="key",
        help="Print a configuration key")
    parser.add_option(
        "-t", "--test", action="store_true", dest="test",
        help="Check the database and users are correctly setup.",
        default=False)
    parser.add_option(
        "-p", "--purge", action="store_true", dest="purge",
        help="Delete database and users.", default=False)
    parser.add_option(
        "-e", "--empty", action="store_true", dest="empty",
        help="Empty the database.", default=False)
    parser.add_option(
        "-r", "--drop-triggers", action="store_true", dest="drop_triggers",
        help="Drop all triggers.", default=False)
    parser.add_option(
        "-a", "--account", action="store", dest="account",
        help="Specify account for conf files..", default=None)
    parser.add_option(
        "-g", "--generate", action="store_true", dest="generate",
        help="Generate MySQL conf to stdout.", default=False)
    parser.add_option(
        "-G", "--generate-dump", action="store_true", dest="generate_dump",
        help="Generate MySQL dump conf to stdout.", default=False)
    parser.add_option(
        "-s", "--source", action="store", dest="source",
        help="Source SQL.")

    (options, args) = parser.parse_args()

    if not len(args) == 1:
        parser.print_usage()
        sys.exit(1)

    (conf_path, ) = args

    log_level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG,)[
        max(0, min(3, 1 + options.verbose - options.quiet))]
    LOG.setLevel(log_level)

    main2(
        conf_path,
        key=options.key,
        purge=options.purge,
        empty=options.empty,
        drop_triggers=options.drop_triggers,
        account=options.account,
        generate=options.generate,
        generate_dump=options.generate_dump,
        test=options.test,
        source=options.source
        )


if __name__ == "__main__":
    main()

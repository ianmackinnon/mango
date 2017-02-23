#!/usr/bin/env python3

import re
import os
import sys
import getpass
import logging
import argparse
import configparser
from hashlib import sha1
from collections import namedtuple

import pymysql



LOG = logging.getLogger('mysql')

Options = namedtuple(
    "Options",
    [
        "database",
        "app_username",
        "app_password",
        "app_privileges",
        "admin_username",
        "admin_password",
        "admin_privileges",
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



def split(text):
    values = []
    for value in text.split(","):
        value = value.strip()
        if value:
            values.append(value)
    return values



def load_conf(path):
    # pylint: disable=protected-access
    # Storing config path in protected variable

    if not os.path.isfile(path):
        LOG.error("%s: File not found", path)
        sys.exit(1)
    config = configparser.ConfigParser()
    config.read(path)
    config._load_path = path
    return config



def get_conf(path):
    config = load_conf(path)

    names = load_database_names(config)

    database = names["default"]

    app_username = config.get("mysql-app", "username")
    app_password = config.get("mysql-app", "password")
    app_privileges = config["mysql-app"].get("privileges", None)
    if app_privileges:
        app_privileges = replace_database_names(names, app_privileges)
        app_privileges = split(app_privileges)

    admin_username = config.get("mysql-admin", "username")
    admin_password = config.get("mysql-admin", "password")
    admin_privileges = config["mysql-admin"].get("privileges", None)
    if admin_privileges:
        admin_privileges = replace_database_names(names, admin_privileges)
        admin_privileges = split(admin_privileges)

    verify(database, "mysql", "default")
    verify(app_username, "mysql-app", "username")
    verify(app_password, "mysql-app", "password")
    verify(admin_username, "mysql-admin", "username")
    verify(admin_password, "mysql-admin", "password")

    options = Options(
        database,
        app_username,
        app_password,
        app_privileges,
        admin_username,
        admin_password,
        admin_privileges,
    )

    return options



def replace_database_names(names, text):
    """
    Accepts either a "format" style string with database names
    in curly braces, or a solitary database name.
    """
    if re.compile(r"^[a-z-]+$").match(text):
        text = "{%s}" % text
    return text.format(**names)



def load_database_names(conf):
    """
    Accepts string or config instance.
    """
    # pylint: disable=protected-access
    # Storing file path in config object.

    if isinstance(conf, str):
        config = load_conf(conf)
    else:
        assert isinstance(conf, configparser.ConfigParser)
        config = conf

    names = {}
    for key in config["mysql"]:
        if key == "default":
            continue
        names[key] = config.get("mysql", key)

    default = config["mysql"].get("default")
    if default:
        names["default"] = replace_database_names(names, default)

    return names



def mysql_connection_url(username, password, database,
                         host=None, port=None):
    login = "%s:%s@" % (username, password)

    if host is None:
        host = "localhost"
    if host == "localhost":
        host = "127.0.0.1"  # Prevents MySQL from using a socket
    if port is not None:
        host += ":%d" % port

    path = "/%s?charset=utf8" % database

    return "mysql+pymysql://%s%s%s" % (login, host, path)



def connection_url_admin(conf_path, host=None, port=None):
    options = get_conf(conf_path)
    return mysql_connection_url(
        options.admin_username, options.admin_password, options.database,
        host=host, port=port)



def connection_url_app(conf_path, host=None, port=None):
    options = get_conf(conf_path)
    return mysql_connection_url(
        options.app_username, options.app_password, options.database,
        host=host, port=port)



def root_cursor():
    mysql_root_password = getpass.getpass("MySQL root password: ")

    try:
        db = pymysql.connect(
            host="localhost",
            user="root",
            passwd=mysql_root_password,
            )
    except pymysql.err.InternalError as e:
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
    except pymysql.err.InternalError as e:
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
    except pymysql.err.InternalError as e:
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
    except pymysql.err.InternalError as e:
        if e.args[0] != 1396:
            raise e
        LOG.debug("User %s did not exist.", username)



def create_user(cursor, username, password, privileges):
    drop_user(cursor, username)
    user = "'%s'@'localhost'" % username
    cursor.execute("create user %s identified by '%s';" % (user, password))
    for privilege in privileges:
        cursor.execute("grant %s.* to %s;" % (privilege, user))
    LOG.debug("User %s created with permissions.", username)



def drop_database(cursor, name):
    try:
        cursor.execute("drop database %s;" % name)
        LOG.debug("Databse %s dropped.", name)
    except pymysql.err.InternalError as e:
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
    except pymysql.err.InternalError as e:
        if e.args[0] != 1049:
            raise e

        LOG.debug("Database %s does not exist.", options.database)

        cursor.execute("""create database %s
DEFAULT CHARACTER SET = utf8
DEFAULT COLLATE = utf8_bin;""" % options.database)

        cursor.execute("use %s;" % options.database)

    LOG.debug("Database %s exists.", options.database)

    create_user(cursor, options.admin_username, options.admin_password, [
        "all privileges on %s" % options.database,
        # "reload on %s" % options.database,
    ] + options.admin_privileges)
    create_user(cursor, options.app_username, options.app_password, [
        "select, insert, update, delete on %s" % options.database,
    ] + options.app_privileges)



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
    except pymysql.err.OperationalError:
        status = False
        LOG.debug("Could not connect as app user.")

    try:
        pymysql.connect(
            host="localhost",
            user=options.admin_username,
            passwd=options.admin_password,
            db=options.database,
            )
    except pymysql.err.OperationalError:
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



def main_functions(
        conf_path,
        key=None, purge=False, empty=False, drop_triggers=False,
        account=None, generate=False, generate_dump=False, test=False,
        source=None):
    # pylint: disable=too-many-return-statements

    options = get_conf(conf_path)

    if key:
        print((getattr(options, key)))
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

    parser = argparse.ArgumentParser(
        description="Create MySQL database and users.")
    parser.add_argument(
        "--verbose", "-v",
        action="count", default=0,
        help="Print verbose information for debugging.")
    parser.add_argument(
        "--quiet", "-q",
        action="count", default=0,
        help="Suppress warnings.")

    parser.add_argument(
        "--key", "-k",
        action="store",
        help="Print a configuration key")
    parser.add_argument(
        "--test", "-t",
        action="store_true", default=False,
        help="Check the database and users are correctly setup.")
    parser.add_argument(
        "--purge", "-p",
        action="store_true", default=False,
        help="Delete database and users.")
    parser.add_argument(
        "--empty", "-e",
        action="store_true", default=False,
        help="Empty the database.")
    parser.add_argument(
        "--drop-triggers", "-r",
        action="store_true", default=False,
        help="Drop all triggers.")
    parser.add_argument(
        "--account", "-a",
        action="store",
        help="Specify account for conf files..")
    parser.add_argument(
        "--generate", "-g",
        action="store_true", default=False,
        help="Generate MySQL conf to stdout.")
    parser.add_argument(
        "--generate-dump", "-G",
        action="store_true", default=False,
        help="Generate MySQL dump conf to stdout.")
    parser.add_argument(
        "--source", "-s",
        action="store", dest="source",
        help="Source SQL.")

    parser.add_argument(
        "conf_path", metavar="CONF",
        help="Path to configuration file.")

    args = parser.parse_args()

    level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[
        max(0, min(3, 1 + args.verbose - args.quiet))]
    LOG.setLevel(level)

    main_functions(
        args.conf_path,
        key=args.key,
        purge=args.purge,
        empty=args.empty,
        drop_triggers=args.drop_triggers,
        account=args.account,
        generate=args.generate,
        generate_dump=args.generate_dump,
        test=args.test,
        source=args.source
    )


if __name__ == "__main__":
    main()

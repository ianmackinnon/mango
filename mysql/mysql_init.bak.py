# 2015.09.07 17:48:13 CEST
#Embedded file name: /home/ianmackinnon/jobs/mango/mysql/mysql_init.py
import re
import sys
import logging
import ConfigParser
from optparse import OptionParser
log = logging.getLogger('mysql_init')
error = 'A configuration file called .mango.conf must be present and readable with the following format:\n\n[mysql]\ndatabase: mango\n\n[mysql-app]\nusername: mango-app\npassword: ????????\n\n[mysql-admin]\nusername: mango-admin\npassword: ????????\n\nCopy the example from mango.example.conf to .mango.conf and set the variables as you wish.\n\nThen change permissions to make it secret. Eg. chmod 600 .mango.conf.\n\n'

def verify(string, section, name):
    if not re.match('[0-9A-Za-z_]*$', string):
        log.error('Error: %s:%s should only contain digits, ASCII letters and underscores. Anything else can cause problems for MySQL.' % (section, name))
        sys.exit(1)
    if len(string) > 16:
        log.error('Error: %s:%s may be a maximum of 16 characters. Anything else can cause problems for MySQL.' % (section, name))
        sys.exit(1)


def get_conf(conf):
    config = ConfigParser.ConfigParser()
    config.read(conf)
    try:
        database = config.get('mysql', 'database')
        app_username = config.get('mysql-app', 'username')
        app_password = config.get('mysql-app', 'password')
        admin_username = config.get('mysql-admin', 'username')
        admin_password = config.get('mysql-admin', 'password')
    except ConfigParser.NoSectionError as e:
        log.error(error)
        sys.exit(1)
    except ConfigParser.NoOptionError as e:
        log.error(error)
        sys.exit(1)

    verify(database, 'mysql', 'database')
    verify(app_username, 'mysql-app', 'username')
    verify(app_password, 'mysql-app', 'password')
    verify(admin_username, 'mysql-admin', 'username')
    verify(admin_password, 'mysql-admin', 'password')
    return (database,
     app_username,
     app_password,
     admin_username,
     admin_password)


def mysql_init(conf, clean = False, datum = None):
    database, app_username, app_password, admin_username, admin_password = get_conf(conf)
    if datum:
        print database
        return
    if clean:
        print "\ndrop user '%s'@'localhost';\ndrop user '%s'@'localhost';\ndrop database %s;\n" % (admin_username, app_username, database)
    else:
        print "\ncreate database %s\n  DEFAULT CHARACTER SET = utf8\n  DEFAULT COLLATE = utf8_bin;\nuse %s;\ncreate user '%s'@'localhost' identified by '%s';\ncreate user '%s'@'localhost' identified by '%s';\ngrant all privileges on * to '%s'@'localhost';\ngrant select, insert, update, delete on * to '%s'@'localhost';\n" % (database,
         database,
         admin_username,
         admin_password,
         app_username,
         app_password,
         admin_username,
         app_username)


if __name__ == '__main__':
    log.addHandler(logging.StreamHandler())
    usage = '%prog'
    parser = OptionParser(usage=usage)
    parser.add_option('-v', '--verbose', action='count', dest='verbose', help='Print verbose information for debugging.', default=0)
    parser.add_option('-q', '--quiet', action='count', dest='quiet', help='Suppress warnings.', default=0)
    parser.add_option('-x', '--clean', action='store_true', dest='clean', help='Delete database and users.', default=False)
    parser.add_option('-d', '--datum', action='store', dest='datum', help='Print a particular datum.', default=False)
    parser.add_option('-c', '--configuration', action='store', dest='configuration', help='.conf file.', default='.mango.conf')
    options, args = parser.parse_args()
    if not len(args) == 0:
        parser.print_usage()
        sys.exit(1)
    verbosity = max(0, min(3, 1 + options.verbose - options.quiet))
    log.setLevel((logging.ERROR,
     logging.WARNING,
     logging.INFO,
     logging.DEBUG)[verbosity])
    mysql_init(conf=options.configuration, clean=options.clean, datum=options.datum)
+++ okay decompyling mysql_init.pyc 
# decompiled 1 files: 1 okay, 0 failed, 0 verify failed
# 2015.09.07 17:48:13 CEST

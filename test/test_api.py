#!/usr/bin/env python3

# pylint: disable=wrong-import-position,import-error
# Allow appending to import path before import
# Must also specify `PYTHONPATH` when invoking Pylint.

import os
import sys
import time
import logging
import argparse
import unittest
from urllib.parse import urlencode
from subprocess import Popen, PIPE
from threading import Thread
from queue import Queue, Empty

import httplib2

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(1, os.path.join(sys.path[0], '..'))

from model import connection_url_app



LOG = logging.getLogger('test_api')

HOST = "http://localhost:8802"

ORG_ID = 1
ORGTAG_ID = 1
EVENT_ID = 1
EVENTTAG_ID = 1
NOTE_ID = 1
ADDRESS_ID = 1
CONTACT_ID = 1

USER_MOD_ID = 1
USER_LOK_ID = 2
USER_REG_ID = 3

TEST_MARKDOWN_LOREM = "Lorem\n\nipsum"
TEST_SOURCE = "source"

# http://stackoverflow.com/a/4896288/201665
ON_POSIX = 'posix' in sys.builtin_module_names



class MangoApiMixin(object):

    @classmethod
    def set_up_class(cls):
        cls.longMessage = True

        connection_url = connection_url_app()
        engine = create_engine(connection_url,)
        cls.Session = sessionmaker(bind=engine, autocommit=False)

        cls.http = httplib2.Http(cache=None)
        cls.http.follow_redirects = False

    def flush_mango_log(self):
        try:
            line = self.queue_out.get_nowait()
        except Empty:
            pass
        else:
            self.mango_log_out.append(line)
        try:
            line = self.queue_err.get_nowait()
        except Empty:
            pass
        else:
            self.mango_log_err.append(line)

    def start_mango(self):
        def enqueue_output(stream, queue, _name):
            for line in iter(stream.readline, ''):
                queue.put(line)

        self.process = Popen(
            "./mango.py", stdout=PIPE, stderr=PIPE, close_fds=ON_POSIX)
        self.queue_out = Queue()
        self.queue_err = Queue()
        thread_out = Thread(
            target=enqueue_output,
            args=(self.process.stdout, self.queue_out, "out")
            )
        thread_err = Thread(
            target=enqueue_output,
            args=(self.process.stderr, self.queue_err, "err")
            )
        thread_out.daemon = True # thread dies with the program
        thread_err.daemon = True # thread dies with the program
        thread_out.start()
        thread_err.start()

        self.mango_log_err = []
        self.mango_log_out = []

        wait = 0.5
        waited = 0
        timeout = 10
        while True:
            self.flush_mango_log()
            if self.mango_log_err or self.mango_log_out:
                break
            time.sleep(wait)
            waited += wait
            if wait > timeout:
                print("Waited long enough. Giving up.")
                sys.exit(1)

    def set_up(self):
        process = Popen('ps -ef | grep "python ./mang[o].py"',
                        shell=True, stdout=PIPE, stderr=PIPE)
        out, err = process.communicate()
        self.assertFalse(
            out, msg="An instance of Mango is already running:\n%s" % out)

        process = Popen("make mysql-test", shell=True,
                        stdout=PIPE, stderr=PIPE)
        out, err = process.communicate()
        self.assertEqual(process.wait(), 0, msg=err)

        self.orm = self.Session()
        self.start_mango()

        self.cookie = None

    def tear_down(self):
        self.process.kill()
        self.orm.close()

    def login(self, user_id):
        url = HOST + "/auth/login/local?user=%d" % user_id
        response, _content = self.http.request(url)
        self.cookie = response["set-cookie"]



class TestUserSubmission(unittest.TestCase, MangoApiMixin):

    @classmethod
    def setUpClass(cls):
        MangoApiMixin.setUpClass()

    def setUp(self):
        MangoApiMixin.setUp(self)

    def tearDown(self):
        MangoApiMixin.tearDown(self)

    def test_create_contact(self):
        self.login(USER_REG_ID)
        url = HOST + "/organisation/%d/contact" % ORG_ID
        method = "POST"
        data = {
            "medium": "Email",
            "text": "new@example.com",
            "description": TEST_MARKDOWN_LOREM,
            "source": TEST_SOURCE,
            }
        headers = {}
        if self.cookie:
            headers["Cookie"] = self.cookie
        response, content = self.http.request(
            url, method, urlencode(data), headers=headers)
        print(response)
        print(content)
        time.sleep(3)
        self.flush_mango_log()
        print((self.mango_log_err))
        print((self.mango_log_out))





def main():
    LOG.addHandler(logging.StreamHandler())

    parser = argparse.ArgumentParser(
        description="Test web app API.")
    parser.add_argument(
        "--verbose", "-v",
        action="count", default=0,
        help="Print verbose information for debugging.")
    parser.add_argument(
        "--quiet", "-q",
        action="count", default=0,
        help="Suppress warnings.")

    args = parser.parse_args()

    level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[
        max(0, min(3, 1 + args.verbose - args.quiet))]
    LOG.setLevel(level)

    unittest.main()



if __name__ == "__main__":
    main()

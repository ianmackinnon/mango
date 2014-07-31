#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append(".")

import os
import json
import time
import httplib2
import unittest
from urllib import urlencode
from subprocess import Popen, PIPE
from threading import Thread
from Queue import Queue, Empty

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from model import connection_url_app, attach_search
from model import Org, Contact


host = "http://localhost:8802"

org_id = 1
orgtag_id = 1
event_id = 1
eventtag_id = 1
note_id = 1
address_id = 1
contact_id = 1

user_mod_id = 1
user_lok_id = 2
user_reg_id = 3

test_markdown_lorem = "Lorem\n\nipsum"
test_source = "source"



class MangoApi(object):
    @classmethod
    def setUpClass(cls):
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
        # http://stackoverflow.com/a/4896288/201665
        ON_POSIX = 'posix' in sys.builtin_module_names
        def enqueue_output(stream, queue, name):
            for line in iter(stream.readline, ''):
                queue.put(line)

        self.process = Popen("./mango.py", stdout=PIPE, stderr=PIPE, close_fds=ON_POSIX)
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
                print "Waited long enough. Giving up."
                sys.exit(1)

    def setUp(self):
        process = Popen('ps -ef | grep "python ./mang[o].py"',
                        shell=True, stdout=PIPE, stderr=PIPE)
        out, err = process.communicate()
        self.assertFalse(
            out, msg=u"An instance of Mango is already running:\n%s" % out)

        process = Popen("make mysql-test", shell=True,
                        stdout=PIPE, stderr=PIPE)
        out, err = process.communicate()
        self.assertEqual(process.wait(), 0, msg=err)

        self.orm = self.Session()
        self.start_mango()

        self.cookie = None

    def tearDown(self):
        self.process.kill()
        self.orm.close()

    def login(self, user_id):
        url = host + u"/auth/login/local?user=%d" % user_id
        response, content = self.http.request(url)
        response, content = self.http.request(url)
        self.cookie = response["set-cookie"]



class TestUserSubmission(unittest.TestCase, MangoApi):

    @classmethod
    def setUpClass(cls):
        MangoApi.setUpClass()

    def setUp(self):
        MangoApi.setUp(self)

    def tearDown(self):
        MangoApi.tearDown(self)

    def test_create_contact(self):
        self.login(user_reg_id)
        url = host + u"/organisation/%d/contact" % org_id
        method = "POST"
        data = {
            "medium": "Email",
            "text": "new@example.com",
            "description": test_markdown_lorem,
            "source": test_source,
            }
        headers = {}
        if self.cookie:
            headers["Cookie"] = self.cookie
        response, content = self.http.request(url, method, urlencode(data), headers=headers)
        print response
        print content
        time.sleep(3)
        self.flush_mango_log()
        print self.mango_log_err
        print self.mango_log_out
        




if __name__ == "__main__":
    unittest.main()
                

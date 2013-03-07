#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

sys.path.append(os.getcwd())

import sys
import json
import codecs
import unittest

from model import short_name



class TestTagShortName(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        
        path = os.path.join(
            os.path.dirname(
                os.path.abspath(__file__)
                ),
            u"data_rename.json"
            )
        with codecs.open(path, "r", "utf-8") as json_data:
            cls.known = json.load(json_data)
        
    def test_html_private(self):
        for name, known_result in self.known:
            result = short_name(name)
            print name, known_result, result
            self.assertIsInstance(result, unicode)
            self.assertEqual(known_result, result)



if __name__ == "__main__":
    unittest.main()
                

#!/usr/bin/env python3

# pylint: disable=wrong-import-position,import-error
# Allow appending to import path before import
# Must also specify `PYTHONPATH` when invoking Pylint.

import os
import sys
import json
import logging
import argparse
import unittest

sys.path.insert(1, os.path.join(sys.path[0], '..'))

from handle.base import url_rewrite_static



LOG = logging.getLogger('test_url_rewrite')



class TestClass(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.longMessage = True

        data_path = os.path.join(sys.path[0], "dataUrlRewrite.json")

        with open(data_path) as fp:
            cls.known_values = json.load(fp)

    def test_known_values(self):
        for inputs, result_known in self.known_values:
            uri = inputs.pop("uri")
            if "next" in inputs:
                inputs["next_"] = inputs["next"]
                del inputs["next"]
            result_found = url_rewrite_static(uri, **inputs)
            self.assertEqual(result_found, result_known)



def main():
    LOG.addHandler(logging.StreamHandler())

    parser = argparse.ArgumentParser(
        description="Test that URL rewrite function produces desired results.")
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

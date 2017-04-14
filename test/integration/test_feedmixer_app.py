from falcon import testing
import feedmixer_app
from urllib.parse import unquote
import json
import feedparser
import os

TESTDB = 'fm_test_cache'


def build_qs(feeds=[], n=-1):
    feeds = ["f={}".format(f) for f in feeds]
    qs = '&'.join(feeds)
    qs += "&n={}".format(n)
    return qs


class FMTestCase(testing.TestCase):
    def setUp(self):
        super().setUp()
        self.app = feedmixer_app.wsgi_app(db_path=TESTDB)

    def tearDown(self):
        os.remove(TESTDB)

    def get_results_errors(self, path='/', qs=''):
        """
        Returns a tuple: (results, error_dictionary)
        """
        result = self.simulate_get(path, query_string=qs)

        # get errors
        json_err = None
        error_head = result.headers.get('x-fm-errors')
        if error_head:
            json_err = json.loads(unquote(error_head))

        return (result, json_err)


class TestAtom(FMTestCase):
    def test_single_good_all(self):
        qs = build_qs(feeds=['http://mretc.net/shaarli/?do=atom'], n=-1)
        result, errors = self.get_results_errors(path='/atom', qs=qs)
        atom = feedparser.parse(result.text)
        self.assertFalse(atom.bozo)
        self.assertTrue(len(atom.entries) > 5)

    def test_good_and_404(self):
        qs = build_qs(feeds=['http://mretc.net/shaarli/?do=atom',
                             'http://mretc.net/thisdoesnotexist'], n=1)
        result, errors = self.get_results_errors(path='/atom', qs=qs)
        atom = feedparser.parse(result.text)
        self.assertFalse(atom.bozo)
        self.assertTrue(len(atom.entries) == 1)
        self.assertIsNotNone(errors)
        self.assertIn('404', errors['http://mretc.net/thisdoesnotexist'])

    def test_mix(self):
        qs = build_qs(feeds=['http://mretc.net/shaarli/?do=atom',
                             'https://news.ycombinator.com/rss'], n=2)
        result, errors = self.get_results_errors(path='/atom', qs=qs)
        atom = feedparser.parse(result.text)
        self.assertFalse(atom.bozo)
        self.assertTrue(len(atom.entries) == 4)
        self.assertIsNone(errors)

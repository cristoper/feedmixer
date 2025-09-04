import json
from urllib.parse import unquote

import feedparser
from falcon import testing

import feedmixer_api


def build_qs(feeds=[], n=-1, full=False):
    feeds = ["f={}".format(f) for f in feeds]
    qs = "&".join(feeds)
    qs += "&n={}".format(n)
    if full:
        qs += "&full=y"
    return qs


class FMTestCase(testing.TestCase):
    def setUp(self):
        super().setUp()
        self.app = feedmixer_api.wsgi_app()

    def get_results_errors(self, path="/", qs=""):
        """
        Returns a tuple: (results, error_dictionary)
        """
        result = self.simulate_get(path, query_string=qs)

        # get errors
        json_err = None
        error_head = result.headers.get("x-fm-errors")
        if error_head:
            json_err = json.loads(unquote(error_head))

        return (result, json_err)


class TestAPI(FMTestCase):
    def test_no_feeds_error(self):
        """
        Test that an error header is returned if no feeds are given.
        """
        qs = build_qs(feeds=[])
        result, errors = self.get_results_errors(path="/atom", qs=qs)
        self.assertIsNotNone(errors)


class TestAtom(FMTestCase):
    def test_single_good_all(self):
        qs = build_qs(feeds=["https://americancynic.net/shaarli/?do=atom"], n=-1)
        result, errors = self.get_results_errors(path="/atom", qs=qs)
        atom = feedparser.parse(result.text)
        self.assertFalse(atom.bozo)
        self.assertTrue(len(atom.entries) > 5)

    def test_good_and_404(self):
        qs = build_qs(
            feeds=[
                "https://americancynic.net/shaarli/?do=atom",
                "https://americancynic.net/thisdoesnotexist",
            ],
            n=1,
        )
        result, errors = self.get_results_errors(path="/atom", qs=qs)
        atom = feedparser.parse(result.text)
        self.assertFalse(atom.bozo)
        self.assertTrue(len(atom.entries) == 1)
        self.assertIsNotNone(errors)
        self.assertIn("404", errors["https://americancynic.net/thisdoesnotexist"])

    def test_mix(self):
        qs = build_qs(
            feeds=[
                "https://americancynic.net/shaarli/?do=atom",
                "https://news.ycombinator.com/rss",
            ],
            n=2,
        )
        result, errors = self.get_results_errors(path="/atom", qs=qs)
        atom = feedparser.parse(result.text)
        self.assertFalse(atom.bozo)
        self.assertTrue(len(atom.entries) == 4)
        self.assertIsNone(errors)

    def test_prefer_summary(self):
        qs = build_qs(feeds=["http://catswhisker.xyz/atom.xml"], n=1)
        qs_full = build_qs(feeds=["http://catswhisker.xyz/atom.xml"], n=1, full=True)
        result, _ = self.get_results_errors(path="/atom", qs=qs)
        result_full, _ = self.get_results_errors(path="/atom", qs=qs_full)
        atom = feedparser.parse(result.text)
        atom_full = feedparser.parse(result_full.text)

        e = atom.entries[0]

        # Find entry in e_full with same unique_id to ensure we are comparing
        # the same entry from each fetch.
        eid = e.get("id")
        for entry in atom_full.entries:
            if entry.get("id") == eid:
                e_full = entry
                break

        e_desc = e.get("description")
        e_full_desc = e_full.get("description")
        self.assertEqual(eid, e_full.get("id"))
        self.assertTrue(len(e_desc) < len(e_full_desc))

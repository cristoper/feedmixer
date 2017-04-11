import unittest
from unittest.mock import MagicMock, call
from feedcache import FeedCache
from urllib.error import URLError
import feedparser
from feedmixer import FeedMixer

ATOM_PATH = 'test/test_atom.xhtml'
RSS_PATH = 'test/test_rss2.xhtml'


with open(ATOM_PATH, 'r') as f:
    feed = ''.join(f.readlines())
    TEST_ATOM = feedparser.parse(feed)

with open(RSS_PATH, 'r') as f:
    feed = ''.join(f.readlines())
    TEST_RSS = feedparser.parse(feed)


def build_mock_cacher():
    def mock_fetch(url):
        """Mimics the FeedCache.fetch() method"""
        if url == "atom":
            return TEST_ATOM
        elif url == "fetcherror":
            raise FeedCache.FetchError("fetch error")
        elif url == "parseerror":
            raise FeedCache.ParseError("parse error")
        elif url == "urlerror":
            raise URLError("URL error")
        else:
            # url == "rss"
            return TEST_RSS
    return MagicMock(side_effect=mock_fetch)

# __init__(self, title: str='Title', link: str='', desc: str='', feeds:
#                 List[Optional[str]]=[], num_keep: int=3, max_threads: int=5,
#                 max_feeds: int=100, cache_path: str='fmcache.db', cacher:
#                 Optional[Callable[[str], FeedParserDict]]=None) -> None:


class TestMixedEntries(unittest.TestCase):
    def test_empty(self):
        """
        Test with an empty `feeds` list.
        """
        mc = MagicMock()
        fm = FeedMixer(feeds=[], cacher=mc)
        me = fm.mixed_entries
        mc.assert_not_called()
        self.assertEqual(me, [])

    def test_single_good(self):
        """
        Test with a single good URL.
        """
        mc = build_mock_cacher()
        fm = FeedMixer(feeds=['atom'], cacher=mc, num_keep=2)
        me = fm.mixed_entries
        mc.assert_called_once_with('atom')
        self.assertEqual(len(me), 2)

    def test_multi_good(self):
        """
        Test with multiple good URLs.
        """
        mc = build_mock_cacher()
        fm = FeedMixer(feeds=['atom', 'rss', 'atom'], cacher=mc, num_keep=2)
        me = fm.mixed_entries
        mc.assert_has_calls([call('atom'), call('rss'), call('atom')],
                            any_order=True)
        self.assertEqual(len(me), 6)

    def test_single_exception(self):
        """
        Test with a single URL which throws an exception.
        """
        mc = build_mock_cacher()
        fm = FeedMixer(feeds=['fetcherror'], cacher=mc, num_keep=2)
        me = fm.mixed_entries
        self.assertEqual(len(me), 0)
        self.assertIsInstance(fm.error_urls['fetcherror'], FeedCache.FetchError)

    def test_multi_exception(self):
        """
        Test with several URLs which all throw exceptions.
        """
        mc = build_mock_cacher()
        fm = FeedMixer(feeds=['fetcherror', 'parseerror', 'urlerror'],
                       cacher=mc, num_keep=2)
        me = fm.mixed_entries
        mc.assert_has_calls([call('fetcherror'), call('parseerror'),
                             call('urlerror')], any_order=True)
        self.assertEqual(len(me), 0)
        self.assertIsInstance(fm.error_urls['fetcherror'], FeedCache.FetchError)
        self.assertIsInstance(fm.error_urls['parseerror'], FeedCache.ParseError)
        self.assertIsInstance(fm.error_urls['urlerror'], URLError)

    def test_multi_mixed(self):
        """
        Test with several URLs, some of which succeed and some of which throw
        exceptions.
        """
        mc = build_mock_cacher()
        fm = FeedMixer(feeds=['fetcherror', 'atom', 'rss', 'parseerror'],
                       cacher=mc, num_keep=2)
        me = fm.mixed_entries
        mc.assert_has_calls([call('fetcherror'), call('atom'), call('rss'),
                             call('parseerror')], any_order=True)
        self.assertEqual(len(me), 4)
        self.assertEqual(len(fm.error_urls.keys()), 2)
        self.assertIsInstance(fm.error_urls['fetcherror'], FeedCache.FetchError)
        self.assertIsInstance(fm.error_urls['parseerror'], FeedCache.ParseError)

    def test_adds_feed_author(self):
        """
        Test that a feed missing the `author_detail` attribute on its entries
        has it added.
        """
        # Ensure that any future changes to the test file at ATOM_PATH don't
        # include <author> for each entry (which would render this test useless)
        feed = TEST_ATOM
        first = feed['entries'][0]
        if hasattr(first, 'author_detail'):
            del first['author_detail']
        first_entry = feed['entries'][0]
        self.assertNotIn('author_detail', first_entry)
        self.assertNotIn('author_name', first_entry)

        # Now simulate fetching URL, after which the entry should have an
        # `author_name` attribute
        mc = build_mock_cacher()
        fm = FeedMixer(feeds=['atom'], cacher=mc, num_keep=1)
        me = fm.mixed_entries
        mc.assert_called_once_with('atom')
        self.assertIn('author_name', me[0])


class TestAtomFeed(unittest.TestCase):
    def test_atom_feed(self):
        known_good = """"""
        mc = build_mock_cacher()
        fm = FeedMixer(feeds=['atom', 'rss'], cacher=mc, num_keep=1)
        af = fm.atom_feed()
        self.assertEqual(af, known_good)

import unittest
from unittest.mock import MagicMock, call
from feedcache import FeedCache
from urllib.error import URLError
import feedparser
from feedmixer import FeedMixer
from copy import deepcopy

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
        feed = deepcopy(TEST_ATOM)
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
        """
        Test serialization as Atom.
        """
        expected = '''<?xml version="1.0" encoding="utf-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom"><title>Title</title><link href="" rel="alternate"></link><id></id><updated>2017-04-05T18:48:43Z</updated><entry><title>Uber finds one allegedly stolen Waymo file on an employee’s personal device</title><link href="https://techcrunch.com/2017/04/05/uber-finds-one-allegedly-stolen-waymo-file-on-an-employees-personal-device/" rel="alternate"></link><published>2017-04-05T18:48:43Z</published><updated>2017-04-05T18:48:43Z</updated><author><name>folz</name></author><id>https://news.ycombinator.com/item?id=14044517</id><summary type="html">&lt;p&gt;Article URL: &lt;a href="https://techcrunch.com/2017/04/05/uber-finds-one-allegedly-stolen-waymo-file-on-an-employees-personal-device/"&gt;https://techcrunch.com/2017/04/05/uber-finds-one-allegedly-stolen-waymo-file-on-an-employees-personal-device/&lt;/a&gt;&lt;/p&gt;&lt;p&gt;Comments URL: &lt;a href="https://news.ycombinator.com/item?id=14044517"&gt;https://news.ycombinator.com/item?id=14044517&lt;/a&gt;&lt;/p&gt;&lt;p&gt;Points: 336&lt;/p&gt;&lt;p&gt;# Comments: 206&lt;/p&gt;</summary></entry><entry><title>A Look At Bernie Sanders\' Electoral Socialism</title><link href="http://americancynic.net/log/2016/2/27/a_look_at_bernie_sanders_electoral_socialism/" rel="alternate"></link><published>2016-02-27T22:33:51Z</published><updated>2017-02-15T07:00:00Z</updated><author><name>A. Cynic</name><uri>http://americancynic.net</uri></author><id>tag:americancynic.net,2016-02-27:/log/2016/2/27/a_look_at_bernie_sanders_electoral_socialism/</id><summary type="html">On the difference between democratic socialism and social democracy, the future of capitalism, and the socialist response to the Bernie Sanders presidential campaign.</summary></entry></feed>'''
        mc = build_mock_cacher()
        fm = FeedMixer(feeds=['atom', 'rss'], cacher=mc, num_keep=1)
        af = fm.atom_feed()
        self.maxDiff = None
        self.assertIn(expected, af)


class TestRSSFeed(unittest.TestCase):
    def test_rss_feed(self):
        """
        Test serialization as RSS.
        """
        expected = '''<?xml version="1.0" encoding="utf-8"?>\n<rss version="2.0"><channel><title>Title</title><link></link><description></description><lastBuildDate>Wed, 05 Apr 2017 18:48:43 -0000</lastBuildDate><item><title>Uber finds one allegedly stolen Waymo file on an employee’s personal device</title><link>https://techcrunch.com/2017/04/05/uber-finds-one-allegedly-stolen-waymo-file-on-an-employees-personal-device/</link><description>&lt;p&gt;Article URL: &lt;a href="https://techcrunch.com/2017/04/05/uber-finds-one-allegedly-stolen-waymo-file-on-an-employees-personal-device/"&gt;https://techcrunch.com/2017/04/05/uber-finds-one-allegedly-stolen-waymo-file-on-an-employees-personal-device/&lt;/a&gt;&lt;/p&gt;&lt;p&gt;Comments URL: &lt;a href="https://news.ycombinator.com/item?id=14044517"&gt;https://news.ycombinator.com/item?id=14044517&lt;/a&gt;&lt;/p&gt;&lt;p&gt;Points: 336&lt;/p&gt;&lt;p&gt;# Comments: 206&lt;/p&gt;</description><dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/">folz</dc:creator><pubDate>Wed, 05 Apr 2017 18:48:43 -0000</pubDate><comments>https://news.ycombinator.com/item?id=14044517</comments><guid isPermaLink="false">https://news.ycombinator.com/item?id=14044517</guid></item><item><title>A Look At Bernie Sanders\' Electoral Socialism</title><link>http://americancynic.net/log/2016/2/27/a_look_at_bernie_sanders_electoral_socialism/</link><description>On the difference between democratic socialism and social democracy, the future of capitalism, and the socialist response to the Bernie Sanders presidential campaign.</description><dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/">A. Cynic</dc:creator><pubDate>Sat, 27 Feb 2016 22:33:51 -0000</pubDate><guid isPermaLink="false">tag:americancynic.net,2016-02-27:/log/2016/2/27/a_look_at_bernie_sanders_electoral_socialism/</guid></item></channel></rss>'''
        mc = build_mock_cacher()
        fm = FeedMixer(feeds=['atom', 'rss'], cacher=mc, num_keep=1)
        rf = fm.rss_feed()
        self.maxDiff = None
        self.assertIn(expected, rf)


class TestJSONFeed(unittest.TestCase):
    def test_json_feed(self):
        """
        Test serialization as JSON.
        """
        expected = '''[{"author_email": null, "author_link": null, "author_name": "folz", "comments": "https://news.ycombinator.com/item?id=14044517", "description": "<p>Article URL: <a href=\\"https://techcrunch.com/2017/04/05/uber-finds-one-allegedly-stolen-waymo-file-on-an-employees-personal-device/\\">https://techcrunch.com/2017/04/05/uber-finds-one-allegedly-stolen-waymo-file-on-an-employees-personal-device/</a></p><p>Comments URL: <a href=\\"https://news.ycombinator.com/item?id=14044517\\">https://news.ycombinator.com/item?id=14044517</a></p><p>Points: 336</p><p># Comments: 206</p>", "enclosures": [], "item_copyright": null, "link": "https://techcrunch.com/2017/04/05/uber-finds-one-allegedly-stolen-waymo-file-on-an-employees-personal-device/", "pubdate": "2017-04-05 18:48:43", "title": "Uber finds one allegedly stolen Waymo file on an employee\\u2019s personal device", "unique_id": "https://news.ycombinator.com/item?id=14044517", "updateddate": "2017-04-05 18:48:43"}, {"author_email": null, "author_link": "http://americancynic.net", "author_name": "A. Cynic", "comments": null, "description": "On the difference between democratic socialism and social democracy, the future of capitalism, and the socialist response to the Bernie Sanders presidential campaign.", "enclosures": [], "item_copyright": null, "link": "http://americancynic.net/log/2016/2/27/a_look_at_bernie_sanders_electoral_socialism/", "pubdate": "2016-02-27 22:33:51", "title": "A Look At Bernie Sanders\' Electoral Socialism", "unique_id": "tag:americancynic.net,2016-02-27:/log/2016/2/27/a_look_at_bernie_sanders_electoral_socialism/", "updateddate": "2017-02-15 07:00:00"}]'''
        mc = build_mock_cacher()
        fm = FeedMixer(feeds=['atom', 'rss'], cacher=mc, num_keep=1)
        jf = fm.json_feed()
        self.maxDiff = None
        self.assertIn(expected, jf)

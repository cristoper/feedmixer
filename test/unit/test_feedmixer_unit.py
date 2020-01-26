import unittest
from unittest.mock import Mock, MagicMock, call, ANY
import feedparser
from feedmixer import FeedMixer, ParseError, cache_parser
import requests
from requests.exceptions import RequestException
from shelfcache import shelfcache


ATOM_PATH = 'test/test_atom.xml'
RSS_PATH = 'test/test_rss2.xml'

OK = 200

with open(ATOM_PATH, 'r') as f:
    TEST_ATOM = ''.join(f.readlines())

with open(RSS_PATH, 'r') as f:
    TEST_RSS = ''.join(f.readlines())


def build_response(status=OK, etag='etag', modified='modified', max_age=None):
    """Make a requests.Response object suitable for testing.
    Args:
        status: HTTP status
        exp-time: cache expire time (set to future for fresh cache, past for
            stale cache (defaults to stale))
        etag: etag cache-control header
        modified: last-modified cache-control header
    Returns:
        A Response instance populated according to the arguments.
    """
    headers = {'last-modified': modified, 'etag': etag, 'Cache-Control':
               'max-age={}'.format(max_age)}
    test_response = requests.Response()
    test_response.status_code = status
    test_response.headers = headers
    return test_response


def build_stub_session():
    def mock_fetch(url, **kwargs):
        """Mimics the cache_get() method"""
        if url == "atom":
            resp = MagicMock()
            resp.text = TEST_ATOM
            return resp
        elif url == "fetcherror":
            raise RequestException("fetch error")
        elif url == "parseerror":
            raise ParseError("parse error")
        elif url == "rss":
            resp = MagicMock()
            resp.text = TEST_RSS
            return resp
        else:
            resp = MagicMock(spec=requests.Response)
            resp.text = url
            return resp
    stub_session = MagicMock(spec=requests.session())
    stub_session.get = MagicMock(side_effect=mock_fetch)
    return stub_session

class TestMixedEntries(unittest.TestCase):
    def test_empty(self):
        """
        Test with an empty `feeds` list.
        """
        mc = build_stub_session()
        fm = FeedMixer(feeds=[], sess=mc)
        me = fm.mixed_entries
        mc.assert_not_called()
        self.assertEqual(me, [])

    def test_single_good(self):
        """
        Test with a single good URL.
        """
        mc = build_stub_session()
        fm = FeedMixer(feeds=['atom'], num_keep=2, sess=mc)
        me = fm.mixed_entries
        mc.get.assert_called_once_with('atom')
        self.assertEqual(len(me), 2)

    def test_memoized(self):
        """
        Test that calls to the parser are memoized
        """
        mc = build_stub_session()
        cache_parser.cache_clear()
        fm = FeedMixer(feeds=['atom'], num_keep=2, sess=mc)
        me = fm.mixed_entries
        fm = FeedMixer(feeds=['atom'], num_keep=2, sess=mc)
        me = fm.mixed_entries
        hits, misses, _, _ = cache_parser.cache_info()
        self.assertEqual(hits, 1)
        self.assertEqual(misses, 1)

    def test_multi_good(self):
        """
        Test with multiple good URLs.
        """
        cache_parser.cache_clear()
        mc = build_stub_session()
        fm = FeedMixer(feeds=['atom', 'rss', 'atom'], num_keep=2, sess=mc)
        me = fm.mixed_entries
        mc.get.assert_has_calls([call('atom'), call('rss'), call('atom')],
                any_order=True)
        self.assertEqual(len(me), 6)

    def test_single_exception(self):
        """
        Test with a single URL which throws an exception.
        """
        mc = build_stub_session()
        fm = FeedMixer(feeds=['fetcherror'], num_keep=2, sess=mc)
        me = fm.mixed_entries
        self.assertEqual(len(me), 0)
        self.assertIsInstance(fm.error_urls['fetcherror'], RequestException)

    def test_multi_exception(self):
        """
        Test with several URLs which all throw exceptions.
        """
        mc = build_stub_session()
        fm = FeedMixer(feeds=['fetcherror', 'parseerror'], num_keep=2, sess=mc)
        me = fm.mixed_entries
        self.assertEqual(len(me), 0)
        self.assertIsInstance(fm.error_urls['fetcherror'], RequestException)
        self.assertIsInstance(fm.error_urls['parseerror'], ParseError)

    def test_multi_mixed(self):
        """
        Test with several URLs, some of which succeed and some of which throw
        exceptions.
        """
        mc = build_stub_session()
        fm = FeedMixer(feeds=['fetcherror', 'atom', 'rss', 'parseerror'],
                       num_keep=2, sess=mc)
        me = fm.mixed_entries
        mc.get.assert_has_calls([call('fetcherror'), call('atom'), call('rss'),
                             call('parseerror')], any_order=True)
        self.assertEqual(len(me), 4)
        self.assertEqual(len(fm.error_urls.keys()), 2)
        self.assertIsInstance(fm.error_urls['fetcherror'], RequestException)
        self.assertIsInstance(fm.error_urls['parseerror'], ParseError)

    def test_keep_all_neg(self):
        """
        Setting num_keep to -1 should keep all the entries.
        """
        mc = build_stub_session()
        fm = FeedMixer(feeds=['atom'], num_keep=-1, sess=mc)
        me = fm.mixed_entries
        self.assertEqual(len(me), 12)

    def test_keep_all_zero(self):
        """
        Setting num_keep to 0 should also keep all the entries.
        """
        mc = build_stub_session()
        fm = FeedMixer(feeds=['atom'], num_keep=0, sess=mc)
        me = fm.mixed_entries
        self.assertEqual(len(me), 12)

    def test_adds_feed_author(self):
        """
        Test that a feed missing the `author_detail` attribute on its entries
        has it added.
        """
        # Ensure that any future changes to the test file at ATOM_PATH don't
        # include <author> for each entry (which would render this test useless)
        feed = feedparser.parse(TEST_ATOM)
        first = feed['entries'][0]
        if hasattr(first, 'author_detail'):
            del first['author_detail']
        first_entry = feed['entries'][0]
        self.assertNotIn('author_detail', first_entry)
        self.assertNotIn('author_name', first_entry)

        # Now simulate fetching URL, after which the entry should have an
        # `author_name` attribute
        mc = build_stub_session()
        fm = FeedMixer(feeds=['atom'], num_keep=1, sess=mc)
        me = fm.mixed_entries
        mc.get.assert_called_once_with('atom')
        self.assertIn('author_name', me[0])


class TestFeed(unittest.TestCase):
    def test_set_feed(self):
        """
        Test that setting the feed property clears existing mixed_entries.
        """
        # First fetch some entries
        mc = build_stub_session()
        fm = FeedMixer(feeds=['atom', 'rss'], num_keep=1, sess=mc)
        self.assertEqual(len(fm.mixed_entries), 2)

        # Now clear feeds and assert that mixed_entries is also cleared
        fm.feeds = []
        self.assertEqual(len(fm.mixed_entries), 0)

    def test_set_num_keep(self):
        """
        Test that setting the num_keep property re-fetches the feeds.
        """
        # First fetch some entries
        mc = build_stub_session()
        fm = FeedMixer(feeds=['atom', 'rss'], num_keep=2, sess=mc)
        self.assertEqual(len(fm.mixed_entries), 4)

        # Now clear feeds and assert that mixed_entries is also cleared
        fm.num_keep = 1
        self.assertEqual(len(fm.mixed_entries), 2)


class TestAtomFeed(unittest.TestCase):
    def test_atom_feed(self):
        """
        Test serialization as Atom.
        """
        # NOTE: expected does not contain entire text because the RSS entry has no
        # pubdate so the UPDATED tag is given the current date; instead of the
        # complication of inserting that into expected, we just test up to that
        # point.
        expected = '''<?xml version="1.0" encoding="utf-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom"><title>Title</title><link href="" rel="alternate"></link><id></id><updated>2017-02-15T07:00:00Z</updated><entry><title>A Look At Bernie Sanders\' Electoral Socialism</title><link href="http://americancynic.net/log/2016/2/27/a_look_at_bernie_sanders_electoral_socialism/" rel="alternate"></link><published>2016-02-27T22:33:51Z</published><updated>2017-02-15T07:00:00Z</updated><author><name>A. Cynic</name><uri>http://americancynic.net</uri></author><id>tag:americancynic.net,2016-02-27:/log/2016/2/27/a_look_at_bernie_sanders_electoral_socialism/</id><summary type="html">On the difference between democratic socialism and social democracy, the future of capitalism, and the socialist response to the Bernie Sanders presidential campaign.</summary></entry><entry><title>Uber finds one allegedly stolen Waymo file on an employee’s personal device</title><link href="https://techcrunch.com/2017/04/05/uber-finds-one-allegedly-stolen-waymo-file-on-an-employees-personal-device/" rel="alternate"></link><updated>'''
        mc = build_stub_session()
        fm = FeedMixer(feeds=['atom', 'rss'], num_keep=1, sess=mc)
        af = fm.atom_feed()
        self.maxDiff = None
        self.assertIn(expected, af)

    def test_atom_prefer_summary(self):
        """
        Test that passing prefer_summary=True will return the short 'summary'
        """
        expected = '''On the difference between democratic socialism and social democracy, the future of capitalism, and the socialist response to the Bernie Sanders presidential campaign.'''
        mc = build_stub_session()
        fm = FeedMixer(feeds=['atom'], num_keep=1, sess=mc,
                prefer_summary=True)
        me = fm.mixed_entries[0]
        self.assertEqual(me.get('description'), expected)

    def test_atom_prefer_content(self):
        """
        Test that passing prefer_summary=False will ask the parser for the full
        entry content.
        """
        mc = build_stub_session()
        fm = FeedMixer(feeds=['atom'], num_keep=1, sess=mc,
                prefer_summary=False)
        me = fm.mixed_entries[0]
        self.assertTrue(len(me.get('description')) > 1000)


class TestRSSFeed(unittest.TestCase):
    def test_rss_feed(self):
        """
        Test serialization as RSS.
        """
        expected = '''<?xml version="1.0" encoding="utf-8"?>\n<rss version="2.0"><channel><title>Title</title><link></link><description></description><lastBuildDate>Wed, 15 Feb 2017 07:00:00 -0000</lastBuildDate><item><title>A Look At Bernie Sanders\' Electoral Socialism</title><link>http://americancynic.net/log/2016/2/27/a_look_at_bernie_sanders_electoral_socialism/</link><description>On the difference between democratic socialism and social democracy, the future of capitalism, and the socialist response to the Bernie Sanders presidential campaign.</description><dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/">A. Cynic</dc:creator><pubDate>Sat, 27 Feb 2016 22:33:51 -0000</pubDate><guid isPermaLink="false">tag:americancynic.net,2016-02-27:/log/2016/2/27/a_look_at_bernie_sanders_electoral_socialism/</guid></item><item><title>Uber finds one allegedly stolen Waymo file on an employee’s personal device</title><link>https://techcrunch.com/2017/04/05/uber-finds-one-allegedly-stolen-waymo-file-on-an-employees-personal-device/</link><description>&lt;p&gt;Article URL: &lt;a href="https://techcrunch.com/2017/04/05/uber-finds-one-allegedly-stolen-waymo-file-on-an-employees-personal-device/"&gt;https://techcrunch.com/2017/04/05/uber-finds-one-allegedly-stolen-waymo-file-on-an-employees-personal-device/&lt;/a&gt;&lt;/p&gt;&lt;p&gt;Comments URL: &lt;a href="https://news.ycombinator.com/item?id=14044517"&gt;https://news.ycombinator.com/item?id=14044517&lt;/a&gt;&lt;/p&gt;&lt;p&gt;Points: 336&lt;/p&gt;&lt;p&gt;# Comments: 206&lt;/p&gt;</description><dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/">folz</dc:creator><comments>https://news.ycombinator.com/item?id=14044517</comments><guid isPermaLink="false">https://news.ycombinator.com/item?id=14044517</guid><enclosure length="501" type="image/jpeg" url="image.jpg"></enclosure></item></channel></rss>'''
        mc = build_stub_session()
        fm = FeedMixer(feeds=['atom', 'rss'], num_keep=1, sess=mc)
        rf = fm.rss_feed()
        self.maxDiff = None
        self.assertIn(expected, rf)


class TestJSONFeed(unittest.TestCase):
    def test_json_feed(self):
        """
        Test serialization as JSON.
        """
        expected = '''{"version": "https://jsonfeed.org/version/1", "title": "Title", "home_page_url": "", "description": "", "items": [{"title": "A Look At Bernie Sanders\' Electoral Socialism", "content_html": "On the difference between democratic socialism and social democracy, the future of capitalism, and the socialist response to the Bernie Sanders presidential campaign.", "url": "http://americancynic.net/log/2016/2/27/a_look_at_bernie_sanders_electoral_socialism/", "id": "tag:americancynic.net,2016-02-27:/log/2016/2/27/a_look_at_bernie_sanders_electoral_socialism/", "author": {"name": "A. Cynic", "url": "http://americancynic.net"}, "date_published": "2016-02-27T22:33:51Z", "date_modified": "2017-02-15T07:00:00Z"}, {"title": "Uber finds one allegedly stolen Waymo file on an employee\\u2019s personal device", "content_html": "<p>Article URL: <a href=\\"https://techcrunch.com/2017/04/05/uber-finds-one-allegedly-stolen-waymo-file-on-an-employees-personal-device/\\">https://techcrunch.com/2017/04/05/uber-finds-one-allegedly-stolen-waymo-file-on-an-employees-personal-device/</a></p><p>Comments URL: <a href=\\"https://news.ycombinator.com/item?id=14044517\\">https://news.ycombinator.com/item?id=14044517</a></p><p>Points: 336</p><p># Comments: 206</p>", "url": "https://techcrunch.com/2017/04/05/uber-finds-one-allegedly-stolen-waymo-file-on-an-employees-personal-device/", "id": "https://news.ycombinator.com/item?id=14044517", "author": {"name": "folz"}, "attachments": [{"url": "image.jpg", "size_in_bytes": "501", "mime_type": "image/jpeg"}]}]}'''
        mc = build_stub_session()
        fm = FeedMixer(feeds=['atom', 'rss'], num_keep=1, sess=mc)
        jf = fm.json_feed()
        self.maxDiff = None
        self.assertIn(expected, jf)

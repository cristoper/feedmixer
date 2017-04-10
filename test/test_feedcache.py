from feedcache import FeedCache
import unittest
from unittest.mock import patch, MagicMock, ANY
from locked_shelf import RWShelf
import feedparser
import datetime
from urllib.error import URLError
from http.client import NOT_MODIFIED, OK

ATOM_PATH = 'test/test_atom.xhtml'


def mock_locked_shelf(return_value=None):
    """Helper function to create a mocked RWShelf instance.

    Args:
        return_value: the value returned by the mocked shelf.get() method
    Returns:
        a MagicMock object spec'd to RWShelf
    """
    mock_shelf = MagicMock(spec=RWShelf)
    mock_get = MagicMock(return_value=return_value)
    mock_set = MagicMock()
    mock_shelf.return_value.__enter__.return_value.get = mock_get
    mock_shelf.return_value.__enter__.return_value.__setitem__ = mock_set
    return mock_shelf


def build_feed(test_file=ATOM_PATH, status=OK,
               exp_time=datetime.datetime.now(), etag='etag',
               modified='modified', max_age=None):
    """Read an Atom/RSS feed from file and return a FeedCache.Feed object
    suitable for testing.

    Args:
        test_file: Path to file containing test Atom/RSS feed
        status: HTTP status
        exp-time: cache expire time (set to future for fresh cache, past for
        stale cache (defaults to stale)
        etag: etag cache-control header
        modified: last-modified cache-control header

    Returns:
        A FeedCache.Feed instance populated by parsing the contents of
        `test_file`
    """
    with open(test_file, 'r') as f:
        feed = ''.join(f.readlines())
        test_parsed = feedparser.parse(feed)
    test_parsed.etag = etag
    test_parsed['etag'] = etag
    test_parsed.modified = modified
    test_parsed['modified'] = modified
    test_parsed.status = status
    test_parsed['status'] = status
    if max_age:
        test_parsed['headers'] = {'cache-control': 'max-age={}'.format(max_age)}
    return FeedCache.Feed(test_parsed, exp_time)


def build_parser(return_value):
    """Build a mock feedparser.parse method.

    Args:
        return_value: the value to be returned by the call to `parse()`
        (probably a dictionary representing a parsed feed).

    Returns:
        A MagicMock instance spec'd to feedparser.parse
    """
    mock_parser = MagicMock(spec=feedparser.parse)
    mock_parser.return_value = return_value
    return mock_parser


class TestFetch(unittest.TestCase):
    def setUp(self):
        pass

    @patch('os.path.exists')
    def test_db_not_exists(self, mock_os_path_exists):
        """
        Test that the cache returns None if the database does not exist.
        """
        # Report the database file as non-existent:
        mock_os_path_exists.return_value = False

        # setup mock locked_shelf:
        new_feed = build_feed()
        mock_shelf = mock_locked_shelf(None)

        # setup mock feedparser.parse method
        mock_parser = build_parser(new_feed.feed)

        # DUT:
        fc = FeedCache(db_path='dummy', shelf_t=mock_shelf,
                       parse=mock_parser).fetch('fake_url')

        self.assertEqual(fc, new_feed.feed)
        mock_parser.assert_called_once_with('fake_url', None, None)

    @patch('os.path.exists')
    def test_new(self, mock_os_path_exists):
        """Simulate a URL not in the cache, and verify that FeedCache tries to
        fetch it over http."""
        # so we don't need an actual db file:
        mock_os_path_exists.return_value = True

        # setup mock locked_shelf:
        new_feed = build_feed()
        mock_shelf = mock_locked_shelf(None)

        # setup mock feedparser.parse method
        mock_parser = build_parser(new_feed.feed)

        # DUT:
        fc = FeedCache(db_path='dummy', shelf_t=mock_shelf,
                       parse=mock_parser).fetch('fake_url')

        self.assertEqual(fc, new_feed.feed)
        mock_parser.assert_called_once_with('fake_url', None, None)

    @patch('os.path.exists')
    def test_fresh(self, mock_os_path_exists):
        """Simulate a freshly cached feed and verify that FeedCache returns
        it."""
        # so we don't need an actual db file:
        mock_os_path_exists.return_value = True

        # setup mock locked_shelf:
        fresh_time = datetime.datetime.now() + datetime.timedelta(days=1)
        fresh_feed = build_feed(exp_time=fresh_time)
        mock_shelf = mock_locked_shelf(fresh_feed)

        # setup mock feedparser.parse method
        mock_parser = build_parser(fresh_feed.feed)

        # DUT:
        fc = FeedCache(db_path='dummy', shelf_t=mock_shelf,
                       parse=mock_parser).fetch('fake_url')

        self.assertEqual(fc, fresh_feed.feed)
        # since feed is resh, assert that the parser is not called:
        mock_parser.assert_not_called()

    @patch('os.path.exists')
    def test_stale_not_modified(self, mock_os_path_exists):
        """Simulate a stale cached feed and verify that FeedCache fetches it and
        then asks the remote server for an updated."""
        # so we don't need an actual db file:
        mock_os_path_exists.return_value = True

        # setup mocked RWShelf
        stale_time = datetime.datetime.now() - datetime.timedelta(days=500)
        stale_feed = build_feed(exp_time=stale_time, status=NOT_MODIFIED)
        mock_shelf = mock_locked_shelf(stale_feed)

        # setup mock feedparser.parse method
        mock_parser = build_parser(stale_feed.feed)

        # instantiate DUT:
        fc = FeedCache(db_path='dummy', shelf_t=mock_shelf,
                       parse=mock_parser).fetch('fake_url')

        mock_parser.assert_called_once_with('fake_url', 'etag', 'modified')
        self.assertEqual(fc, stale_feed.feed)

    @patch('os.path.exists')
    def test_stale_modified(self, mock_os_path_exists):
        """Simulate a stale cached feed and verify that FeedCache fetches it and
        then updates with new feed from server."""
        # so we don't need an actual db file:
        mock_os_path_exists.return_value = True

        # setup mocked RWShelf
        stale_time = datetime.datetime.now() - datetime.timedelta(days=500)
        stale_feed = build_feed(exp_time=stale_time, status=OK)
        mock_shelf = mock_locked_shelf(stale_feed)

        # setup mock feedparser.parse method  (and mock headers so we can verify
        # that FeedCache parsed the cache-control header)
        mock_headers = MagicMock(spec=dict)
        mock_headers.get.return_value = 'max-age=10'
        new_feed = stale_feed.feed
        new_feed['headers'] = mock_headers
        new_feed.entries[0].title = "This title was changed on the server"
        mock_parser = build_parser(new_feed)

        # instantiate DUT:
        fc = FeedCache(db_path='dummy', shelf_t=mock_shelf,
                       parse=mock_parser).fetch('fake_url')

        mock_parser.assert_called_once_with('fake_url', 'etag', 'modified')
        mock_headers.get.assert_called_with('cache-control')

        # Make sure feed was updated:
        mock_set = mock_shelf.return_value.__enter__.return_value.__setitem__
        mock_shelf.assert_any_call('dummy', 'c')
        mock_set.assert_called_with('fake_url', ANY)

        self.assertEqual(fc, new_feed)

    @patch('os.path.exists')
    def test_404(self, mock_os_path_exists):
        """Simulate fetching a non-existent feed."""
        # so we don't need an actual db file:
        mock_os_path_exists.return_value = True

        # setup mocked RWShelf
        feed404 = build_feed(status=404)
        mock_shelf = mock_locked_shelf(None)

        # setup mock feedparser.parse method
        mock_parser = build_parser(feed404.feed)

        # instantiate DUT:
        fc = FeedCache(db_path='dummy', shelf_t=mock_shelf,
                       parse=mock_parser)

        with self.assertRaises(FeedCache.FetchError) as e:
            fc.fetch('http://notfound/')
        self.assertEqual(404, e.exception.status)
        mock_parser.assert_called_once_with('http://notfound/', None, None)

    @patch('os.path.exists')
    def test_fetch_error(self, mock_os_path_exists):
        """
        Test case if feedparser returns an object with no `status` attribute (we
        assume some sort of network error occurred).
        """
        # so we don't need an actual db file:
        mock_os_path_exists.return_value = True

        # setup mocked RWShelf
        feed_err = build_feed(status=None)
        mock_shelf = mock_locked_shelf(None)

        # setup mock feedparser.parse method
        mock_parser = build_parser(feed_err.feed)

        # instantiate DUT:
        fc = FeedCache(db_path='dummy', shelf_t=mock_shelf,
                       parse=mock_parser)

        with self.assertRaises(FeedCache.FetchError):
            fc.fetch('http://domain/error')
        mock_parser.assert_called_once_with('http://domain/error', None, None)

    @patch('os.path.exists')
    def test_parse_error(self, mock_os_path_exists):
        """Simulate a fatal parse error."""
        # so we don't need an actual db file:
        mock_os_path_exists.return_value = True

        # setup mocked RWShelf
        error_feed = {}
        error_feed['bozo'] = 1
        error_feed['bozo_exception'] = ("xml.sax._exceptions.SAXParseException"
                                        "('syntax error')")
        error_feed['entries'] = []
        error_feed['feed'] = {}
        error_feed['status'] = 301

        mock_shelf = mock_locked_shelf(None)

        # setup mock feedparser.parse method
        mock_parser = build_parser(error_feed)

        # instantiate DUT:
        fc = FeedCache(db_path='dummy', shelf_t=mock_shelf,
                       parse=mock_parser)

        with self.assertRaises(FeedCache.ParseError) as e:
            fc.fetch('http://doamin/notafeed')
            self.assertEqual(404, e.exception['status'])
        mock_parser.assert_called_once_with('http://doamin/notafeed', None,
                                            None)

    @patch('os.path.exists')
    def test_DNS_error(self, mock_os_path_exists):
        """Give fetch() a non-existing domain name and check that it handles the
        error correctly."""
        # so we don't need an actual db file:
        mock_os_path_exists.return_value = True

        # setup mocked RWShelf
        mock_shelf = mock_locked_shelf(None)

        # setup mock feedparser.parse method
        mock_parser = build_parser(None)
        mock_parser.side_effect = URLError('Name or service not known')

        # instantiate DUT:
        fc = FeedCache(db_path='dummy', shelf_t=mock_shelf,
                       parse=mock_parser)

        with self.assertRaises(URLError):
            fc.fetch('http://notfound/')

        mock_parser.assert_called_once_with('http://notfound/', None, None)

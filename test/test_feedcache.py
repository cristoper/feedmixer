from feedcache import FeedCache
import unittest
from unittest.mock import patch, MagicMock
from locked_shelf import RWShelf
import feedparser
import datetime

ATOM_PATH = 'test/test_atom.xhtml'
NOT_MODIFIED = 301
OK = 200


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


def test_feed(test_file='test/test_atom.xhtml', status=OK,
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
    test_parsed['etag'] = etag
    test_parsed['modified'] = modified
    test_parsed.status = status
    if max_age:
        test_parsed['headers'] = {'cache-control': 'max-age={}'.format(max_age)}
    return FeedCache.Feed(test_parsed, exp_time)


def test_parser(return_value):
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
    def test_fresh(self, mock_os_path_exists):
        """Simulate a freshly cached feed and verify that FeedCache returns
        it."""
        # so we don't need an actual db file:
        mock_os_path_exists.return_value = True

        # setup mock locked_shelf:
        fresh_time = datetime.datetime.now() + datetime.timedelta(days=1)
        fresh_feed = test_feed(exp_time=fresh_time)
        mock_shelf = mock_locked_shelf(fresh_feed)

        # setup mock feedparser.parse method
        mock_parser = test_parser(fresh_feed.feed)

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
        stale_feed = test_feed(exp_time=stale_time, status=NOT_MODIFIED)
        mock_shelf = mock_locked_shelf(stale_feed)

        # setup mock feedparser.parse method
        mock_parser = test_parser(stale_feed.feed)

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
        stale_feed = test_feed(exp_time=stale_time, status=OK)
        mock_shelf = mock_locked_shelf(stale_feed)

        # setup mock feedparser.parse method  (and mock headers so we can verify
        # that FeedCache parsed the cache-control header)
        mock_headers = MagicMock(spec=dict)
        mock_headers.get.return_value = None
        new_feed = stale_feed.feed
        new_feed['headers'] = mock_headers
        new_feed.entries[0].title = "This title was changed on the server"
        mock_parser = test_parser(new_feed)

        # instantiate DUT:
        fc = FeedCache(db_path='dummy', shelf_t=mock_shelf,
                       parse=mock_parser).fetch('fake_url')

        mock_parser.assert_called_once_with('fake_url', 'etag', 'modified')
        mock_headers.get.assert_called_with('cache-control')
        self.assertEqual(fc, new_feed)


class TestGet(unittest.TestCase):
    @patch('os.path.exists')
    def test_no_db(self, mock_os_path_exists):
        """If the database file does not exist, get() should return
        None."""
        mock_os_path_exists.return_value = False
        fc = FeedCache(db_path='dummy', shelf_t=self.mock_shelf).get('fake_url')
        self.mock_shelf.assert_not_called()
        self.assertEqual(fc, None)

    @patch('os.path.exists')
    def test_exists(self, mock_os_path_exists):
        """Test that FeedCache returns existing feed from shelf."""
        mock_os_path_exists.return_value = True
        mock_get = MagicMock(return_value="fake result")
        self.mock_shelf.return_value.__enter__.return_value.get = mock_get
        fc = FeedCache(db_path='dummy', shelf_t=self.mock_shelf).get('fake_url')
        self.mock_shelf.assert_called_with('dummy', 'r')
        mock_get.assert_called_with('fake_url')
        self.assertEqual(fc, "fake result")

    @patch('os.path.exists')
    def test_not_exists(self, mock_os_path_exists):
        """Test that FeedCache resturns None for key that doesn't exist in
        shelf."""
        mock_os_path_exists.return_value = True
        mock_get = MagicMock(return_value=None)
        self.mock_shelf.return_value.__enter__.return_value.get = mock_get
        fc = FeedCache(db_path='dummy', shelf_t=self.mock_shelf).get('fake_url')
        self.mock_shelf.assert_called_with('dummy', 'r')
        mock_get.assert_called_with('fake_url')
        self.assertEqual(fc, None)


class TestUpdate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(ATOM_PATH, 'r') as f:
            cls.test_atom = ''.join(f.readlines())
            cls.test_atom_parsed = feedparser.parse(cls.test_atom)
        with open(RSS_PATH, 'r') as f:
            cls.test_rss = ''.join(f.readlines())
            cls.test_rss_parsed = feedparser.parse(cls.test_rss)

class TestFetch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(ATOM_PATH, 'r') as f:
            cls.test_atom = ''.join(f.readlines())
            cls.test_atom_parsed = feedparser.parse(cls.test_atom)
        with open(RSS_PATH, 'r') as f:
            cls.test_rss = ''.join(f.readlines())
            cls.test_rss_parsed = feedparser.parse(cls.test_rss)

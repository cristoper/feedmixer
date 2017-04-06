from feedcache import FeedCache
import unittest
from unittest.mock import patch, MagicMock
from locked_shelf import RWShelf
import feedparser

ATOM_PATH = 'test/test_atom.xhtml'
RSS_PATH = 'test/test_rss2.xhtml'


class TestGet(unittest.TestCase):
    def setUp(self):
        self.mock_shelf = MagicMock(spec=RWShelf)

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

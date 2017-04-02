"""
The FeedCache class provided by this module adds [thread- and multiprocess-safe]
caching to Mark Pilgrim's feedparser (https://pypi.python.org/pypi/feedparser)
"""

import feedparser
import os.path
import datetime
from http.client import NOT_MODIFIED
import re
import logging
from locked_shelf import RWShelf

logger = logging.getLogger(__name__)


class FeedCache:
    """A wrapper for feedparser which handles caching using the standard shelve
    library."""

    class Feed:
        """A wrapper class around a parsed feed so we can add some metadata (like
        an expire time)."""
        def __init__(self, feed, expire_dt=datetime.datetime.utcnow()):
            self.feed = feed
            self.expire_dt = expire_dt

    def __init__(self, db_path: str, min_age: int = 1200):
        """
        db_path: Path to the dbm file which holds the cache
        min_age: Minimum time (seconds) to keep feed in hard cache. This is
        overridden by a smaller max-age attribute in the received cache-control
        http header (default: 1200)
        """
        logger.debug("Initialized cache: {}".format(db_path))
        self.path = db_path
        self.min_age = min_age

    def get(self, url):
        """Get a feed from the cache db by its url."""
        if os.path.exists(self.path):
            with RWShelf(self.path, flag='r') as shelf:
                return shelf.get(url)
        return None

    def update(self, url, feed):
        """Update a feed in the cache db."""
        with RWShelf(self.path, flag='c') as shelf:
            logger.info("Updated feed for url: {}".format(url))
            shelf[url] = feed

    def fetch(self, url):
        etag = None
        lastmod = None
        now = datetime.datetime.now()

        logger.debug("Fetching feed for url: {}".format(url))
        cached = self.get(url)
        if cached:
            logger.info("Got feed from cache for url: {}".format(url))
            if now < cached.expire_dt:
                # If cache is fresh, use it without further ado
                logger.info("Fresh feed found in cache: {}".format(url))
                return cached.feed

            logger.info("Stale feed found in cache: {}".format(url))
            etag = cached.feed.get('etag')
            etag = etag.lstrip('W/') if etag else None  # strip weak etag
            lastmod = cached.feed.get('modified')
        else:
            logger.info("No feed in cache for url: {}".format(url))

        # Cache wasn't fresh in db, so we'll request it, but give origin etag
        # and/or last-modified headers (if available) so we only fetch and
        # parse it if it is new/updated.
        logger.info("Fetching from remote {}".format(url))
        feed = feedparser.parse(url, etag=etag, modified=lastmod)
        fetched = FeedCache.Feed(feed)
        logger.info("Got feed from feedparser {}".format(url))
        logger.debug("Feed: {}".format(feed))

        # TODO: error handling (len(feed.entries) < 1; feed.status == 404, 410,
        # etc)

        if feed.status == NOT_MODIFIED:
            # Source says feed is still fresh
            logger.info("Server says feed is still fresh: {}".format(url))
            fetched.feed = cached.feed

        # Add to/update cache with new expire_dt
        # Using max-age parsed from cache-control header, if it exists
        cc_header = fetched.feed.headers.get('cache-control')
        ma_match = re.search('max-age=(\d+)', cc_header)
        if ma_match:
            min_age = min(int(ma_match.group(1)), self.min_age)
        else:
            self.min_age
        fetched.expire_dt = now + datetime.timedelta(seconds=min_age)
        self.update(url, fetched)
        return fetched.feed

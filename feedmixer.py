"""
Instances of FeedMixer are initialized with a list of Atom/RSS feeds, and
generate an Atom/RSS/JSON feed consisting of the most recent `num_keep` entries
from each feed.

Feeds are fetched in parallel (using threads), and cached to disk (using
FeedCache).

To set a timeout on network requests, do this in your app:

TIMEOUT = 120  # time to wait for http requests (seconds)
import socket
socket.setdefaulttimeout(TIMEOUT)
"""
import datetime
import logging
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import json
from typing import List, Optional

# https://docs.djangoproject.com/en/1.10/_modules/django/utils/feedgenerator/
import feedgenerator
from feedgenerator import Rss201rev2Feed, Atom1Feed, SyndicationFeed

from feedcache import FeedCache

logger = logging.getLogger(__name__)


class FeedMixer(object):
    def __init__(self, title: str='Title', link: str='', desc: str='', feeds:
                 List[Optional[str]]=[], num_keep: int=3, max_threads: int=5,
                 max_feeds: int=100, cache_path: str='fmcache.db') -> None:
        """
        Args:
            title: the title of the generated feed
            link: the URL of the generated feed
            desc: the description of the generated feed
            feeds: the list of feed URLs to fetch and mix
            num_keep: the number of entries to keep from each member of `feeds`
            max_threads: the maximum number of threads to spin up while fetching
            feeds
            max_feeds: the maximum number of feeds to fetch
            cache_path: path where the cache database should be created
        """
        self.title = title
        self.link = link
        self.desc = desc
        self.feeds = feeds[:max_feeds]
        self.num_keep = num_keep
        self.cache_path = cache_path
        self.max_threads = max_threads
        self._mixed_entries = []  # type: List[Optional[dict]]

    @property
    def mixed_entries(self):
        if len(self._mixed_entries) < 1:
            self.__fetch_entries()
        return self._mixed_entries

    def atom_feed(self):
        """
        Returns:
            An Atom feed consisting of the `num_keep` most recent entries from
            each of the `feeds`.
        """
        return self.__generate_feed(Atom1Feed).writeString('utf-8')

    def rss_feed(self):
        """
        Returns:
            An RSS 2 feed consisting of the `num_keep` most recent entries from
            each of the `feeds`.
        """
        return self.__generate_feed(Rss201rev2Feed).writeString('utf-8')

    def json_feed(self):
        """
        Returns:
            A JSON dict consisting of the `num_keep` most recent entries from
            each of the `feeds`.
        """
        return json.dumps(self.mixed_entries, default=lambda o: str(o))

    def __fetch_entries(self):
        """
        Multi-threaded fetching of the `feeds`. Keeps the `num_keep` most recent
        entry of each feed, then combines them (sorted chronologically),
        extracts `feedgernerator`-compatible metadata, and then stores the list
        of entries as `self.mixed_entries`
        """
        mixed_entries, parsed_entries = [], []
        cache = FeedCache(self.cache_path)
        with ThreadPoolExecutor(max_workers=self.max_threads) as exec:
            future_to_url = {exec.submit(cache.fetch, url): url for url in
                             self.feeds}
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    f = future.result()
                    if self.num_keep == -1:
                        newest = f.entries
                    else:
                        newest = f.entries[0:self.num_keep]
                    # use feed author if individual entries are missing
                    # author property
                    if 'author_detail' in f.feed:
                        for e in newest:
                            if 'author_detail' not in e:
                                e['author_detail'] = f.feed.author_detail
                                e.author_detail = f.feed.author_detail
                    parsed_entries += newest
                except Exception as e:
                    print("{} generated an exception: {}".format(url, e))

        # sort entries by published date
        parsed_entries.sort(key=lambda e: e.published, reverse=True)

        # extract metadata into a form usable by feedgenerator
        for e in parsed_entries:
            metadata = {}

            # title, link, and description are mandatory
            metadata['title'] = e.get('title', '')
            metadata['link'] = e.get('link', '')
            metadata['description'] = e.get('description', '')

            if 'author_detail' in e:
                metadata['author_email'] = e.author_detail.get('email')
                metadata['author_name'] = e.author_detail.get('name')
                metadata['author_link'] = e.author_detail.get('href')

            # convert time_struct tuples into datetime objects
            # (the min() prevents error in the off-chance that the
            # date contains a leap-second)
            tp = e.get('published_parsed')
            if tp:
                metadata['pubdate'] = datetime.datetime(*tp[:5] + (min(tp[5],
                                                                       59),))

            tu = e.get('updated_parsed')
            if tu:
                metadata['updateddate'] = datetime.datetime(*tu[:5] +
                                                            (min(tu[5], 59),))

            metadata['comments'] = e.get('comments')
            metadata['unique_id'] = e.get('id')
            metadata['item_copyright'] = e.get('license')

            if 'tags' in e:
                taglist = [tag.get('term') for tag in e.tags]
                metadata['categories'] = taglist
            if 'enclosures' in e:
                enclist = []
                for enc in e.enclosures:
                    enclist.append(feedgenerator.Enclosure(enc.href, enc.length,
                                                           enc.type))
                metadata['enclosures'] = enclist

            mixed_entries.append(metadata)
        self._mixed_entries = mixed_entries

    def __generate_feed(self, gen_cls: SyndicationFeed):
        """
        Generate a feed using one of the generator classes from the Django
        `feedgenerator` module.
        """
        gen = gen_cls(title=self.title, link=self.link, description=self.desc)
        for e in self.mixed_entries:
            gen.add_item(**e)
        return gen

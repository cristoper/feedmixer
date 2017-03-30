import datetime
import feedparser
import logging
import concurrent.futures
import json

# https://docs.djangoproject.com/en/1.10/_modules/django/utils/feedgenerator/
import feedgenerator 

from feedcache import *

#logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TIMEOUT = 120 # time to wait for http requests (seconds)
MAX_FEEDS = 100

# Move to app:
import socket
socket.setdefaulttimeout(TIMEOUT)
feeds = ['http://notwithoutsincerity.in1accord.net/rss',
        'http://bothsandneithers.tumblr.com/rss',
        'http://feeds.feedburner.com/AmericanCynic',
        'http://wholeheaptogether.in1accord.net/rss',
        'http://mymorninghaiku.blogspot.com//feeds/posts/default']


class FeedMixer(object):
    def __init__(self, title='Title', link='', desc='', feeds=[], num_keep=3, max_threads=5, cache_path='fmcache.db'):
        self.title = title
        self.link = link
        self.desc = desc
        self.feeds = feeds[:MAX_FEEDS]
        self.num_keep = num_keep
        self._mixed_entries = []
        self.cache_path = cache_path
        self.max_threads = max_threads

    @property
    def mixed_entries(self):
        if len(self._mixed_entries) < 1:
            self.fetch_entries()
        return self._mixed_entries


    def fetch_entries(self):
        mixed_entries, parsed_entries = [], []
        cache = FeedCache(self.cache_path)
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            future_to_url = {executor.submit(cache.fetch, url): url for url in self.feeds}
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
                            if not 'author_detail' in e:
                                e['author_detail'] = f.feed.author_detail
                                e.author_detail = f.feed.author_detail
                    parsed_entries += newest
                except Exception as e:
                    print("{} generated an exception: {}".format(url, e))

        # sort entries by published date
        parsed_entries.sort(key = lambda e: e.published, reverse = True)

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
                metadata['pubdate'] = datetime.datetime(*tp[:5] + (min(tp[5], 59),))

            tu = e.get('updated_parsed')
            if tu:
                metadata['updateddate'] = datetime.datetime(*tu[:5] + (min(tu[5], 59),))

            metadata['comments'] = e.get('comments')
            metadata['unique_id'] = e.get('id')
            metadata['item_copyright'] = e.get('license')

            if 'tags' in e:
                taglist = [tag.get('term') for tag in e.tags]
                metadata['categories'] = taglist
            
            if 'enclosures' in e:
                enclist = [feedgenerator.Enclosure(enc.href, enc.length, enc.type) for enc in e.enclosures]
                metadata['enclosures'] = enclist

            mixed_entries.append(metadata)
        self._mixed_entries = mixed_entries

    def generate_feed(self, gen_cls):
        gen = gen_cls(title=self.title, link=self.link, description=self.desc)
        for e in self.mixed_entries:
            gen.add_item(**e)
        return gen

    def atom_feed(self):
        return self.generate_feed(feedgenerator.Atom1Feed).writeString('utf-8')

    def rss_feed(self):
        return self.generate_feed(feedgenerator.Rss201rev2Feed).writeString('utf-8')

    def json_feed(self):
        return json.dumps(self.mixed_entries, default = lambda o: str(o))

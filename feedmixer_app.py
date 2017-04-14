"""
FeedMixer is a WSGI micro web service which takes a list of feed URLs and
returns a new feed consisting of the most recent `n` entries from each given
feed.

The module variable `api` (also available as `application`) is a WSGI-compliant
object.

See the include README.rst file for more documentation.

Usage
-----

FeedMixer exposes three endpoints:

- /atom
- /rss
- /json

When sent a GET request they return an Atom, an RSS2, or a JSON feed,
respectively. The query string of the GET request can contain two fields:

f
    A url-encoded URL of a feed (any version of Atom or RSS). To include multiple
    feeds, simply include multiple `f` fields.

n
    The number of entries to keep from each field (pass -1 to keep all entries,
    which is the default if no `n` field is provided).


As an example, assuming an instance of the FeedMixer app is running on the
localhost on port 8000, let's fetch the newest entry each from the following
Atom and RSS feeds:

- http://mretc.net/shaarli/?do=atom
- https://hnrss.org/newest

The constructed URL to GET is:

``http://localhost:8000/atom?f=http://mretc.net/shaarli/?do=atom&f=https://hnrss.org/newest&n=1``

Entering it into a browser will return an Atom feed with two entries. To GET it
from a client programatically, remember to URL-encode the `f` fields::

>>> curl 'localhost:8000/atom?f=http%3A%2F%2Fmretc.net%2Fshaarli%2F%3Fdo%3Datom&f=https%3A%2F%2Fhnrss.org%2Fnewest&n=1'


Interface
---------
"""
from feedmixer import FeedMixer
import falcon
from typing import NamedTuple, List
import json
import urllib
import urllib.parse

ParsedQS = NamedTuple('ParsedQS', [('f', List[str]),
                                   ('n', int)])

# Vars to config:
TITLE = "FeedMixer feed"
DESC = "{type} feed created by FeedMixer."
# The path where the cache database file will be created:
DBPATH = "fmcache.db"


def parse_qs(req: falcon.Request) -> ParsedQS:
    """
    Get `feeds` and `num_keep` from request query string.

    :param req: the Falcon request from which to parse the query string.
    """
    qs = falcon.uri.parse_query_string(req.query_string)
    feeds = qs.get('f', [])
    n = qs.get('n', -1)
    if not isinstance(feeds, list): feeds = [feeds] # NOQA
    return ParsedQS(feeds, int(n))


class MixedFeed:
    """
    Used to handle HTTP GET requests to all three endpoints: '/atom', '/rss',
    and '/json'

    Any errors that occur are returned in a custom HTTP header ('X-fm-errors')
    as a JSON hash.
    """
    def __init__(self, ftype: str='atom') -> None:
        """
        :param ftype: one of 'atom', 'rss', or 'json'
        """
        super().__init__()
        self.ftype = ftype

    def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        """
        Falcon GET handler.
        """
        feeds, n = parse_qs(req)
        fm = FeedMixer(feeds=feeds, num_keep=n, title=TITLE,
                       desc=DESC.format(type=self.ftype), link=req.uri,
                       cache_path=DBPATH)

        # dynamically find and call appropriate method based on ftype:
        method_name = "{}_feed".format(self.ftype)
        method = getattr(fm, method_name)
        resp.body = method()

        if fm.error_urls:
            # There were errors; report them in the 'X-fm-errors' http header as
            # a url-encoded JSON hash
            error_dict = {}
            for url, e in fm.error_urls.items():
                err_str = str(e)
                if hasattr(e, 'status'):
                    err_str += " ({})".format(e.status)
                error_dict[url] = err_str
            json_err = urllib.parse.quote(json.dumps(error_dict))
            resp.append_header('X-fm-errors', json_err)

        resp.content_type = "application/{}".format(self.ftype)
        resp.status = falcon.HTTP_200

atom = MixedFeed(ftype='atom')
rss = MixedFeed(ftype='rss')
jsn = MixedFeed(ftype='json')

api = application = falcon.API()
api.add_route('/atom', atom)
api.add_route('/rss', rss)
api.add_route('/json', jsn)

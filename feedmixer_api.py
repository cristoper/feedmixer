"""
FeedMixer is a WSGI micro web service which takes a list of feed URLs and
returns a new feed consisting of the most recent `n` entries from each given
feed.

Calling `wsgi_app()` returns a WSGI-compliant callable which can be hosted by
any WSGI server.

See `feedmixer.wsgi` for an example webservice which can be used as-is or copied
and modified.

Usage
-----

FeedMixer exposes three endpoints:

- /atom
- /rss
- /json

When sent a GET request they return an Atom, an RSS2, or a JSON feed,
respectively. The query string of the GET request can contain two fields:

f
    A url-encoded URL of a feed (any version of Atom or RSS). To include
    multiple feeds, simply include multiple `f` fields.

n
    The number of entries to keep from each field (pass -1 to keep all entries,
    which is the default if no `n` field is provided).

full
    If set, prefer the full entry `content`; otherwise prefer the shorter entry
    `summary`.

As an example, assuming an instance of the FeedMixer app is running on the localhost on port 8000, let's fetch the newest entry each from the following Atom and RSS feeds:

- https://americancynic.net/shaarli/?do=atom
- https://hnrss.org/newest

The constructed URL to GET is:

``http://localhost:8000/atom?f=https://americancynic.net/shaarli/?do=atom&f=https://hnrss.org/newest&n=1``

Entering it into a browser will return an Atom feed with two entries. To GET it
from a client programatically, remember to URL-encode the `f` fields::

>>> curl 'localhost:8000/atom?f=https%3A%2F%2Famericancynic.net%2Fshaarli%2F%3Fdo%3Datom&f=https%3A%2F%2Fhnrss.org%2Fnewest&n=1'


Interface
---------
"""
from feedmixer import FeedMixer
from shelfcache import ShelfCache
import falcon
from typing import NamedTuple, List
import json
import urllib
import urllib.parse

ParsedQS = NamedTuple('ParsedQS', [('f', List[str]),
                                   ('n', int),
                                   ('full', bool)])


def parse_qs(req: falcon.Request) -> ParsedQS:
    """
    Get `feeds` and `num_keep` from request query string.

    :param req: the Falcon request from which to parse the query string.
    """
    qs = falcon.uri.parse_query_string(req.query_string)
    feeds = qs.get('f', [])
    n = qs.get('n', -1)
    full = qs.get('full', False)
    if not isinstance(feeds, list): feeds = [feeds] # NOQA
    return ParsedQS(feeds, int(n), bool(full))


class MixedFeed:
    """
    Used to handle HTTP GET requests to all three endpoints: '/atom', '/rss',
    and '/json'

    Any errors that occur are returned in a custom HTTP header ('X-fm-errors')
    as a JSON hash.
    """
    def __init__(self, ftype='atom', title='FeedMixer feed',
                 desc='{type} feed created by FeedMixer.',
                 db_path='fmcache.db', exp_seconds=300) -> None:
        """
        :param ftype: one of 'atom', 'rss', or 'json'
        :param title: the title of the generated feed
        :param desc: description of the generated feed (the '{type}' formatting
            parameter will be replaced by the value of `ftype`)
        :param db_path: the path where the cache database file should be created
        :param exp_seconds: the default number of seconds to cache feeds before
            re-validating. This can be overridden by a Cache-Control header from
            the server.
        """
        super().__init__()
        self.ftype = ftype
        self.title = title
        self.desc = desc.format(type=ftype)
        self.cache = ShelfCache(db_path=db_path, exp_seconds=exp_seconds)

    def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        """
        Falcon GET handler.
        """
        feeds, n, full = parse_qs(req)
        summ = not full
        fm = FeedMixer(feeds=feeds, num_keep=n, prefer_summary=summ,
                       title=self.title, desc=self.desc, link=req.uri,
                       cache=self.cache)

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

        if self.ftype == 'json':
            # special case content_type for JSON
            resp.content_type = "application/json"
        else:
            resp.content_type = "application/{}+xml".format(self.ftype)
        resp.status = falcon.HTTP_200


def wsgi_app(title='FeedMixer feed', desc='{type} feed created by FeedMixer.',
             db_path='fmcache.db', exp_seconds=300) -> falcon.API:
    """
    Creates the Falcon api object (a WSGI-compliant callable)

    See `FeedMixer` docstring for parameter descriptions.
    """
    atom = MixedFeed(ftype='atom', title=title, desc=desc, db_path=db_path,
                     exp_seconds=exp_seconds)
    rss = MixedFeed(ftype='rss', title=title, desc=desc, db_path=db_path,
                    exp_seconds=exp_seconds)
    jsn = MixedFeed(ftype='json', title=title, desc=desc, db_path=db_path,
                    exp_seconds=exp_seconds)

    api = falcon.API()
    api.add_route('/atom', atom)
    api.add_route('/rss', rss)
    api.add_route('/json', jsn)
    return api

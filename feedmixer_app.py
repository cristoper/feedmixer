from feedmixer import FeedMixer
import falcon
from typing import NamedTuple, List

ParsedQS = NamedTuple('ParsedQS', [('f', List[str]),
                                   ('n', int)])


def parse_qs(req: falcon.Request) -> ParsedQS:
    qs = falcon.uri.parse_query_string(req.query_string)
    feeds = qs.get('f', [])
    n = qs.get('n', -1)
    if not isinstance(feeds, list): feeds = [feeds]
    return ParsedQS(feeds, int(n))


class JSONFeed(object):
    def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        feeds, n = parse_qs(req)
        fm = FeedMixer(feeds=feeds, num_keep=n)
        resp.body = fm.json_feed()
        resp.status = falcon.HTTP_200


class AtomFeed(object):
    def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        feeds, n = parse_qs(req)
        fm = FeedMixer(feeds=feeds, num_keep=n)
        resp.body = fm.atom_feed()
        resp.content_type = "application/atom"
        resp.status = falcon.HTTP_200


class RSSFeed(object):
    def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        feeds, n = parse_qs(req)
        fm = FeedMixer(feeds=feeds, num_keep=n)
        resp.body = fm.rss_feed()
        resp.content_type = "application/rss"
        resp.status = falcon.HTTP_200

atom = AtomFeed()
rss = RSSFeed()
json = JSONFeed()

api = application = falcon.API()
api.add_route('/atom', atom)
api.add_route('/rss', rss)
api.add_route('/json', json)

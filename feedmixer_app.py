from feedmixer import *
import falcon

def get_feeds(req):
    qs = falcon.uri.parse_query_string(req.query_string)
    feeds = qs.get('f', [])
    if not isinstance(feeds, list): feeds = [feeds]
    return feeds


class JSONFeed(object):
    def on_get(self, req, resp):
        feeds = get_feeds(req)
        fm = FeedMixer(feeds=feeds)
        resp.body = fm.json_feed()
        resp.status = falcon.HTTP_200

class AtomFeed(object):
    def on_get(self, req, resp):
        feeds = get_feeds(req)
        fm = FeedMixer(feeds=feeds)
        resp.body = fm.atom_feed()
        resp.content_type = "application/atom"
        resp.status = falcon.HTTP_200

class RSSFeed(object):
    def on_get(self, req, resp):
        fm = FeedMixer(feeds=feeds)
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

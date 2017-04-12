from feedmixer import FeedMixer
import falcon
from typing import NamedTuple, List

ParsedQS = NamedTuple('ParsedQS', [('f', List[str]),
                                   ('n', int)])

TITLE = "FeedMixer feed"
DESC = "{type} feed created by FeedMixer."


def parse_qs(req: falcon.Request) -> ParsedQS:
    qs = falcon.uri.parse_query_string(req.query_string)
    feeds = qs.get('f', [])
    n = qs.get('n', -1)
    if not isinstance(feeds, list): feeds = [feeds] # NOQA
    return ParsedQS(feeds, int(n))


class MixedFeed:
    def __init__(self, ftype: str='atom', *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.ftype = ftype

    def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        feeds, n = parse_qs(req)
        fm = FeedMixer(feeds=feeds, num_keep=n, title=TITLE,
                       desc=DESC.format(type=self.ftype), link=req.uri)

        # dynamically find and call appropriate method based on ftype:
        method_name = "{}_feed".format(self.ftype)
        method = getattr(fm, method_name)
        resp.body = method()
        resp.content_type = "application/{}".format(self.ftype)
        resp.status = falcon.HTTP_200

atom = MixedFeed(ftype='atom')
rss = MixedFeed(ftype='rss')
json = MixedFeed(ftype='json')

api = application = falcon.API()
api.add_route('/atom', atom)
api.add_route('/rss', rss)
api.add_route('/json', json)

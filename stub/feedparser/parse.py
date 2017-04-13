import feedparser.util
from typing import Optional, Union, Tuple, List, Dict
import io
import urllib
import urllib.request

time_t = Union[Tuple[int, int, int, int, int, int, int, int, int], str]
stream_str_t = Union[io.FileIO, str]
handlers_t = List[urllib.request.BaseHandler]
headers_t = Dict[str, str]


def parse(url_file_stream_or_string: stream_str_t, etag: Optional[str]=None,
          modified: Optional[time_t]=None, agent: Optional[str]=None, referrer:
          Optional[str]=None, handlers: Optional[handlers_t]=None,
          request_headers: Optional[headers_t]=None, response_headers:
          Optional[headers_t]=None) -> feedparser.util.FeedParserDict:
    ...

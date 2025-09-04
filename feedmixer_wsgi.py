"""
This module instantiates the feedmixer WSGI object with sensible defaults and a
rotating logfile (or to syslog if running multiprocess) as both `api` and
`application` (default names used by common WSGI servers). To start the service
with gunicorn_, for example, clone the repository and in the root directory
run::

$ gunicorn feedmixer_wsgi

This file can be used-as is or copied as a template (to customize things like
the title, description, logging, etc.)

The top-level install directory must be writable by the server running the app,
because it creates the logfiles ('fm.log' and 'fm.log.1') there.

.. _gunicorn: http://gunicorn.org/
"""

import functools
import logging
import os
import sys

import cachecontrol
import requests
import feedparser
from feedmixer import ParserCacheCallable

from feedmixer_api import wsgi_app

# envar configs
ALLOW_CORS = bool(os.environ.get("FM_ALLOW_CORS"))
LOG_LEVEL_NAME = os.environ.get("FM_LOG_LEVEL", "INFO").upper()
LOG_LEVEL = logging.getLevelName(LOG_LEVEL_NAME)
if not isinstance(LOG_LEVEL, int):
    print(
        f"feedmixer_wsgi: Invalid log level '{LOG_LEVEL_NAME}'. Defaulting to INFO.",
        file=sys.stderr,
    )
    LOG_LEVEL = logging.INFO

try:
    TIMEOUT = int(os.environ.get("FM_TIMEOUT", "30"))
except ValueError:
    print(
        f"feedmixer_wsgi: Invalid timeout value '{os.environ.get('FM_TIMEOUT')}'. Defaulting to 30.",
        file=sys.stderr,
    )
    TIMEOUT = 30


try:
    CACHE_SIZE = int(os.environ.get("FM_CACHE_SIZE", "128"))
except ValueError:
    print(
        f"feedmixer_wsgi: Invalid cache size value '{os.environ.get('FM_CACHE_SIZE')}'. Defaulting to 128.",
        file=sys.stderr,
    )
    CACHE_SIZE = 128


# Application-wide memoized parser
PARSER_CACHE: ParserCacheCallable = functools.lru_cache(maxsize=CACHE_SIZE)(
    feedparser.parse
)


# All requests share a requests.session object so they can share a CacheControl cache
SESS = cachecontrol.CacheControl(requests.session())


def application(environ, start_response):
    """
    Wrap the main WSGI app to set up logging to stderr.
    """
    # Log to stderr
    handler = logging.StreamHandler(sys.stderr)
    format_str = "%(name)s: "
    format_str += "%(asctime)s %(levelname)s:%(message)s"
    formatter = logging.Formatter(format_str)
    handler.setFormatter(formatter)
    handler.setLevel(LOG_LEVEL)
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    root_logger.handlers = []
    root_logger.addHandler(handler)

    # setup and return actual app:
    api = wsgi_app(
        sess=SESS,
        allow_cors=ALLOW_CORS,
        timeout=TIMEOUT,
        parser_cache=PARSER_CACHE,
    )
    return api(environ, start_response)


api = application

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

import logging
import logging.handlers
import multiprocessing
import socket

import cachecontrol
import requests

from feedmixer_api import wsgi_app

LOG_PATH = "fm.log"
LOG_LEVEL = logging.INFO
# LOG_LEVEL = logging.DEBUG
TIMEOUT = 120  # time to wait for http requests (seconds)
socket.setdefaulttimeout(TIMEOUT)

# all requests share a requests.session object so they can share a CacheControl cache
SESS = cachecontrol.CacheControl(requests.session())


def application(environ, start_response):
    """
    Wrap the main WSGI app so that we can intercept the 'wsgi.multiprocess'
    environment variable to set up logging accordingly.
    """
    pid = multiprocessing.current_process().pid

    is_multiprocess = environ.get("wsgi.multiprocess", False)
    if is_multiprocess:
        # log to the syslog daemon
        handler = logging.handlers.SysLogHandler(address="/dev/log")
    else:
        # Setup root logger to log to rotating log file
        handler = logging.handlers.RotatingFileHandler(
            LOG_PATH, maxBytes=100000, backupCount=1
        )
    format_str = "fm-%(name)s-" + "%d" % pid + ": "
    format_str += "%(asctime)s %(levelname)s:%(message)s"
    formatter = logging.Formatter(format_str)
    handler.setFormatter(formatter)
    handler.setLevel(LOG_LEVEL)
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    root_logger.handlers = []
    root_logger.addHandler(handler)

    # setup and return actual app:
    api = wsgi_app(sess=SESS)
    return api(environ, start_response)


api = application

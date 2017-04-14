"""
This module instantiates the feedmixer WSGI object with sensible defaults and a
rotating logfiel as both `api` and `application` (default names used by common
WSGI servers). To start the service with gunicorn_, for example, clone the
repository and in the root directory run::

$ gunicorn feedmixer_wsgi

This file can be used-as is or copied as a template (to customize things like
the title, description, cache database path, logging, etc.)

The top-level install directory must be writable by the server running the app,
because it creates the logfiles ('fm.log' and 'fm.log.1') and its cache database
('fmcach') there.

.. _gunicorn: http://gunicorn.org/
"""
from feedmixer_api import wsgi_app
import socket
import logging
import logging.handlers

LOG_PATH = 'fm.log'
LOG_LEVEL = logging.INFO

# Setup root logger to log to rotating log file
handler = logging.handlers.RotatingFileHandler(LOG_PATH, maxBytes=100000,
                                               backupCount=1)
formatter = logging.Formatter('%(asctime)s %(levelname)s:%(message)s')
handler.setFormatter(formatter)
handler.setLevel(LOG_LEVEL)
root_logger = logging.getLogger()
root_logger.setLevel(LOG_LEVEL)
root_logger.addHandler(handler)


TIMEOUT = 120  # time to wait for http requests (seconds)
socket.setdefaulttimeout(TIMEOUT)

api = application = wsgi_app()

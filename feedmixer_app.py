"""
This module instantiates the feedmixer WSGI object with sensible defaults as
both `api` and `application` (default names used by common WSGI servers). To
start the service with gunicorn_, for example, clone the repository and in the
root directory run::

$ gunicorn feedmixer_app


If you need to provide different parameters (`title`, `desc`, `db_path`), copy
or edit this file and pass them to `wsgi_app()`. See the documentation in
`feedmixer_wsgi.py`.

.. _gunicorn: http://gunicorn.org/
"""
from feedmixer_wsgi import wsgi_app
import socket

TIMEOUT = 120  # time to wait for http requests (seconds)
socket.setdefaulttimeout(TIMEOUT)

api = application = wsgi_app()

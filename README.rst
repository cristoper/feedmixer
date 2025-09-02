FeedMixer
=========
FeedMixer is a little web service (Python3/WSGI) which takes a list of feed
URLs and  combines them into a single (Atom, RSS, or JSON) feed. Useful for
personal news aggregators, "planet"-like websites, etc.

Status
------

Changelog
~~~~~~~~~

- v2.4.0_ Migrate from pipenv to uv and update dependencies. `feedgenerator` now produces slightly different output including JSONFeed 1.1.
- v2.3.2_ Update dependencies to use upstream feedparser now that the fix for `this bug <https://github.com/kurtmckee/feedparser/pull/260>`_ has been merged.
- v2.3.1_ More consistent builds: update dependencies in Pipfile.lock (which also seems to work better with newer versions of pipenv) and pin Dockerfile base image to specific hash
- v2.3.0_ Replace on-disk cache with in-memory cache. This simplifies application code and administration (don't have to worry about pruning the cache database)
- v2.2.0_ Fix handling of RSS feeds with missing pubDates so that they sort to the bottom instead of throwing an exception during sorting
- v2.1.0_ Fix handling of RSS enclosures and Atom links so that they are included in output (important if you're trying to aggregate podcasts or similar)
- v2.0.0_ The JSON output now conforms to `JSON Feed version 1`_. This breaks any client which depends on the previous ad-hoc JSON format. That legacy format will continue to be maintained in the `v1 branch`_, so any clients which don't want to update to the JSON Feed format should depend on that branch.

- v1.0.0_ Stable API. I'm using it in production for small personal "planet"-like feed aggregators.

.. _v2.3.2: https://github.com/cristoper/feedmixer/tree/v2.3.2
.. _v2.3.1: https://github.com/cristoper/feedmixer/tree/v2.3.1
.. _v2.3.0: https://github.com/cristoper/feedmixer/tree/v2.3.0
.. _v2.2.0: https://github.com/cristoper/feedmixer/tree/v2.2.0
.. _v2.1.0: https://github.com/cristoper/feedmixer/tree/v2.1.0
.. _v2.0.0: https://github.com/cristoper/feedmixer/tree/v2.0.0
.. _`JSON FEED version 1`: https://jsonfeed.org/
.. _`v1 branch`: https://github.com/cristoper/feedmixer/tree/v1
.. _v1.0.0: https://github.com/cristoper/feedmixer/tree/v1.0.0


API
---
FeedMixer exposes three endpoints:

- /atom
- /rss
- /json

When sent a GET request they return an Atom, an RSS 2.0, or a JSON feed, respectively. The query string of the GET request can contain these fields:

f
    A url-encoded URL of a feed (any version of Atom or RSS). To include multiple feeds, simply include multiple `f` fields.

n
    The number of entries to keep from each field (pass 0 to keep all entries, which is the default if no `n` field is provided).

full
    If set to anything, prefer the full entry `content`; if absent, prefer the shorter entry `summary`.

An OpenAPI specification is available in `openapi.yaml`_

.. _openapi.yaml: openapi.yaml

Features
--------

API
~~~

- Combine several feeds (just about any version of Atom and RSS should work) into a single feed
- Optionally return only the `n` most recent items from each input feed
- Control whether the output feed contains only the summary or the entire content of the input feed items
- Parser results are memoized so that repeated requests for the same feed can
  be returned without re-parsing.

Included WSGI app
~~~~~~~~~~~~~~~~~
- The provided `feedmixer_wsgi.py` application uses a session that caches HTTP
  responses so that repeatedly fetching the same sets of feeds can usually be
  responded to quickly by the FeedMixer service.

  The `FeedMixer` object can be passed a custom `requests.session` object used
  to make HTTP requests, which allows flexible customization in how requests
  are made if you need that. 

Non-features
------------
FeedMixer does not (yet?) do any resource restriction itself:

- Authorization
- Rate limiting
- CORS restriction

To protect your installation either configure a front-end http proxy to take
care of your required restrictions (Nginx is a good choice), or/and use
suitable WSGI middleware.


Installation
------------

#. Clone this repository:
   ``$ git clone https://github.com/cristoper/feedmixer.git``
#. ``$ cd feedmixer``
#. Recommended: use uv_ to create a virtualenv and install dependencies:
   ``$ uv venv``
   ``$ . .venv/bin/activate``
   ``$ uv sync``

The project consists of three modules:

- ``feedmixer.py`` - contains the core logic
- ``feedmixer_api.py`` - contains the Falcon_-based API. Call ``wsgi_app()`` to
  get a WSGI-compliant object to host.
- ``feedmixer_wsgi.py`` - contains an actual WSGI application which can be used
  as-is or as a starting point to create your own custom FeedMixer service.

.. _falcon: https://falconframework.org/
.. _gunicorn: http://gunicorn.org/
.. _`virtual environment`: https://virtualenv.pypa.io/en/stable/
.. _uv: https://github.com/astral-sh/uv

Run Locally
~~~~~~~~~~~

The feedmixer_wsgi module instantiates the feedmixer WSGI object (with sensible
defaults and a rotating logfile) as both `api` and `application` (default names
used by common WSGI servers). To start the service with gunicorn_, for example,
clone the repository and in the root directory run::

$ uv venv
$ . .venv/bin/activate
$ uv sync
$ uv pip install gunicorn
$ gunicorn feedmixer_wsgi

Note that the top-level install directory must be writable by the server
running the app, because it creates the logfiles ('fm.log' and 'fm.log.1')
there.

As an example, assuming an instance of the FeedMixer app is running on the localhost on port 8000, let's fetch the newest entry each from the following Atom and RSS feeds:

- https://catswhisker.xyz/shaarli/?do=atom
- https://hnrss.org/newest

The constructed URL to GET is:

``http://localhost:8000/atom?f=https://catswhisker.xyz/shaarli/?do=atom&f=https://hnrss.org/newest&n=1``

Entering it into a browser will return an Atom feed with two entries. To GET it from a client programatically, remember to URL-encode the `f` fields::

$ curl 'localhost:8000/atom?f=https%3A%2F%2Fcatswhisker.xyz%2Fshaarli%2F%3Fdo%3Datom&f=https%3A%2F%2Fhnrss.org%2Fnewest&n=1'

`HTTPie <https://httpie.org/>`_ is a nice command-line http client that makes testing RESTful services more pleasant::

$ pip3 install httpie
$ http localhost:8000/json f==http://hnrss.org/newest f==http://catswhisker.xyz/atom.xml n==1

You should see some JSONFeed output (since we are requesting from the `/json` endpoint):

.. code-block:: json
  
   HTTP/1.1 200 OK
   Connection: close
   Date: Thu, 23 Jan 2020 03:53:45 GMT
   Server: gunicorn/20.0.4
   content-length: 1296
   content-type: application/json

   {
     "version": "https://jsonfeed.org/version/1", 
     "title": "FeedMixer feed", 
     "home_page_url": "http://localhost:8000/json?f=http%3A%2F%2Fhnrss.org%2Fnewest&f=https%3A%2F%2Fcatswhisker.xyz%2Fatom.xml&n=1", 
     "description": "json feed created by FeedMixer.", 
     "items": [
       {
         "title": "Kyrsten Sinema, the Only Anti-Net Neutrality Dem, Linked to Comcast Super Pac", 
         "content_html": "<p>Article URL: <a href=\"https://prospect.org/politics/kyrsten-sinema-anti-net-neutrality-super-pac-comcast-lobbyist/\">https://prospect.org/politics/kyrsten-sinema-anti-net-neutrality-super-pac-comcast-lobbyist/</a></p>\n<p>Comments URL: <a href=\"https://news.ycombinator.com/item?id=22124592\">https://news.ycombinator.com/item?id=22124592</a></p>\n<p>Points: 1</p>\n<p># Comments: 0</p>", 
         "url": "https://prospect.org/politics/kyrsten-sinema-anti-net-neutrality-super-pac-comcast-lobbyist/", 
         "id": "https://news.ycombinator.com/item?id=22124592", 
         "author": {
           "name": "joeyespo"
         }, 
         "date_published": "2020-01-23T03:32:19Z", 
         "date_modified": "2020-01-23T03:32:19Z"
       }, 
       {
         "title": "FO Roundup December 2019", 
         "content_html": "I've started knitting again.", 
         "url": "http://catswhisker.xyz/log/2019/12/3/fo_december/", 
         "id": "tag:catswhisker.xyz,2019-12-04:/log/2019/12/3/fo_december/", 
         "author": {
           "name": "A. Cynic", 
           "url": "http://catswhisker.xyz/about/"
         }, 
         "date_published": "2019-12-04T04:48:59Z", 
         "date_modified": "2019-12-04T04:48:59Z"
       }
     ]
   }

Deploy
~~~~~~

Deploy FeedMixer using any WSGI-compliant server (uswgi, gunicorn, mod_wsgi,
...). For a production deployment, put an asynchronous http proxy (like Nginx)
in front of FeedMixer to protect it from too many and slow connections (as well
as to provide SSL termination, additional caching, authoriziation, etc., as
required)

Refer to the documentation of the server of your choice.

Apache
````````
For notes on deploying behind Apache, see `apache.rst`_ (from html docs: `apache.html`_)

.. _apache.rst: doc/apache.rst
.. _apache.html: apache.html

Docker
~~~~~~

An alternative to using a virtualenv for both building and deploying is to run
FeedMixer in a Docker container. The included Dockerfile will produce an image
which runs FeedMixer using gunicorn.

Build the image from the feedmixer directory::

$ docker build . -t feedmixer

Run it in the foreground::

$ docker run -p --rm 8000:8000 feedmixer

Now from another terminal you should be able to connect to FeedMixer on
localhost port 8000 just as in the example above.

The Dockerfile is based on alpine linux and produces an image that is about
60MB.

If you have issue building the docker image, you can try the included
Debian-based Dockerfile (which produces an image about twice the size of the
alpine Dockerfile):

$ docker build . -t feedmixer-debian -f Dockerfile-debian
$ docker run --rm -p 8000:8000 feedmixer-debian

Troubleshooting
---------------

Using the provided `feedmixer_wsgi.py` application, information and errors are
logged to the file `fm.log` in the directory the application is started from
(auto rotated with a single old log called `fm.1.log`).

Any errors encountered in fetching and parsing remote feeds are reported in a
custom HTTP header called `X-fm-errors`.

Hacking
-------

First install as per instructions above.

Documentation
~~~~~~~~~~~~~

Other than this README, the documentation is in the docstrings. To build a
pretty version (HTML) using Sphinx:

1. Install Sphinx dependencies: ``$ uv pip install -r doc/requirements.txt``
2. Change to `doc/` directory: ``$ cd doc``
3. Build: ``$ make html``
4. View: ``$ x-www-browser _build/html/index.html``

Tests
~~~~~

Tests are in the `test` directory and Python will find and run them with::

$ python3 -m unittest

Typechecking
~~~~~~~~~~~~

To check types using mypy_::

$ MYPYPATH=stub/ mypy --ignore-missing-imports -p feedmixer

Not everything is stubbed out, but can be useful for catching bugs after changing `feedparser.py`

.. _mypy: http://mypy-lang.org/


Get help
--------

Feel free to open an issue on Github for help: https://github.com/cristoper/feedmixer/issues


Support the project
-------------------

If this package was useful to you, please consider supporting my work on this
and other open-source projects by making a small (like a tip) one-time
donation: `donate via PayPal <https://www.paypal.me/cristoper/5>`_

If you're looking to contract a Python developer, I might be able to help.
Contact me at chris.burkhardt@orangenoiseproduction.com


License
-------

The project is licensed under the WTFPL_ license, without warranty of any kind.

.. _WTFPL: http://www.wtfpl.net/about/

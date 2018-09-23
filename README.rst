FeedMixer
=========
FeedMixer is a tiny WSGI (Python3) micro service which takes a list of feed
URLs and returns a new feed consisting of the most recent `n` entries from each
given feed.


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
    If set, prefer the full entry `content`; otherwise prefer the shorter entry `summary`.


Installation
------------

#. Clone this repository:
   ``$ git clone https://github.com/cristoper/feedmixer.git``
#. ``$ cd feedmixer``
#. Optional, but I recommend creating a `virtual environment`_:

   a. ``$ virtualenv venv`` or ``$ python3 -m venv venv``
   b. ``$ source venv/bin/activate``

#. Install dependencies: ``$ pip3 install -r requirements.txt``

The project consists of three modules:

- ``feedmixer.py`` - contains the core logic
- ``feedmixer_api.py`` - contains the Falcon_-based API. Call ``wsgi_app()`` to
  get a WSGI-compliant object to host.
- ``feedmixer_wsgi.py`` - contains an actual WSGI application which can be used
  as-is or as a template to customize.

.. _falcon: https://falconframework.org/
.. _gunicorn: http://gunicorn.org/
.. _`virtual environment`: https://virtualenv.pypa.io/en/stable/

Run Locally
~~~~~~~~~~~

The feedmixer_wsgi module instantiates the feedmixer WSGI object (with sensible
defaults and a rotating logfile) as both `api` and `application` (default names
used by common WSGI servers). To start the service with gunicorn_, for example,
clone the repository and in the root directory run::

$ gunicorn feedmixer_wsgi

Note that the top-level install directory must be writable by the server
running the app, because it creates the logfiles ('fm.log' and 'fm.log.1') and
its cache database ('fmcache.db') there.

As an example, assuming an instance of the FeedMixer app is running on the localhost on port 8000, let's fetch the newest entry each from the following Atom and RSS feeds:

- https://americancynic.net/shaarli/?do=atom
- https://hnrss.org/newest

The constructed URL to GET is:

``http://localhost:8000/atom?f=https://americancynic.net/shaarli/?do=atom&f=https://hnrss.org/newest&n=1``

Entering it into a browser will return an Atom feed with two entries. To GET it from a client programatically, remember to URL-encode the `f` fields::

$ curl 'localhost:8000/atom?f=https%3A%2F%2Famericancynic.net%2Fshaarli%2F%3Fdo%3Datom&f=https%3A%2F%2Fhnrss.org%2Fnewest&n=1'

`HTTPie <https://httpie.org/>`_ is a nice command-line http client that makes testing RESTful services more pleasant::

$ pip3 install httpie
$ http localhost:8000/json f==http://hnrss.org/newest f==http://americancynic.net/atom.xml n==1

.. code-block:: json

    HTTP/1.1 200 OK
    Access-Control-Allow-Origin: *
    Connection: Keep-Alive
    Content-Length: 1319
    Content-Type: application/json
    Date: Sat, 15 Apr 2017 00:25:18 GMT
    Keep-Alive: timeout=5, max=100
    Server: Apache/2.4.10 (Debian)

    [
        {
            "author_email": null,
            "author_link": null,
            "author_name": "cwisecarver",
            "comments": "https://news.ycombinator.com/item?id=14118526",
            "description": "I'm working through a book on functional web development with Elixir, OTP, and Phoenix (search that string and you'll find it) and I started thinking about how this language and \"platform\" had come about. I'd like to know more. Any recommendations?",
            "enclosures": [],
            "item_copyright": null,
            "link": "https://news.ycombinator.com/item?id=14118526",
            "pubdate": "2017-04-15 00:20:09",
            "title": "Ask HN: Book recommendations about how Erlang and OTP were developed?",
            "unique_id": "https://news.ycombinator.com/item?id=14118526",
            "updateddate": "2017-04-15 00:20:09"
        },
        {
            "author_email": null,
            "author_link": "http://americancynic.net",
            "author_name": "A. Cynic",
            "comments": null,
            "description": "Here are some of the better introductions to the alt-right that I've found, just in case anybody wants to waste as much time as me reading about this stuff.",
            "enclosures": [],
            "item_copyright": null,
            "link": "http://americancynic.net/log/2017/3/2/guides_to_the_alt-right/",
            "pubdate": "2017-03-02 16:42:49",
            "title": "Guides to the Alt-Right",
            "unique_id": "tag:americancynic.net,2017-03-02:/log/2017/3/2/guides_to_the_alt-right/",
            "updateddate": "2017-03-02 16:42:49"
        }
    ]

Deploy
~~~~~~

Deploy FeedMixer using any WSGI-compliant server (uswgi, gunicorn, mod_wsgi,
...). Refer to the documentation of the server of your choice.

mod_wsgi
````````

This is how I've deployed FeedMixer with Apache and mod_wsgi_ (on Debian):

#. Create a directory outside of your Apache DocumentRoot in which to install: ``$ sudo mkdir /usr/lib/wsgi-bin``
#. Install as above (so the cloned repo is at ``/usr/lib/wsgi-bin/feedmixer``)
#. Give Apache write permissions: ``$ sudo chown :www-data feedmixer; sudo chmod g+w feedmixer``
#. Configure Apache using something like the snippet below (either in apache2.conf or in a VirtualHost directive):

.. code-block:: apache

    WSGIDaemonProcess feedmixer threads=10 \
	python-home=/usr/lib/wsgi-bin/feedmixer/venv \
	python-path=/usr/lib/wsgi-bin/feedmixer \
	home=/usr/lib/wsgi-bin/feedmixer
    WSGIProcessGroup feedmixer
    WSGIApplicationGroup %{GLOBAL}
    WSGIScriptAlias /feedmixer /usr/lib/wsgi-bin/fm/feedmixer_wsgi.py
    <Directory "/usr/lib/wsgi-bin/fm">
	Require all granted
	Header set Access-Control-Allow-Origin "*"
    </Directory>

The main things to note are the ``python-home`` (set to the virtualenv directory), ``python-path``, and ``home`` options to the ``WSGIDaemonProcess``.

As configured above, Apache will run the WSGI app in a single process, handling concurrent requests on up to 10 threads. It is also possible to pass the ``processes=N`` directive to ``WSGIDaemonProcess`` in order to run the app in N processes. If ``feedmixer_wsgi.py`` detects that the WSGI server is running it in multiple processes, it will log to syslog instead of to a file.

Also note the CORS header in the Directory directive which allows the feed to
be fetched by JavaScript clients from any domain (this requires ``mod_headers``
to be enabled). Restrict (or remove) as your application requires.

.. _mod_wsgi: https://modwsgi.readthedocs.io/en/develop/

Docker
~~~~~~

An alternative to using a virtualenv for both building and deploying is to run FeedMixer in a Docker container. The included Dockerfile will produce an image which runs FeedMixer using gunicorn.

Build the image from the feedmixer directory::

$ docker build . -t feedmixer

Run it in the foreground::

$ docker run -p 8000:8000 feedmixer

Now from another terminal you should be able to connect to FeedMixer on localhost port 8000 just as in the example above.


Troubleshooting
---------------

Using the provided `feedmixer_wsgi.py` application, information and errors are logged to the file `fm.log` in the directory the application is started from (auto rotated with a single old log called `fm.1.log`).

Any errors encountered in fetching and parsing remote feeds are reported in a custom HTTP header called `X-fm-errors`.

Database Pruning
----------------
The included ``prune_expired.py`` script can be used to prune old entries from
the database (for example by running it from cron)::

    >>>  /path/to/venv/bin/python3 prune_expired.py 'dbname.db' 1200

The first argument is the path to the `ShelfCache <https://github.com/cristoper/shelfcache>`_ database file, and the second
argument is the age threshold (in seconds), any entries older than which will
be deleted.

Non-features
------------
FeedMixer does not (yet?) do these things itself, though finding or writing suitable
WSGI middleware is one way to get them (running it behind a reverse proxy server like nginx is another way):

- Authentication
- Rate limiting


Hacking
-------

First install as per instructions above.

Documentation
~~~~~~~~~~~~~

Other than this README, the documentation is in the docstrings. To build a pretty version (HTML) using Sphinx:

1. Install Sphinx dependencies: ``$ pip3 install -r doc/requirements.txt``
2. Change to `doc/` directory: ``$ cd doc``
3. Build: ``$ make html``
4. View: ``$ x-www-browser _build/html/index.html``

Tests
~~~~~

Tests are in the `test` directory and Python will find and run them with::

$ python3 -m unittest

Get help
--------

Feel free to open an issue on Github for help: https://github.com/cristoper/feedmixer/issues


Support the project
-------------------

If this package was useful to you, please consider supporting my work on this and other open-source projects by making a small (like a tip) one-time donation: `donate via PayPal <https://www.paypal.me/cristoper/5>`_

If you're looking to contract a Python developer, I might be able to help. Contact me at chris.burkhardt@orangenoiseproduction.com


License
-------

The project is licensed under the WTFPL_ license, without warranty of any kind.

.. _WTFPL: http://www.wtfpl.net/about/

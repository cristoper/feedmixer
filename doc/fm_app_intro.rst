FeedMixer is a WSGI micro web service which takes a list of feed URLs and
returns a new feed consisting of the most recent `n` entries from each given
feed.

The module variable `api` (also available as `application`) is a WSGI-compliant object. To start the service with gunicorn_, for example, clone the repository and in the root directory run::

$ gunicorn --reload feedmixer_app:api

.. _gunicorn: http://gunicorn.org/

Usage
-----
FeedMixer exposes three endpoints:

- /atom
- /rss
- /json

When sent a GET request they return an Atom, an RSS2, or a JSON feed, respectively. The query string of the GET request can contain two fields:

f
    A url-encoded URL of a feed (any version of Atom or RSS). To include multiple feeds, simply include multiple `f` fields.

n
    The number of entries to keep from each field (pass -1 to keep all entries, which is the default if no `n` field is provided).


As an example, assuming an instance of the FeedMixer app is running on the localhost on port 8000, let's fetch the newest entry each from the following Atom and RSS feeds:

- http://mretc.net/shaarli/?do=atom
- https://hnrss.org/newest

The constructed URL to GET is:

`http://localhost:8000/atom?f=http://mretc.net/shaarli/?do=atom&f=https://hnrss.org/newest&n=1`

Entering it into a browser will return an Atom feed with two entries. To GET it from a client programatically, remember to URL-encode the `f` fields::

>>> curl 'localhost:8000/atom?f=http%3A%2F%2Fmretc.net%2Fshaarli%2F%3Fdo%3Datom&f=https%3A%2F%2Fhnrss.org%2Fnewest&n=1'

FeedMixer
=========
.. include:: fm_app_intro.rst


Installation
------------

1. Clone this repository
2. Optional, but I recommend creating a `virtual environment`_:

   a. ``$ virtualenv venv``
   b. ``$ source venv/bin/activate``

3. Install dependencies: ``$ pip3 install -r requirements.txt``

FeedMixer should run in any WSGI server (uwsgi, gunicorn, mod_wsgi, ...). Refer to the documentation for your server of choice. (The module to run is `feedmixer_app.py` and the WSGI object is `api`).

TODO: example mod_wsgi setup.

.. _`virtual environment`: https://virtualenv.pypa.io/en/stable/

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

Support
-------

Feel free to open an issue on Github for help: https://github.com/cristoper/feedmixer/issues

License
-------

The project is licensed under the WTFPL_ license, without warranty of any kind.

.. _WTFPL: http://www.wtfpl.net/about/

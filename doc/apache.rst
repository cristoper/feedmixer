mod_wsgi
========
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

As configured above, Apache will run the WSGI app in a single process
(recommended), handling concurrent requests on up to 10 threads. It is also
possible to pass the ``processes=N`` directive to ``WSGIDaemonProcess`` in
order to run the app in N processes. If ``feedmixer_wsgi.py`` detects that the
WSGI server is running it in multiple processes, it will log to syslog instead
of to a file.

Also note the CORS header in the Directory directive which allows the feed to
be fetched by JavaScript clients from any domain (this requires ``mod_headers``
to be enabled). Restrict (or remove) as your application requires.

.. _mod_wsgi: https://modwsgi.readthedocs.io/en/develop/


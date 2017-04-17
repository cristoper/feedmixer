"""
A simple script to prune old entries from a ShelfCache database.

Takes two arguments:

    dbname: the full path to the database to prune
    seconds_old: any items last updated more than seconds_old seconds ago will
    be deleted

Run it with the python interpreter in your virtual environment from cron, for
example:

    >>> /path/to/venv/bin/python3 prune_expired.py 'dbname.db' 1200

ShelfCache
uses a reader/writer lock implmented with `flock`, so it should be safe to run
this any time (at least under a *nix on a local file system).
from shelfcache import ShelfCache
"""

from shelfcache import ShelfCache
import sys
from datetime import datetime, timedelta


def prune(dbname, thresh_date):
    cache = ShelfCache(dbname)
    n = cache.prune_old(thresh_date)
    print(n)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: prune_expired.py dbname seconds_old')
        sys.exit(1)
    dbname = sys.argv[1]
    age = int(sys.argv[2])
    thresh_date = datetime.utcnow() - timedelta(seconds=age)
    prune(dbname, thresh_date)

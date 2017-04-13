"""
Explicitly use the GNU dbm backend for the standard shelve class.

The default shelve implementation will use any available dbm implementation.
This module provides an `open` function which forces the use of GNU dbm. This is
less portable, but the advantage is that GNU dbm provides locking whereas other
implementations may not.

However, the GNU dbm locks are non-blocking, so to make practical use of them
requires polling on an exception. (TODO: example)

shelve docs: https://docs.python.org/3/library/shelve.html
shelve.py: https://github.com/python/cpython/blob/master/Lib/shelve.py
"""

import shelve
import dbm.gnu


class GdbmfilenameShelf(shelve.Shelf):
    """Shelf implementation using the GNU (gdbm) interface."""

    def __init__(self, filename: str, flag: str = 'c', protocol: int = None,
                 writeback: bool = False) -> None:
        super().__init__(dbm.gnu.open(filename, flag), protocol, writeback)


def open(filename: str, flag: str = 'c',
         protocol: int = None, writeback: bool = False) -> GdbmfilenameShelf:
    """Open a persistent dictionary for reading and writing using the gdbm
    database interface.

    Args:
        filename: the base filename for the underlying database.
        flag: the optional flag parameter has the same interpretation as the
        flag parameter of gdbm.open().
        protocol: the optional protocol parameter specifies the version of the
        pickle protocol (0, 1, or 2).
    """

    return GdbmfilenameShelf(filename, flag, protocol, writeback)

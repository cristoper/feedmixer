import shelve
import dbm.gnu # in python 2 this module is called gdbm

# shelve docs: https://docs.python.org/3/library/shelve.html
# shelve.py: https://github.com/python/cpython/blob/master/Lib/shelve.py

def open(filename, flag='c', protocol=None, writeback=False):
    """Open a persistent dictionary for reading and writing using the gdbm
    database interface.
    The filename parameter is the base filename for the underlying
    database.  As a side-effect, an extension may be added to the
    filename and more than one file may be created.  The optional flag
    parameter has the same interpretation as the flag parameter of
    gdbm.open(). The optional protocol parameter specifies the
    version of the pickle protocol (0, 1, or 2).
    """

    return GdbmfilenameShelf(filename, flag, protocol, writeback)

class GdbmfilenameShelf(shelve.Shelf):
    """Shelf implementation using the GNU (gdbm) interface.
    This is less portable than DbfilenameShelf in the shelve module, but gdbm
    takes care of reader/writer locking for us.
    This is initialized with the filename for the gdbm database (not including
    the .db suffix).
    """

    def __init__(self, filename, flag='c', protocol=None, writeback=False):
        import dbm
        super().__init__(dbm.gnu.open(filename, flag), protocol, writeback)

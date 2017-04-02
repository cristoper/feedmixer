from locked_shelf import MutexShelf
import shelve
import unittest
import os
import time
import threading
import multiprocessing

TEST_DB = 'test_locked.db'


class TestMutex(unittest.TestCase):
    def read_db(self, id='val'):
        with MutexShelf(TEST_DB, flag='r', lock=self.lock) as shelf:
            self.result[id] = shelf['key']
            self.messages.append("Got read lock ({})".format(threading.current_thread().ident))

    def write_db(self, value, sleep=0):
        with MutexShelf(TEST_DB, flag='c', lock=self.lock) as shelf:
            time.sleep(sleep)
            self.messages.append("Got write lock ({})".format(threading.current_thread().ident))
            shelf['key'] = value

    @classmethod
    def setUpClass(cls):
        cls.lock = threading.Lock()

    def setUp(self):
        self.result = {}
        self.messages = []
        with shelve.open(TEST_DB, flag='c') as shelf:
            shelf['key'] = "test"

    def test_threaded_write(self):
        """
        Start a slow writing thread, then a fast writing thread, and ensure that
        the slow thread finishes writing before the fast thread writes.
        """
        slow_writer = threading.Thread(target=self.write_db, args=("slow", 2))
        fast_writer = threading.Thread(target=self.write_db, args=("fast",))

        self.read_db()
        self.assertEqual(self.result['val'], "test")

        # reset messages
        self.messages = []

        slow_writer.start()
        slow_id = slow_writer.ident

        fast_writer.start()
        fast_id = fast_writer.ident

        slow_writer.join()
        fast_writer.join()
        self.read_db()
        self.assertEqual(self.messages[0], "Got write lock ({})".format(slow_id))
        self.assertEqual(self.messages[1], "Got write lock ({})".format(fast_id))
        self.assertEqual(self.result['val'], "fast")

    def test_threaded_read(self):
        """
        Start a bunch of reader threads and make sure they finish reading before
        the writing thread acquires the lock.
        """
        num_readers = 10
        readers = []

        fast_writer = threading.Thread(target=self.write_db, args=("fastr",))

        for i in range(num_readers):
            readers.append(threading.Thread(target=self.read_db, args=(i,)))
            readers[i].start()

        fast_writer.start()

        for i in range(num_readers):
            readers[i].join()

        for i in range(num_readers):
            self.assertEqual(self.result[i], "test")

    def tearDown(self):
        os.remove(TEST_DB)

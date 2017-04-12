from locked_shelf import MutexShelf, RWShelf
import shelve
import unittest
import os
import time
import threading
import multiprocessing
import logging

logger = logging.getLogger(__name__)
#logging.basicConfig(level=logging.INFO)
TEST_DB = 'test_locked.db'


class TestMutex(unittest.TestCase):
    def read_db(self, sleep=0, lock=None):
        logger.info("about to acquire read lock")
        lock = self.lock if lock is None else lock
        with MutexShelf(TEST_DB, flag='r', lock=lock) as shelf:
            logger.info("acquired read lock")
            time.sleep(sleep)
            self.result['val'] = shelf['key']
            logger.info("finished reading")

    def write_db(self, value, sleep=0, lock=None):
        logger.info("about to acquire write lock ({})".format(value))
        lock = self.lock if lock is None else lock
        with MutexShelf(TEST_DB, flag='c', lock=lock) as shelf:
            logger.info("acquired write lock ({})".format(value))
            time.sleep(sleep)
            shelf['key'] = value
            logger.info("finished writing ({})".format(value))

    @classmethod
    def setUpClass(cls):
        cls.lock = threading.Lock()
        cls.procLock = multiprocessing.Lock()

    def setUp(self):
        self.result = multiprocessing.Manager().dict()
        with shelve.open(TEST_DB, flag='c') as shelf:
            shelf['key'] = "test"

    def test_threaded_write(self):
        """
        Start a slow writing thread, then a fast writing thread, and ensure that
        the slow thread finishes writing before the fast thread writes.
        """
        slow_writer = threading.Thread(target=self.write_db,
                                       args=("slow", 1))
        fast_writer = threading.Thread(target=self.write_db,
                                       args=("fast",))

        self.read_db()
        self.assertEqual(self.result['val'], "test")

        slow_writer.start()
        while self.lock.acquire(blocking=False):
            self.lock.release()
        fast_writer.start()
        slow_writer.join()
        fast_writer.join()
        self.read_db()
        self.assertEqual(self.result['val'], "fast")

    def test_process_write(self):
        """
        Start a slow writing process, then a fast writing process, and ensure
        that the slow process finishes writing before the fast process writes.
        """
        slow_writer = multiprocessing.Process(target=self.write_db,
                                              kwargs={'value': "slowmutproc",
                                                      'sleep': 1, 'lock':
                                                      self.procLock})
        fast_writer = multiprocessing.Process(target=self.write_db,
                                              kwargs={'value': "fastmutproc",
                                                      'lock': self.procLock})

        self.read_db()
        self.assertEqual(self.result['val'], "test")

        slow_writer.start()
        while self.procLock.acquire(block=False):
            self.procLock.release()
        fast_writer.start()
        fast_writer.join()
        slow_writer.join()

        self.read_db()
        self.assertEqual(self.result['val'], "fastmutproc")

    def test_process_read(self):
        """
        Start a slow reader proc and then a fast writer proc; make sure the
        reader finishes reading before the writing process acquires the lock.
        """
        slow_reader = threading.Thread(target=self.read_db,
                                       kwargs={'sleep': .1, 'lock':
                                               self.procLock})
        fast_writer = threading.Thread(target=self.write_db,
                                       kwargs={'value': "fastrproc", 'lock':
                                               self.procLock})

        slow_reader.start()
        while self.procLock.acquire(block=False):
            self.procLock.release()
        fast_writer.start()
        fast_writer.join()
        slow_reader.join()

        self.assertEqual(self.result['val'], "test")

    def test_threaded_read(self):
        """
        Start a slow reader thread and then a fast writer thread; make sure the
        reader finishes reading before the writing thread acquires the lock.
        """
        slow_reader = threading.Thread(target=self.read_db, args=(.1,))
        fast_writer = threading.Thread(target=self.write_db, args=("fastr",))

        slow_reader.start()
        while self.lock.acquire(blocking=False):
            self.lock.release()
        fast_writer.start()
        fast_writer.join()
        slow_reader.join()

        self.assertEqual(self.result['val'], "test")

    def tearDown(self):
        os.remove(TEST_DB)


class TestRW(unittest.TestCase):
    def read_db(self, sleep=0):
        read = TestRW.ReadThread(sleep=sleep, result=self.result)
        read.start()
        read.join()

    class ReadThread(threading.Thread):
        def __init__(self, *args, sleep=0, result=None, **kwargs):
            super().__init__(*args, **kwargs)
            self.sleep = sleep
            self.result = result
            self.has_lock = False

        def run(self):
            logger.info("about to acquire read lock")
            with RWShelf(TEST_DB, flag='r') as shelf:
                self.has_lock = True
                logger.info("acquired read lock")
                time.sleep(self.sleep)
                self.result['val'] = shelf['key']
                logger.info("finished reading")
            self.has_lock = False

    class ReadProcess(multiprocessing.Process):
        def __init__(self, *args, sleep=0, result=None, **kwargs):
            super().__init__(*args, **kwargs)
            self.sleep = sleep
            self.result = result
            self.sync = multiprocessing.Lock()
            self.sync.acquire()

        def run(self):
            logger.info("about to acquire read lock")
            with RWShelf(TEST_DB, flag='r') as shelf:
                self.sync.release()
                logger.info("acquired read lock")
                time.sleep(self.sleep)
                self.result['val'] = shelf['key']
                logger.info("finished reading")

    class WriteThread(threading.Thread):
        def __init__(self, value, *args, sleep=0, **kwargs):
            super().__init__(*args, **kwargs)
            self.value = value
            self.sleep = sleep
            self.has_lock = False

        def run(self):
            logger.info("about to acquire write lock ({})".format(self.value))
            with RWShelf(TEST_DB, flag='c') as shelf:
                self.has_lock = True
                logger.info("acquired write lock ({})".format(self.value))
                time.sleep(self.sleep)
                shelf['key'] = self.value
                logger.info("finished writing ({})".format(self.value))
            self.has_lock = False

    class WriteProcess(multiprocessing.Process):
        def __init__(self, value, *args, sleep=0, **kwargs):
            super().__init__(*args, **kwargs)
            self.value = value
            self.sleep = sleep
            self.sync = multiprocessing.Lock()
            self.sync.acquire()

        def run(self):
            logger.info("about to acquire proc write lock ({})".format(self.value))
            with RWShelf(TEST_DB, flag='c') as shelf:
                self.sync.release()
                logger.info("acquired write lock ({})".format(self.value))
                time.sleep(self.sleep)
                shelf['key'] = self.value
                logger.info("finished writing ({})".format(self.value))

    def setUp(self):
        self.result = multiprocessing.Manager().dict()
        with shelve.open(TEST_DB, flag='c') as shelf:
            shelf['key'] = "test"

    def test_threaded_write(self):
        """
        Start a slow writing thread, then a fast writing thread, and ensure that
        the slow thread finishes writing before the fast thread writes.
        """
        slow_writer = TestRW.WriteThread("slow", sleep=1)
        fast_writer = TestRW.WriteThread("fast")

        self.read_db()
        self.assertEqual(self.result['val'], "test")

        slow_writer.start()
        while not slow_writer.has_lock:
            pass
        fast_writer.start()
        slow_writer.join()
        fast_writer.join()
        self.read_db()
        self.assertEqual(self.result['val'], "fast")

    def test_process_write(self):
        """
        Start a slow writing proc, then a fast writing proc, and ensure that the
        slow process finishes writing before the fast process writes.
        """
        slow_writer = TestRW.WriteProcess("slowproc", sleep=1)
        fast_writer = TestRW.WriteProcess("fastproc")

        self.read_db()
        self.assertEqual(self.result['val'], "test")

        slow_writer.start()
        while not slow_writer.sync.acquire(block=False):
            pass
        slow_writer.sync.release()
        fast_writer.start()
        slow_writer.join()
        fast_writer.join()
        self.read_db()
        self.assertEqual(self.result['val'], "fastproc")

    def test_process_read(self):
        """
        Start a slow reader proc and then a fast writer proc; make sure the
        reader finishes reading before the writing process acquires the lock.
        """
        slow_reader = TestRW.ReadProcess(sleep=1, result=self.result)
        fast_writer = TestRW.WriteProcess("fastrproc")

        slow_reader.start()
        while not slow_reader.sync.acquire(block=False):
            pass
        slow_reader.sync.release()
        fast_writer.start()
        fast_writer.join()
        slow_reader.join()

        self.assertEqual(self.result['val'], "test")

    def test_threaded_read(self):
        """
        Start a slow reader thread and then a fast writer thread; make sure the
        reader finishes reading before the writing thread acquires the lock.
        """
        slow_reader = TestRW.ReadThread(sleep=1, result=self.result)
        fast_writer = TestRW.WriteThread("fastrthread")

        slow_reader.start()
        while not slow_reader.has_lock:
            pass
        fast_writer.start()
        fast_writer.join()
        slow_reader.join()

        self.assertEqual(self.result['val'], "test")

    def tearDown(self):
        os.remove(TEST_DB)

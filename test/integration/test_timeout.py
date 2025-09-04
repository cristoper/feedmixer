import http.server
import socketserver
import threading
import time
import unittest

from requests.exceptions import Timeout

from feedmixer import FeedMixer

HOST = "localhost"
SLOW_DELAY = 1
FAST_TIMEOUT = 0.5

TEST_ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test Feed</title>
  <link href="http://example.org/"/>
  <updated>2025-09-03T18:30:02Z</updated>
  <author>
    <name>John Doe</name>
  </author>
  <id>urn:uuid:60a76c80-d399-11d9-b93C-0003939e0af6</id>
  <entry>
    <title>Test Entry</title>
    <link href="http://example.org/test"/>
    <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
    <updated>2025-09-03T18:30:02Z</updated>
    <summary>Some text.</summary>
  </entry>
</feed>
""".encode("utf-8")


class SlowRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        """Suppress logging."""
        pass

    def do_GET(self):
        if self.path == "/slow":
            time.sleep(SLOW_DELAY)
            try:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"slow response")
            except BrokenPipeError:
                # The client has timed out and closed the connection, which is expected.
                pass
        elif self.path == "/fast":
            time.sleep(FAST_TIMEOUT * 0.9)
            self.send_response(200)
            self.send_header("Content-type", "application/atom+xml")
            self.end_headers()
            self.wfile.write(TEST_ATOM)
        else:
            self.send_response(404)
            self.end_headers()


class TimeoutIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = socketserver.TCPServer((HOST, 0), SlowRequestHandler)
        cls.port = cls.httpd.server_address[1]
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.server_thread.join()

    def test_request_times_out(self):
        """
        Test that a slow request times out correctly.
        """
        url = f"http://{HOST}:{self.port}/slow"
        fm = FeedMixer(feeds=[url], timeout=FAST_TIMEOUT)
        # Accessing mixed_entries triggers the fetch
        self.assertEqual(len(fm.mixed_entries), 0)
        self.assertIn(url, fm.error_urls)
        self.assertIsInstance(fm.error_urls[url], Timeout)

    def test_fast_request_does_not_time_out(self):
        """
        Test that a fast request does not time out.
        """
        url = f"http://{HOST}:{self.port}/fast"
        fm = FeedMixer(feeds=[url], timeout=FAST_TIMEOUT)
        # Accessing mixed_entries triggers the fetch
        self.assertEqual(len(fm.mixed_entries), 1)
        self.assertEqual(len(fm.error_urls), 0)

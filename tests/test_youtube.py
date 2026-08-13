"""Tests for YouTube RSS fetching and parsing."""

import io
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import feedparser
import requests

from cunradar.collectors.youtube import YouTubeCollector


REAL_FEEDPARSER_PARSE = feedparser.parse
CHANNEL_ID = "UCgv3xMy6kECn0boYP9d2o-g"
FEED_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
VALID_ATOM = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015"
      xmlns:media="http://search.yahoo.com/mrss/"
      xmlns="http://www.w3.org/2005/Atom">
  <title>Cloudflare</title>
  <entry>
    <id>yt:video:video123</id>
    <yt:videoId>video123</yt:videoId>
    <title>Test video</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=video123"/>
    <published>2026-08-14T01:02:03+00:00</published>
    <media:group><media:description>Test description</media:description></media:group>
  </entry>
</feed>
"""


class YouTubeCollectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.collector = YouTubeCollector(
            [{"name": "Cloudflare", "channel_id": CHANNEL_ID}]
        )

    @staticmethod
    def response(content: bytes = VALID_ATOM, status: int = 200) -> Mock:
        response = Mock()
        response.content = content
        response.headers = {"Content-Type": "application/atom+xml; charset=UTF-8"}
        if status >= 400:
            response.raise_for_status.side_effect = requests.HTTPError(
                f"{status} error", response=Mock(status_code=status)
            )
        else:
            response.raise_for_status.return_value = None
        return response

    @patch("cunradar.collectors.youtube.requests.get")
    def test_valid_atom_uses_expected_url_headers_and_timeout(self, get: Mock) -> None:
        get.return_value = self.response()

        items = self.collector.collect()

        self.assertEqual(len(items), 1)
        get.assert_called_once()
        args, kwargs = get.call_args
        self.assertEqual(args[0], FEED_URL)
        self.assertEqual(kwargs["timeout"], 15)
        self.assertIn("Mozilla/5.0", kwargs["headers"]["User-Agent"])
        self.assertIn("zh-CN", kwargs["headers"]["Accept-Language"])
        self.assertEqual(
            kwargs["headers"]["Accept"],
            "application/atom+xml, application/xml, text/xml",
        )

    @patch("cunradar.collectors.youtube.requests.get")
    def test_video_id_and_published_are_converted(self, get: Mock) -> None:
        get.return_value = self.response()

        item = self.collector.collect()[0]

        self.assertEqual(item.item_id, "yt:video123")
        self.assertEqual(item.url, "https://www.youtube.com/watch?v=video123")
        self.assertEqual(item.title, "Test video")
        self.assertEqual(item.description, "Test description")
        self.assertEqual(item.published, datetime(2026, 8, 14, 1, 2, 3, tzinfo=timezone.utc))
        self.assertEqual(item.extra["channel_id"], CHANNEL_ID)

    def assert_http_error_returns_empty(self, status: int) -> None:
        with patch("cunradar.collectors.youtube.requests.get") as get:
            get.return_value = self.response(status=status)
            output = io.StringIO()
            with redirect_stdout(output):
                items = self.collector.collect()
        self.assertEqual(items, [])
        self.assertIn("Failed to fetch 'Cloudflare': HTTPError", output.getvalue())

    def test_http_403_returns_empty(self) -> None:
        self.assert_http_error_returns_empty(403)

    def test_http_429_returns_empty(self) -> None:
        self.assert_http_error_returns_empty(429)

    def test_http_500_returns_empty(self) -> None:
        self.assert_http_error_returns_empty(500)

    @patch("cunradar.collectors.youtube.requests.get")
    def test_timeout_returns_empty(self, get: Mock) -> None:
        get.side_effect = requests.Timeout("request timed out")
        output = io.StringIO()

        with redirect_stdout(output):
            items = self.collector.collect()

        self.assertEqual(items, [])
        self.assertIn("Timeout: request timed out", output.getvalue())

    @patch("cunradar.collectors.youtube.requests.get")
    def test_connection_error_returns_empty(self, get: Mock) -> None:
        get.side_effect = requests.ConnectionError("DNS lookup failed")
        output = io.StringIO()

        with redirect_stdout(output):
            items = self.collector.collect()

        self.assertEqual(items, [])
        self.assertIn("ConnectionError: DNS lookup failed", output.getvalue())

    @patch("cunradar.collectors.youtube.requests.get")
    def test_html_response_reports_bozo_exception(self, get: Mock) -> None:
        get.return_value = self.response(b"<html><body>not a feed</body></html>")
        get.return_value.headers = {"Content-Type": "text/html; charset=UTF-8"}
        output = io.StringIO()

        with redirect_stdout(output):
            items = self.collector.collect()

        self.assertEqual(items, [])
        self.assertIn("unexpected Content-Type text/html", output.getvalue())
        self.assertNotIn("<html>", output.getvalue())

    @patch("cunradar.collectors.youtube.requests.get")
    def test_truncated_xml_reports_bozo_exception(self, get: Mock) -> None:
        get.return_value = self.response(
            b'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry>'
        )
        output = io.StringIO()

        with redirect_stdout(output):
            items = self.collector.collect()

        self.assertEqual(items, [])
        self.assertIn("SAXParseException", output.getvalue())
        self.assertIn("Skipping incomplete entry", output.getvalue())

    @patch("cunradar.collectors.youtube.feedparser.parse")
    @patch("cunradar.collectors.youtube.requests.get")
    def test_bozo_feed_with_entries_keeps_valid_entries(self, get: Mock, parse: Mock) -> None:
        get.return_value = self.response()
        parsed = REAL_FEEDPARSER_PARSE(VALID_ATOM)
        parsed.bozo = True
        parsed.bozo_exception = ValueError("trailing malformed data")
        parse.return_value = parsed

        items = self.collector.collect()

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].item_id, "yt:video123")


if __name__ == "__main__":
    unittest.main()

"""Security tests for public HTML report generation."""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from cunradar.collectors.base import CollectedItem
from cunradar.report import generate_html


class ReportSecurityTests(unittest.TestCase):
    def render(
        self,
        *,
        title: str = "Safe title",
        url: str = "https://example.com/item",
        description: str = "Safe description",
        source_name: str = "Safe source",
        digest: str = "",
    ) -> str:
        item = CollectedItem(
            source="rss",
            source_name=source_name,
            item_id="test-item",
            title=title,
            url=url,
            published=datetime(2026, 8, 13, tzinfo=timezone.utc),
            description=description,
        )
        with tempfile.TemporaryDirectory() as output_dir:
            path = generate_html(
                items=[item],
                digest=digest,
                date_str="2026-08-13",
                output_dir=output_dir,
                configured_sources=["rss"],
                now=datetime(2026, 8, 13, 19, 0, tzinfo=timezone.utc),
            )
            return Path(path).read_text(encoding="utf-8")

    def test_script_in_title_is_escaped(self) -> None:
        page = self.render(title="<script>alert(1)</script>")
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertNotIn("<script>alert(1)</script>", page)

    def test_attribute_in_title_is_escaped(self) -> None:
        page = self.render(title='title\" onmouseover=\"alert(1)')
        self.assertIn("title&quot; onmouseover=&quot;alert(1)", page)
        self.assertNotIn('onmouseover="alert(1)', page)

    def test_html_in_description_is_escaped(self) -> None:
        page = self.render(description='<img src=x onerror="alert(1)">')
        self.assertIn("&lt;img src=x onerror=&quot;alert(1)&quot;&gt;", page)
        self.assertNotIn("<img src=x", page)

    def test_description_is_truncated_before_escaping(self) -> None:
        page = self.render(description=("a" * 299) + "<script>")
        self.assertIn(("a" * 299) + "&lt;", page)
        self.assertNotIn("&lt;script", page)

    def test_admin_source_name_is_escaped(self) -> None:
        page = self.render(source_name="</div><script>alert(1)</script>")
        self.assertIn("&lt;/div&gt;&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertNotIn("<script>alert(1)</script>", page)

    def test_href_attribute_injection_is_escaped(self) -> None:
        page = self.render(url='https://example.com/\" onmouseover=\"alert(1)')
        self.assertIn(
            'href="https://example.com/&quot; onmouseover=&quot;alert(1)"', page
        )
        self.assertNotIn('href="https://example.com/" onmouseover=', page)

    def test_javascript_url_is_not_linked(self) -> None:
        page = self.render(url="javascript:alert(1)")
        self.assertNotIn('<a class="item-title"', page)
        self.assertIn('<span class="item-title">Safe title</span>', page)

    def test_data_url_is_not_linked(self) -> None:
        page = self.render(url="data:text/html,<script>alert(1)</script>")
        self.assertNotIn('<a class="item-title"', page)
        self.assertIn('<span class="item-title">Safe title</span>', page)

    def test_url_with_control_character_is_not_linked(self) -> None:
        page = self.render(url="https://example.com/path\nother")
        self.assertNotIn('<a class="item-title"', page)

    def test_valid_https_url_is_linked(self) -> None:
        page = self.render(url="https://example.com/path?q=value")
        self.assertIn('href="https://example.com/path?q=value"', page)

    def test_url_query_characters_are_attribute_escaped(self) -> None:
        page = self.render(url="https://example.com/?a=1&b='quoted'")
        self.assertIn(
            'href="https://example.com/?a=1&amp;b=&#x27;quoted&#x27;"', page
        )

    def test_raw_html_in_digest_is_escaped(self) -> None:
        page = self.render(digest="<script>alert(1)</script>")
        self.assertIn("<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>", page)
        self.assertNotIn("<script>alert(1)</script>", page)

    def test_attribute_injection_in_digest_is_escaped(self) -> None:
        page = self.render(digest='<img src=x onerror="alert(1)">')
        self.assertIn(
            "<p>&lt;img src=x onerror=&quot;alert(1)&quot;&gt;</p>", page
        )
        self.assertNotIn("<img src=x", page)

    def test_safe_digest_subset_is_rendered(self) -> None:
        page = self.render(digest="# Heading\n- **Bold item**\nParagraph")
        self.assertIn("<h1>Heading</h1>", page)
        self.assertIn("<li><strong>Bold item</strong></li>", page)
        self.assertIn("<p>Paragraph</p>", page)

    def test_markdown_link_and_image_are_not_activated(self) -> None:
        page = self.render(
            digest="[link](javascript:alert(1))\n![image](https://example.com/x.png)"
        )
        self.assertIn("<p>[link](javascript:alert(1))</p>", page)
        self.assertIn("<p>![image](https://example.com/x.png)</p>", page)
        self.assertNotIn('<a href="javascript:', page)
        self.assertNotIn("<img", page)


if __name__ == "__main__":
    unittest.main()

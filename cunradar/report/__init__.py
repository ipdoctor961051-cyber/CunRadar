"""HTML daily report generator."""

import html
import re
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from ..collectors.base import CollectedItem

_TEMPLATE_PATH = Path(__file__).resolve().parent / "template.html"
_PUBLIC_DIR = Path(__file__).resolve().parent.parent.parent / "public"

# All possible sources with their metadata
_SOURCES = {
    "youtube": ("YouTube", "🎬"),
    "bilibili": ("B站", "📺"),
    "rss": ("博客 & RSS", "📝"),
    "github": ("GitHub 项目", "💻"),
    "github_trending": ("GitHub Trending", "🔥"),
}


def _safe_http_url(value: str) -> str | None:
    """Return an escaped HTTP(S) URL suitable for an href attribute."""
    url = value.strip()
    if not url or any(ord(char) < 32 or ord(char) == 127 for char in url):
        return None
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not hostname:
        return None
    return html.escape(url, quote=True)


def _render_inline_markdown(value: str) -> str:
    """Escape text, then render only the supported bold Markdown syntax."""
    escaped = html.escape(value, quote=True)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)


def _render_digest(digest: str) -> str:
    """Render a safe subset of Markdown without accepting raw HTML."""
    rendered: list[str] = []
    for raw_line in digest.strip().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            rendered.append(
                f"<h{level}>{_render_inline_markdown(heading_match.group(2))}</h{level}>"
            )
        elif line.startswith(("- ", "* ")):
            rendered.append(f"<li>{_render_inline_markdown(line[2:])}</li>")
        else:
            rendered.append(f"<p>{_render_inline_markdown(line)}</p>")
    return f'<div class="digest">{"".join(rendered)}</div>' if rendered else ""


def _build_section(title: str, icon: str, items: list[CollectedItem]) -> str:
    """Build an HTML section with items or an empty-state message."""
    if not items:
        return f"""<div class="section">
    <h2>{icon} {title}</h2>
    <div class="empty-state">无新内容</div>
</div>"""

    rows = "\n".join(_build_row(item) for item in items)

    return f"""<div class="section">
    <h2>{icon} {title} <span class="count">{len(items)}</span></h2>
    <div class="items">{rows}</div>
</div>"""


def _build_row(item: CollectedItem) -> str:
    published = ""
    if item.published:
        published = f'<span class="time">{item.published.strftime("%Y-%m-%d %H:%M")}</span>'

    title = html.escape(item.title, quote=True)
    source_name = html.escape(item.source_name, quote=True)
    description = html.escape(item.description[:300], quote=True)
    desc = f'<p class="desc">{description}</p>' if item.description else ""
    safe_url = _safe_http_url(item.url)
    title_html = (
        f'<a class="item-title" href="{safe_url}" target="_blank" rel="noopener">'
        f"{title}</a>"
        if safe_url
        else f'<span class="item-title">{title}</span>'
    )

    return f"""<div class="item">
    <div class="item-header">
        {title_html}
        {published}
    </div>
    <div class="meta">{source_name}</div>
    {desc}
</div>"""


def generate_html(
    items: list[CollectedItem],
    digest: str,
    date_str: str,
    output_dir: str,
    configured_sources: list[str] | None = None,
    now: datetime | None = None,
) -> str:
    """Generate the daily HTML report.

    Args:
        items: All collected new items.
        digest: AI-generated markdown digest.
        date_str: Date string (e.g. ``2026-07-28``).
        output_dir: Output directory.
        configured_sources: Source types the user has configured.
            If provided, empty sections will be rendered as "无新内容".
            If None, empty sections are omitted.
        now: Timezone-aware datetime for timestamps. Defaults to local now.

    Returns:
        Path to the generated HTML file.
    """
    out = Path(output_dir) / date_str
    out.mkdir(parents=True, exist_ok=True)

    # Group items by source
    grouped: dict[str, list[CollectedItem]] = {}
    for item in items:
        grouped.setdefault(item.source, []).append(item)

    # Determine which sources to render
    if configured_sources:
        render_keys = configured_sources
    else:
        render_keys = [k for k in _SOURCES if k in grouped]

    section_html = ""
    total_sections = 0
    for key in render_keys:
        info = _SOURCES.get(key)
        if not info:
            continue
        title, icon = info
        section_html += _build_section(title, icon, grouped.get(key, []))
        if key in grouped:
            total_sections += 1

    digest_html = _render_digest(digest) if digest else ""

    # Read template
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")

    summary_items = sum(len(v) for v in grouped.values())

    html = template.replace("{{TITLE}}", f"CunRadar Daily - {date_str}")
    if now is None:
        now = datetime.now()
    display_datetime = f"{date_str}  {now.strftime('%H:%M')}"
    html = html.replace("{{DATE}}", display_datetime)
    html = html.replace("{{SUMMARY_ITEMS}}", str(summary_items))
    html = html.replace("{{SUMMARY_SOURCES}}", str(total_sections))
    html = html.replace("{{SECTIONS}}", section_html)
    html = html.replace("{{DIGEST}}", digest_html)
    html = html.replace("{{GENERATED_AT}}", now.strftime("%Y-%m-%d %H:%M:%S"))

    html_path = str(out / "index.html")
    Path(html_path).write_text(html, encoding="utf-8")

    # Copy public assets (favicon, logo, robots.txt) to both date dir and root
    if _PUBLIC_DIR.exists():
        for asset in ["favicon.ico", "logo.png", "robots.txt"]:
            src = _PUBLIC_DIR / asset
            if src.exists():
                shutil.copy2(src, out / asset)
                shutil.copy2(src, Path(output_dir) / asset)

    # Also write index.html in output root for easy access
    root_index = Path(output_dir) / "index.html"
    root_index.write_text(html, encoding="utf-8")

    print(f"\n  [Report] HTML saved to: {html_path}")
    print(f"  [Report] Root index: {root_index}")
    return html_path

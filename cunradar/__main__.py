"""CunRadar main entry point.

Orchestrates the full daily pipeline:
  1. Load config
  2. Run all collectors
  3. Filter by time window + deduplicate against SQLite
  4. Generate AI digest
  5. Generate HTML report
  6. Push to Telegram
"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import load_config
from .collectors.base import CollectedItem
from .collectors.youtube import YouTubeCollector
from .collectors.bilibili import BilibiliCollector
from .collectors.rss import RSSCollector
from .collectors.github import GitHubTrendingCollector, GitHubRepoCollector
from .storage import Storage
from .ai import AIRequestError, generate_digest
from .report import generate_html
from .notification import send_digest


def _filter_by_age(
    items: list[CollectedItem],
    max_hours: int,
    now: datetime,
) -> list[CollectedItem]:
    """Keep only items published within the last ``max_hours``."""
    if max_hours <= 0:
        return items
    # Convert cutoff to UTC for comparison (all published dates are UTC)
    cutoff_utc = now.astimezone(timezone.utc) - timedelta(hours=max_hours)
    filtered: list[CollectedItem] = []
    for it in items:
        if it.published is None:
            continue
        pub = it.published
        # Make offset-naive datestamps offset-aware (assume UTC)
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        if pub >= cutoff_utc:
            filtered.append(it)
    dropped = len(items) - len(filtered)
    if dropped:
        print(f"  [Age filter] dropped {dropped} items older than {max_hours}h")
    return filtered


def _run_collector(
    name: str,
    collector,
    storage: Storage,
    max_hours: int,
    now: datetime,
    enable_fallback: bool = False,
) -> list[CollectedItem]:
    """Run a collector, filter by time, then deduplicate.

    If ``enable_fallback`` is True **and** no new items are found in the
    time window, the single latest item from the raw feed is included as a
    baseline entry (and marked as seen in the DB).  This ensures the DB
    has a record for first runs and long-idle sources.
    """
    print(f"\n[{name}] Collecting...")
    try:
        raw = collector.collect()
    except Exception as e:
        print(f"  [{name}] Collector error: {e}")
        return []

    # 1. Time window filter
    aged = _filter_by_age(raw, max_hours, now)

    # 1.5. For snapshot sources (trending), clear old entries before dedup
    #     so a fresh daily snapshot is always recorded.
    if not enable_fallback and aged:
        for item in aged:
            storage.delete_source(item.source, item.item_id)

    # 2. Dedup
    new_items: list[CollectedItem] = []
    for item in aged:
        if storage.is_new(item.item_id):
            new_items.append(item)
            storage.mark_seen(
                item.item_id, item.source,
                item.source_name, item.title, item.url,
            )

    # 3. Fallback: if nothing new in window, take the latest item as baseline
    if not new_items and enable_fallback and raw:
        print(f"  [{name}] Fallback: {len(raw)} raw items available")
        # Try to sort by published date first
        with_date = [it for it in raw if it.published is not None]
        print(f"  [{name}] Fallback: {len(with_date)} items have published dates")
        if with_date:
            with_date.sort(key=lambda x: x.published, reverse=True)
            fallback = with_date[0]
            print(f"  [{name}] Fallback picked (by date): {fallback.title} ({fallback.published})")
        else:
            # No items have dates — just take the first one
            fallback = raw[0]
            print(f"  [{name}] Fallback picked (first raw): {fallback.title}")
        print(f"  [{name}] Fallback item_id: {fallback.item_id}, source: {fallback.source}")
        storage.mark_seen(
            fallback.item_id, fallback.source,
            fallback.source_name, fallback.title, fallback.url,
        )
        new_items.append(fallback)

    print(f"  [{name}] {len(new_items)} new out of {len(raw)} total ({len(aged)} in time window)")
    return new_items


def main() -> None:
    """Run the full CunRadar pipeline."""
    print("=" * 50)
    print("  📡 CunRadar - Personal Information Radar")
    print("=" * 50)

    # ── 1. Load config ──
    config_path = os.environ.get("CONFIG_PATH")
    config = load_config(config_path)

    app_cfg = config.get("app", {})
    timezone_name = app_cfg.get("timezone", "Asia/Shanghai")
    max_item_age_hours = app_cfg.get("max_item_age_hours", 24)
    follow = config.get("follow", {})
    ai_cfg = config.get("ai", {})
    notify_cfg = config.get("notification", {})
    output_cfg = config.get("output", {})

    try:
        import pytz
        now = datetime.now(pytz.timezone(timezone_name))
    except ImportError:
        now = datetime.now()
    except Exception:
        now = datetime.now()

    date_str = now.strftime("%Y-%m-%d")
    print(f"\n  Date: {date_str}")
    print(f"  Timezone: {timezone_name}")
    print(f"  Max item age: {max_item_age_hours}h")

    # ── 2. Storage ──
    output_dir = output_cfg.get("dir", "output")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    db_path = os.path.join(output_dir, "cunradar.db")
    storage = Storage(db_path)

    # ── 3. Run collectors ──
    all_new_items: list[CollectedItem] = []

    # YouTube
    yt_channels = follow.get("youtube", [])
    if yt_channels:
        all_new_items.extend(
            _run_collector("YouTube", YouTubeCollector(yt_channels), storage, max_item_age_hours, now, enable_fallback=True)
        )
    else:
        print("\n  [YouTube] Skipped (no channels configured)")

    # Bilibili
    bili_creators = follow.get("bilibili", [])
    if bili_creators:
        all_new_items.extend(
            _run_collector("Bilibili", BilibiliCollector(bili_creators), storage, max_item_age_hours, now, enable_fallback=True)
        )
    else:
        print("\n  [Bilibili] Skipped (no creators configured)")

    # RSS
    rss_feeds = follow.get("rss", [])
    if rss_feeds:
        all_new_items.extend(
            _run_collector("RSS", RSSCollector(rss_feeds), storage, max_item_age_hours, now, enable_fallback=True)
        )
    else:
        print("\n  [RSS] Skipped (no feeds configured)")

    # GitHub repos
    gh_repos = follow.get("github", [])
    if gh_repos:
        gh_token = os.environ.get("GITHUB_TOKEN", "")
        all_new_items.extend(
            _run_collector(
                "GitHub",
                GitHubRepoCollector(gh_repos, token=gh_token),
                storage,
                max_item_age_hours,
                now,
                enable_fallback=True,
            )
        )
    else:
        print("\n  [GitHub] Skipped (no repos configured)")

    # GitHub Trending
    gh_trending_cfg = follow.get("github_trending", {})
    if gh_trending_cfg.get("enabled", False):
        all_new_items.extend(
            _run_collector(
                "GitHub Trending",
                GitHubTrendingCollector(
                    language=gh_trending_cfg.get("language", ""),
                    limit=gh_trending_cfg.get("limit", 15),
                ),
                storage,
                max_item_age_hours,
                now,
            )
        )
    else:
        print("\n  [GitHub Trending] Skipped (disabled)")

    # ── 4. Summary ──
    print(f"\n{'=' * 50}")
    print(f"  Total new items (in time window): {len(all_new_items)}")
    if not all_new_items:
        print("  No new content today.")

    # ── 5. Compute configured sources for report ──
    configured_sources: list[str] = []
    if follow.get("youtube"):
        configured_sources.append("youtube")
    if follow.get("bilibili"):
        configured_sources.append("bilibili")
    if follow.get("rss"):
        configured_sources.append("rss")
    if follow.get("github"):
        configured_sources.append("github")
    if follow.get("github_trending", {}).get("enabled"):
        configured_sources.append("github_trending")

    # ── 6. Generate AI digest ──
    digest = ""
    if all_new_items:
        print("\n[AI] Generating daily digest...")
        try:
            digest = generate_digest(
                items=all_new_items,
                date_str=date_str,
                config=ai_cfg,
            )
        except AIRequestError as exc:
            print(f"  [AI] Recoverable provider error: {exc}")
            print("  [AI] Continuing report generation without an AI digest")
    else:
        print("\n[AI] Skipped (no new items to summarize)")

    # ── 6. Generate HTML report ──
    html_path = None
    if output_cfg.get("html", True) and (all_new_items or configured_sources):
        print("\n[Report] Generating HTML...")
        html_path = generate_html(
            items=all_new_items,
            digest=digest,
            date_str=date_str,
            output_dir=output_dir,
            configured_sources=configured_sources,
            now=now,
        )
        storage.save_report(date_str, html_path)
    else:
        print("\n[Report] Skipped (HTML disabled or no new items)")

    # ── 7. Telegram notification ──
    tg_cfg = notify_cfg.get("telegram", {})
    if tg_cfg.get("bot_token") and tg_cfg.get("chat_id"):
        print("\n[Telegram] Sending digest...")
        html_url = None
        if os.environ.get("CUNRADAR_PUBLIC_URL"):
            html_url = f"{os.environ['CUNRADAR_PUBLIC_URL']}/{date_str}/"
        display_datetime = now.strftime("%Y-%m-%d  %H:%M")
        send_digest(
            bot_token=tg_cfg["bot_token"],
            chat_id=tg_cfg["chat_id"],
            date_str=display_datetime,
            items=all_new_items,
            digest=digest,
            html_url=html_url,
            configured_sources=configured_sources,
        )
    else:
        print("\n[Telegram] Skipped (bot_token or chat_id not configured)")

    # ── 8. Cleanup ──
    storage.close()

    print(f"\n{'=' * 50}")
    print("  ✅ Done")
    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    main()

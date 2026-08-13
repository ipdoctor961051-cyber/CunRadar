"""Provider-neutral AI daily digest generation."""

import os
from collections.abc import Mapping

from ..collectors.base import CollectedItem
from .base import AIConfigurationError, AIProvider, AIRequestError
from .cloudflare import CloudflareProvider, DEFAULT_MODEL as CLOUDFLARE_DEFAULT_MODEL
from .deepseek import DeepSeekProvider, DEFAULT_MODEL as DEEPSEEK_DEFAULT_MODEL


AI_SYSTEM_PROMPT = """You are CunRadar's AI digest writer. Your job is to take today's
collection of updates from various sources and produce a concise,
well-organized daily digest in Chinese.

Rules:
1. Group related items by topic when possible.
2. Keep each item description to 1-2 sentences.
3. Focus on WHAT changed and WHY it matters.
4. If an item is from GitHub, note the repo name.
5. If an item is a video, note the creator name.
6. Output in MARKDOWN format with clear section headers.
7. Be factual and concise - no fluff or marketing language.
8. Total output should be 200-500 characters.
9. If there are very few updates (0-3 items), still write a short digest."""


def build_user_prompt(items: list[CollectedItem], date_str: str) -> str:
    """Build the user prompt from collected items."""
    lines = [f"Today's date: {date_str}", "", "Updates collected today:"]
    for i, item in enumerate(items, 1):
        source_tag = item.source.upper()
        published = item.published.strftime("%H:%M UTC") if item.published else "unknown time"
        lines.append(f"{i}. [{source_tag}] {item.title}")
        lines.append(f"   From: {item.source_name} | {published}")
        if item.description:
            lines.append(f"   {item.description[:200].replace(chr(10), ' ')}")
        lines.append("")
    return "\n".join(lines)


def create_provider(
    config: Mapping[str, object] | None = None,
    environ: Mapping[str, str] | None = None,
) -> AIProvider:
    """Create the configured provider without exposing credentials in logs."""
    config = {} if config is None else config
    environ = os.environ if environ is None else environ
    explicit_provider = str(environ.get("AI_PROVIDER") or config.get("provider") or "").strip().lower()

    if explicit_provider:
        provider_name = explicit_provider
    elif environ.get("DEEPSEEK_API_KEY"):
        provider_name = "deepseek"
    elif environ.get("CLOUDFLARE_ACCOUNT_ID") and environ.get("CLOUDFLARE_AI_TOKEN"):
        provider_name = "cloudflare"
    else:
        raise AIConfigurationError(
            "AI provider is not configured; set AI_PROVIDER and its required credentials"
        )

    if provider_name == "cloudflare":
        account_id = environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
        token = environ.get("CLOUDFLARE_AI_TOKEN", "").strip()
        if not account_id:
            raise AIConfigurationError(
                "Cloudflare AI selected but CLOUDFLARE_ACCOUNT_ID is missing"
            )
        if not token:
            raise AIConfigurationError(
                "Cloudflare AI selected but CLOUDFLARE_AI_TOKEN is missing"
            )
        model = str(environ.get("AI_MODEL") or config.get("model") or CLOUDFLARE_DEFAULT_MODEL)
        return CloudflareProvider(account_id=account_id, api_token=token, model=model)

    if provider_name == "deepseek":
        api_key = environ.get("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise AIConfigurationError("DeepSeek selected but DEEPSEEK_API_KEY is missing")
        model = str(
            environ.get("DEEPSEEK_MODEL")
            or environ.get("AI_MODEL")
            or config.get("model")
            or DEEPSEEK_DEFAULT_MODEL
        )
        api_base = str(config.get("api_base") or "https://api.deepseek.com")
        return DeepSeekProvider(api_key=api_key, model=model, api_base=api_base)

    raise AIConfigurationError(f"Unsupported AI_PROVIDER: {provider_name}")


def generate_digest(
    items: list[CollectedItem],
    date_str: str,
    config: Mapping[str, object] | None = None,
    provider: AIProvider | None = None,
) -> str:
    """Generate a digest through the selected provider.

    Configuration errors and request errors are deliberately raised so the
    caller can distinguish a broken setup from a recoverable provider outage.
    """
    if not items:
        return "今日无新内容。"

    provider = provider or create_provider(config)
    timeout = int((config or {}).get("timeout", 120))
    print(f"  [AI Digest] Provider: {provider.name}")
    print(f"  [AI Digest] Model: {provider.model}")
    content = provider.complete(
        [
            {"role": "system", "content": AI_SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(items, date_str)},
        ],
        timeout,
    )
    print(f"  [AI Digest] Generated successfully ({len(content)} chars)")
    return content


__all__ = [
    "AIConfigurationError",
    "AIRequestError",
    "build_user_prompt",
    "create_provider",
    "generate_digest",
]

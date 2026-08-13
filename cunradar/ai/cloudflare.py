"""Cloudflare Workers AI provider."""

from .openai_compatible import OpenAICompatibleProvider


DEFAULT_MODEL = "@cf/meta/llama-3.2-3b-instruct"


class CloudflareProvider(OpenAICompatibleProvider):
    def __init__(self, *, account_id: str, api_token: str, model: str) -> None:
        super().__init__(
            name="cloudflare",
            model=model,
            api_key=api_token,
            endpoint=(
                "https://api.cloudflare.com/client/v4/accounts/"
                f"{account_id}/ai/v1/chat/completions"
            ),
        )

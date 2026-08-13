"""DeepSeek provider retained for backward compatibility."""

from .openai_compatible import OpenAICompatibleProvider


DEFAULT_MODEL = "deepseek-chat"


class DeepSeekProvider(OpenAICompatibleProvider):
    def __init__(self, *, api_key: str, model: str, api_base: str) -> None:
        super().__init__(
            name="deepseek",
            model=model,
            api_key=api_key,
            endpoint=f"{api_base.rstrip('/')}/v1/chat/completions",
        )

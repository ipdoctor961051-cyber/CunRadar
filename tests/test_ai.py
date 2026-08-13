"""Tests for AI provider selection and failure semantics."""

import unittest
from unittest.mock import Mock, patch

from cunradar.ai import AIConfigurationError, AIRequestError, create_provider
from cunradar.ai.cloudflare import CloudflareProvider
from cunradar.ai.deepseek import DeepSeekProvider


class ProviderSelectionTests(unittest.TestCase):
    def test_cloudflare_provider_is_selected(self) -> None:
        provider = create_provider(
            environ={
                "AI_PROVIDER": "cloudflare",
                "CLOUDFLARE_ACCOUNT_ID": "account-id",
                "CLOUDFLARE_AI_TOKEN": "token",
                "AI_MODEL": "@cf/test/model",
            }
        )
        self.assertIsInstance(provider, CloudflareProvider)
        self.assertEqual(provider.model, "@cf/test/model")

    def test_cloudflare_missing_token_fails_configuration(self) -> None:
        with self.assertRaisesRegex(
            AIConfigurationError, "CLOUDFLARE_AI_TOKEN is missing"
        ):
            create_provider(
                environ={
                    "AI_PROVIDER": "cloudflare",
                    "CLOUDFLARE_ACCOUNT_ID": "account-id",
                }
            )

    def test_cloudflare_missing_account_id_fails_configuration(self) -> None:
        with self.assertRaisesRegex(
            AIConfigurationError, "CLOUDFLARE_ACCOUNT_ID is missing"
        ):
            create_provider(
                environ={
                    "AI_PROVIDER": "cloudflare",
                    "CLOUDFLARE_AI_TOKEN": "token",
                }
            )

    def test_deepseek_remains_supported(self) -> None:
        provider = create_provider(
            environ={
                "AI_PROVIDER": "deepseek",
                "DEEPSEEK_API_KEY": "key",
            }
        )
        self.assertIsInstance(provider, DeepSeekProvider)
        self.assertEqual(provider.model, "deepseek-chat")

    def test_existing_deepseek_key_selects_deepseek_without_ai_provider(self) -> None:
        provider = create_provider(environ={"DEEPSEEK_API_KEY": "key"})
        self.assertIsInstance(provider, DeepSeekProvider)

    def test_unknown_provider_fails_configuration(self) -> None:
        with self.assertRaisesRegex(AIConfigurationError, "Unsupported AI_PROVIDER"):
            create_provider(environ={"AI_PROVIDER": "unknown"})


class ProviderRequestTests(unittest.TestCase):
    @patch("cunradar.ai.openai_compatible.requests.post")
    def test_provider_returns_chat_completion(self, post: Mock) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [{"message": {"content": "测试成功"}}]
        }
        post.return_value = response
        provider = CloudflareProvider(
            account_id="account-id", api_token="token", model="@cf/test/model"
        )

        result = provider.complete([{"role": "user", "content": "test"}], 10)

        self.assertEqual(result, "测试成功")
        request_headers = post.call_args.kwargs["headers"]
        self.assertEqual(request_headers["Authorization"], "Bearer token")

    @patch("cunradar.ai.openai_compatible.requests.post")
    def test_invalid_response_is_a_request_error(self, post: Mock) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"unexpected": True}
        post.return_value = response
        provider = CloudflareProvider(
            account_id="account-id", api_token="token", model="@cf/test/model"
        )

        with self.assertRaisesRegex(AIRequestError, "invalid response"):
            provider.complete([{"role": "user", "content": "test"}], 10)

    @patch("cunradar.ai.openai_compatible.requests.post")
    def test_http_failure_is_a_request_error_without_response_body(self, post: Mock) -> None:
        import requests

        response = Mock(status_code=401)
        post.side_effect = requests.HTTPError(response=response)
        provider = CloudflareProvider(
            account_id="account-id", api_token="token", model="@cf/test/model"
        )

        with self.assertRaisesRegex(AIRequestError, "HTTP 401"):
            provider.complete([{"role": "user", "content": "test"}], 10)


if __name__ == "__main__":
    unittest.main()

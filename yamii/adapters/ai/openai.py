"""
OpenAI AIアダプター
OpenAI API (GPT-4.1等) への接続実装
"""

import aiohttp
from typing import Optional

from ...domain.ports.ai_port import IAIProvider


class OpenAIAdapter(IAIProvider):
    """
    OpenAI AIアダプター

    OpenAI APIを使用してAI応答を生成。
    GPT-4.1をデフォルトモデルとして使用。
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4.1",
        timeout: int = 60,
        base_url: str = "https://api.openai.com/v1",
    ):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.base_url = base_url

    async def generate(
        self,
        message: str,
        system_prompt: str,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        AI応答を生成

        Args:
            message: ユーザーメッセージ
            system_prompt: システムプロンプト
            max_tokens: 最大トークン数（オプション）

        Returns:
            str: AI応答テキスト

        Raises:
            Exception: API呼び出し失敗時
        """
        request_body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
        }

        if max_tokens:
            request_body["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=request_body,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"OpenAI API error: HTTP {response.status} - {error_text}"
                    )

                response_data = await response.json()

                if "choices" not in response_data or not response_data["choices"]:
                    raise Exception("No choices in OpenAI response")

                choice = response_data["choices"][0]
                if "message" not in choice or "content" not in choice["message"]:
                    raise Exception("Invalid response structure from OpenAI API")

                response_text = choice["message"]["content"]

                if not response_text or not response_text.strip():
                    raise Exception("Empty response from OpenAI API")

                return response_text

    async def health_check(self) -> bool:
        """
        OpenAI APIの健全性チェック

        Returns:
            bool: 正常に動作しているか
        """
        try:
            response = await self.generate(
                message="Hello",
                system_prompt="Reply with 'OK' only.",
                max_tokens=10,
            )
            return len(response) > 0
        except Exception:
            return False

    @property
    def model_name(self) -> str:
        """使用中のモデル名"""
        return self.model


class OpenAIAdapterWithFallback(OpenAIAdapter):
    """
    フォールバック付きOpenAIアダプター

    API呼び出し失敗時にフォールバック応答を返す。
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4.1",
        timeout: int = 60,
        base_url: str = "https://api.openai.com/v1",
        fallback_message: str = "申し訳ありません。今少し調子が悪いようです。",
    ):
        super().__init__(api_key, model, timeout, base_url)
        self.fallback_message = fallback_message

    async def generate(
        self,
        message: str,
        system_prompt: str,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        AI応答を生成（フォールバック付き）
        """
        try:
            return await super().generate(message, system_prompt, max_tokens)
        except Exception:
            return self.fallback_message

"""
Gemini AIアダプター
Google Gemini APIへの接続実装
"""

import aiohttp
from typing import Optional

from ...domain.ports.ai_port import IAIProvider


class GeminiAdapter(IAIProvider):
    """
    Gemini AIアダプター

    Google Gemini APIを使用してAI応答を生成。
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash-exp",
        timeout: int = 30,
    ):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.api_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )

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
            "contents": [{
                "role": "user",
                "parts": [{"text": message}]
            }],
            "systemInstruction": {
                "role": "system",
                "parts": [{"text": system_prompt}]
            }
        }

        if max_tokens:
            request_body["generationConfig"] = {
                "maxOutputTokens": max_tokens
            }

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                self.api_url,
                params={"key": self.api_key},
                json=request_body,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Gemini API error: HTTP {response.status} - {error_text}")

                response_data = await response.json()

                if "candidates" not in response_data or not response_data["candidates"]:
                    raise Exception("No candidates in Gemini response")

                candidate = response_data["candidates"][0]
                if "content" not in candidate or "parts" not in candidate["content"]:
                    raise Exception("Invalid response structure from Gemini API")

                response_text = candidate["content"]["parts"][0].get("text", "")

                if not response_text.strip():
                    raise Exception("Empty response from Gemini API")

                return response_text

    async def health_check(self) -> bool:
        """
        Gemini APIの健全性チェック

        Returns:
            bool: 正常に動作しているか
        """
        try:
            # 簡単なテストリクエスト
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


class GeminiAdapterWithFallback(GeminiAdapter):
    """
    フォールバック付きGeminiアダプター

    API呼び出し失敗時にフォールバック応答を返す。
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash-exp",
        timeout: int = 30,
        fallback_message: str = "申し訳ありません。今少し調子が悪いようです。",
    ):
        super().__init__(api_key, model, timeout)
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

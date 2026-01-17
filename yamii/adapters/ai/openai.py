"""
OpenAI AIアダプター
OpenAI API (GPT-4.1等) への接続実装
PII匿名化機能付き
"""

import aiohttp

from ...core.anonymizer import PIIAnonymizer, get_anonymizer
from ...domain.ports.ai_port import ChatMessage, IAIProvider


class OpenAIAdapter(IAIProvider):
    """
    OpenAI AIアダプター

    OpenAI APIを使用してAI応答を生成。
    GPT-4.1をデフォルトモデルとして使用。
    PII匿名化機能を内蔵。
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4.1",
        timeout: int = 60,
        base_url: str = "https://api.openai.com/v1",
        enable_anonymization: bool = True,
    ):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.base_url = base_url
        self.enable_anonymization = enable_anonymization
        self._anonymizer: PIIAnonymizer | None = None

    @property
    def anonymizer(self) -> PIIAnonymizer:
        """匿名化サービスを取得（遅延初期化）"""
        if self._anonymizer is None:
            self._anonymizer = get_anonymizer()
        return self._anonymizer

    async def generate(
        self,
        message: str,
        system_prompt: str,
        max_tokens: int | None = None,
        conversation_history: list[ChatMessage] | None = None,
    ) -> str:
        """
        AI応答を生成

        Args:
            message: ユーザーメッセージ
            system_prompt: システムプロンプト
            max_tokens: 最大トークン数（オプション）
            conversation_history: 会話履歴（オプション、セッション内文脈保持用）

        Returns:
            str: AI応答テキスト（PII復元済み）

        Raises:
            Exception: API呼び出し失敗時
        """
        # PII匿名化
        mapping: dict[str, str] = {}
        processed_message = message
        processed_history: list[ChatMessage] | None = None

        if self.enable_anonymization:
            result = self.anonymizer.anonymize(message)
            processed_message = result.anonymized_text
            mapping = result.mapping

            # 会話履歴も匿名化
            if conversation_history:
                processed_history = []
                for msg in conversation_history:
                    history_result = self.anonymizer.anonymize(msg.content)
                    processed_history.append(
                        ChatMessage(role=msg.role, content=history_result.anonymized_text)
                    )
                    mapping.update(history_result.mapping)
        else:
            processed_history = conversation_history

        # API呼び出し
        response_text = await self._call_api(
            processed_message, system_prompt, max_tokens, processed_history
        )

        # PII復元（応答にプレースホルダーが含まれている場合）
        if mapping:
            response_text = self.anonymizer.deanonymize(response_text, mapping)

        return response_text

    async def _call_api(
        self,
        message: str,
        system_prompt: str,
        max_tokens: int | None = None,
        conversation_history: list[ChatMessage] | None = None,
    ) -> str:
        """OpenAI APIを呼び出し"""
        # メッセージリストを構築
        messages = [{"role": "system", "content": system_prompt}]

        # 会話履歴があれば追加（セッション内文脈保持）
        if conversation_history:
            for msg in conversation_history:
                messages.append({"role": msg.role, "content": msg.content})

        # 現在のユーザーメッセージを追加
        messages.append({"role": "user", "content": message})

        request_body = {
            "model": self.model,
            "messages": messages,
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
            response = await self._call_api(
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
        enable_anonymization: bool = True,
        fallback_message: str = "申し訳ありません。今少し調子が悪いようです。",
    ):
        super().__init__(api_key, model, timeout, base_url, enable_anonymization)
        self.fallback_message = fallback_message

    async def generate(
        self,
        message: str,
        system_prompt: str,
        max_tokens: int | None = None,
        conversation_history: list[ChatMessage] | None = None,
    ) -> str:
        """
        AI応答を生成（フォールバック付き）
        """
        try:
            return await super().generate(
                message, system_prompt, max_tokens, conversation_history
            )
        except Exception:
            return self.fallback_message

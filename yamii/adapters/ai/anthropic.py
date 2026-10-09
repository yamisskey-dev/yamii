"""
Anthropic AIアダプター
Claude API (Messages API) への接続実装
PII匿名化機能付き
"""

import re
from collections.abc import AsyncGenerator

import anthropic

from ...core.anonymizer import PIIAnonymizer, get_anonymizer
from ...domain.ports.ai_port import ChatMessage, IAIProvider

DEFAULT_MAX_TOKENS = 16000

# 拒否（refusal）時にサーバー側で別モデルへフォールバックさせる
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicAdapter(IAIProvider):
    """
    Anthropic AIアダプター

    Claude API を使用してAI応答を生成。
    Claude Sonnet 5.5 をデフォルトモデルとして使用。
    PII匿名化機能を内蔵。
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-5-5",
        timeout: int = 60,
        enable_anonymization: bool = True,
        client: anthropic.AsyncAnthropic | None = None,
    ):
        self.model = model
        self.enable_anonymization = enable_anonymization
        self._anonymizer: PIIAnonymizer | None = None
        self._client = client or anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout)

    async def close(self) -> None:
        """HTTPクライアントを閉じる"""
        await self._client.close()

    def _request_params(
        self,
        message: str,
        system_prompt: str,
        max_tokens: int | None,
        conversation_history: list[ChatMessage] | None,
    ) -> dict:
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in conversation_history or []
        ]
        messages.append({"role": "user", "content": message})
        return {
            "model": self.model,
            "max_tokens": max_tokens or DEFAULT_MAX_TOKENS,
            "system": system_prompt,
            "messages": messages,
            # 短い max_tokens（タイトル生成等）でも応答が切れないよう thinking は使わない
            "thinking": {"type": "between_tools"},
            "fallbacks": "default",
            "betas": [FALLBACK_BETA],
        }

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
        """Claude API を呼び出し"""
        response = await self._client.beta.messages.create(
            **self._request_params(message, system_prompt, max_tokens, conversation_history)
        )

        if response.stop_reason == "refusal":
            raise Exception("Claude API refusal")

        response_text = "".join(
            block.text for block in response.content if block.type == "text"
        )
        if not response_text.strip():
            raise Exception("Empty response from Claude API")

        return response_text

    async def generate_stream(
        self,
        message: str,
        system_prompt: str,
        max_tokens: int | None = None,
        conversation_history: list[ChatMessage] | None = None,
    ) -> AsyncGenerator[str, None]:
        """AI応答をストリーミング生成（PII匿名化/復元付き）"""
        mapping: dict[str, str] = {}
        processed_message = message
        processed_history: list[ChatMessage] | None = None

        if self.enable_anonymization:
            result = self.anonymizer.anonymize(message)
            processed_message = result.anonymized_text
            mapping = result.mapping

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

        if mapping:
            # PII復元が必要な場合、バッファリングして復元
            # プレースホルダーパターン: [PERSON_1] 等
            placeholder_pattern = re.compile(r"\[[A-Z_]+\d*\]")
            buffer = ""
            async for chunk in self._call_api_stream(
                processed_message, system_prompt, max_tokens, processed_history
            ):
                buffer += chunk
                # バッファにプレースホルダーの開始 '[' があり、まだ閉じていない場合は保留
                if "[" in buffer and "]" not in buffer.split("[")[-1]:
                    continue
                # 復元してyield
                restored = placeholder_pattern.sub(
                    lambda m: mapping.get(m.group(0), m.group(0)), buffer
                )
                yield restored
                buffer = ""
            # 残りのバッファをflush
            if buffer:
                restored = placeholder_pattern.sub(
                    lambda m: mapping.get(m.group(0), m.group(0)), buffer
                )
                yield restored
        else:
            async for chunk in self._call_api_stream(
                processed_message, system_prompt, max_tokens, processed_history
            ):
                yield chunk

    async def _call_api_stream(
        self,
        message: str,
        system_prompt: str,
        max_tokens: int | None = None,
        conversation_history: list[ChatMessage] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Claude API をストリーミングで呼び出し"""
        async with self._client.beta.messages.stream(
            **self._request_params(message, system_prompt, max_tokens, conversation_history)
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def health_check(self) -> bool:
        """
        Claude API の健全性チェック

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


class AnthropicAdapterWithFallback(AnthropicAdapter):
    """
    フォールバック付きAnthropicアダプター

    API呼び出し失敗時にフォールバック応答を返す。
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-5-5",
        timeout: int = 60,
        enable_anonymization: bool = True,
        client: anthropic.AsyncAnthropic | None = None,
        fallback_message: str = "申し訳ありません。今少し調子が悪いようです。",
    ):
        super().__init__(api_key, model, timeout, enable_anonymization, client)
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

    async def generate_stream(
        self,
        message: str,
        system_prompt: str,
        max_tokens: int | None = None,
        conversation_history: list[ChatMessage] | None = None,
    ) -> AsyncGenerator[str, None]:
        """AI応答をストリーミング生成（フォールバック付き）"""
        try:
            async for chunk in super().generate_stream(
                message, system_prompt, max_tokens, conversation_history
            ):
                yield chunk
        except Exception:
            yield self.fallback_message

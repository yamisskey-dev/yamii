"""
AIプロバイダーポート
LLM APIへのアクセスを抽象化
"""

from abc import ABC, abstractmethod


class IAIProvider(ABC):
    """
    AIプロバイダーインターフェース

    LLM API（Gemini, Claude, OpenAI等）への
    アクセスを抽象化。実装で切り替え可能。
    """

    @abstractmethod
    async def generate(
        self,
        message: str,
        system_prompt: str,
        max_tokens: int | None = None,
    ) -> str:
        """
        AI応答を生成

        Args:
            message: ユーザーメッセージ
            system_prompt: システムプロンプト
            max_tokens: 最大トークン数（オプション）

        Returns:
            str: AI応答テキスト
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """
        AI APIの健全性チェック

        Returns:
            bool: 正常に動作しているか
        """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """
        使用中のモデル名

        Returns:
            str: モデル名
        """

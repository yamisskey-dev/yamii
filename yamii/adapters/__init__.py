"""
Adapters Layer
ポートインターフェースの具体的な実装

注: 依存関係を軽くするため、アダプターは直接インポートを推奨
使用例:
    from yamii.adapters.ai.gemini import GeminiAdapter
    from yamii.adapters.storage.file import FileStorageAdapter
"""

# 遅延インポート用のサブモジュール名のみエクスポート
__all__ = [
    "ai",
    "storage",
    "platforms",
]

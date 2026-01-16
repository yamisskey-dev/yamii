"""
カスタム例外クラス
階層的な例外処理によるエラーハンドリングの統一
"""

from typing import Any


class YamiiException(Exception):
    """Yamiiアプリケーションのベース例外クラス"""

    def __init__(self, message: str, error_code: str | None = None,
                 details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}


class ConfigurationError(YamiiException):
    """設定関連のエラー"""


class DatabaseError(YamiiException):
    """データベース関連のエラー"""


class AuthenticationError(YamiiException):
    """認証・認可エラー"""


class ValidationError(YamiiException):
    """バリデーションエラー"""

    def __init__(self, message: str, field: str | None = None,
                 value: Any | None = None, **kwargs):
        super().__init__(message, **kwargs)
        if field:
            self.details['field'] = field
        if value is not None:
            self.details['value'] = value


class BusinessLogicError(YamiiException):
    """ビジネスロジック関連のエラー"""


class ExternalServiceError(YamiiException):
    """外部サービス（Gemini APIなど）関連のエラー"""

    def __init__(self, message: str, service_name: str = "unknown",
                 status_code: int | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.details['service_name'] = service_name
        if status_code:
            self.details['status_code'] = status_code


class PromptError(BusinessLogicError):
    """プロンプト関連のエラー"""


class UserProfileError(BusinessLogicError):
    """ユーザープロファイル関連のエラー"""


class MemoryError(BusinessLogicError):
    """メモリ・記憶関連のエラー"""


class CounselingError(BusinessLogicError):
    """カウンセリング処理関連のエラー"""

    def __init__(self, message: str, user_id: str | None = None,
                 session_id: str | None = None, **kwargs):
        super().__init__(message, **kwargs)
        if user_id:
            self.details['user_id'] = user_id
        if session_id:
            self.details['session_id'] = session_id

"""
カスタム例外クラス
階層的な例外処理によるエラーハンドリングの統一
"""

from typing import Optional, Dict, Any


class NaviException(Exception):
    """Naviアプリケーションのベース例外クラス"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}


class ConfigurationError(NaviException):
    """設定関連のエラー"""
    pass


class DatabaseError(NaviException):
    """データベース関連のエラー"""
    pass


class AuthenticationError(NaviException):
    """認証・認可エラー"""
    pass


class ValidationError(NaviException):
    """バリデーションエラー"""
    
    def __init__(self, message: str, field: Optional[str] = None, 
                 value: Optional[Any] = None, **kwargs):
        super().__init__(message, **kwargs)
        if field:
            self.details['field'] = field
        if value is not None:
            self.details['value'] = value


class BusinessLogicError(NaviException):
    """ビジネスロジック関連のエラー"""
    pass


class ExternalServiceError(NaviException):
    """外部サービス（Gemini APIなど）関連のエラー"""
    
    def __init__(self, message: str, service_name: str = "unknown", 
                 status_code: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.details['service_name'] = service_name
        if status_code:
            self.details['status_code'] = status_code


class PromptError(BusinessLogicError):
    """プロンプト関連のエラー"""
    pass


class UserProfileError(BusinessLogicError):
    """ユーザープロファイル関連のエラー"""
    pass


class MemoryError(BusinessLogicError):
    """メモリ・記憶関連のエラー"""
    pass


class CounselingError(BusinessLogicError):
    """カウンセリング処理関連のエラー"""
    
    def __init__(self, message: str, user_id: Optional[str] = None,
                 session_id: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        if user_id:
            self.details['user_id'] = user_id
        if session_id:
            self.details['session_id'] = session_id
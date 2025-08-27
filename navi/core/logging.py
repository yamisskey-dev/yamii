"""
統一ログシステム
構造化ログによる一貫したログ出力
"""

import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from .exceptions import NaviException


class StructuredFormatter(logging.Formatter):
    """構造化ログフォーマッター"""
    
    def format(self, record: logging.LogRecord) -> str:
        # ベース情報
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }
        
        # モジュール情報
        if hasattr(record, 'filename'):
            log_entry["file"] = record.filename
        if hasattr(record, 'lineno'):
            log_entry["line"] = record.lineno
        if hasattr(record, 'funcName'):
            log_entry["function"] = record.funcName
        
        # カスタム属性の追加
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info']:
                extra_fields[key] = value
        
        if extra_fields:
            log_entry["extra"] = extra_fields
        
        # 例外情報
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None
            }
            
            # NaviExceptionの場合は追加情報を含める
            if isinstance(record.exc_info[1], NaviException):
                log_entry["exception"]["error_code"] = record.exc_info[1].error_code
                log_entry["exception"]["details"] = record.exc_info[1].details
        
        return json.dumps(log_entry, ensure_ascii=False, separators=(',', ':'))


class NaviLogger:
    """統一ログシステム"""
    
    _loggers: Dict[str, logging.Logger] = {}
    _configured = False
    
    @classmethod
    def configure(cls, log_level: str = "INFO", log_file: Optional[str] = None):
        """ログシステムを設定"""
        if cls._configured:
            return
        
        # ルートロガーの設定
        root_logger = logging.getLogger("navi")
        root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # コンソールハンドラー
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(console_handler)
        
        # ファイルハンドラー（指定された場合）
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(StructuredFormatter())
            root_logger.addHandler(file_handler)
        
        cls._configured = True
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """ログインスタンスを取得"""
        if not cls._configured:
            cls.configure()
        
        if name not in cls._loggers:
            logger_name = f"navi.{name}" if not name.startswith("navi.") else name
            cls._loggers[name] = logging.getLogger(logger_name)
        
        return cls._loggers[name]


# 便利関数群
def get_logger(name: str) -> logging.Logger:
    """ロガーを取得"""
    return NaviLogger.get_logger(name)


def log_request(logger: logging.Logger, user_id: str, endpoint: str, 
                method: str = "POST", **kwargs):
    """リクエストログ"""
    logger.info(f"Request received: {method} {endpoint}", extra={
        "event_type": "request",
        "user_id": user_id,
        "endpoint": endpoint,
        "method": method,
        **kwargs
    })


def log_response(logger: logging.Logger, user_id: str, endpoint: str,
                status_code: int, duration_ms: float, **kwargs):
    """レスポンスログ"""
    logger.info(f"Response sent: {status_code}", extra={
        "event_type": "response", 
        "user_id": user_id,
        "endpoint": endpoint,
        "status_code": status_code,
        "duration_ms": duration_ms,
        **kwargs
    })


def log_error(logger: logging.Logger, error: Exception, context: Optional[Dict[str, Any]] = None):
    """エラーログ"""
    extra_info = {"event_type": "error"}
    if context:
        extra_info.update(context)
    
    logger.error(f"Error occurred: {str(error)}", exc_info=True, extra=extra_info)


def log_business_event(logger: logging.Logger, event: str, user_id: Optional[str] = None,
                      **kwargs):
    """ビジネスイベントログ"""
    extra_info = {
        "event_type": "business_event",
        "business_event": event
    }
    if user_id:
        extra_info["user_id"] = user_id
    extra_info.update(kwargs)
    
    logger.info(f"Business event: {event}", extra=extra_info)
"""
統一ログシステム
構造化ログによる一貫したログ出力
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any

from .exceptions import YamiiException


def _get_log_level() -> str:
    """環境変数からログレベルを取得"""
    return os.getenv("YAMII_LOG_LEVEL", "INFO").upper()


def _is_debug_mode() -> bool:
    """デバッグモードかどうか"""
    return os.getenv("YAMII_DEBUG", "false").lower() == "true"


class StructuredFormatter(logging.Formatter):
    """構造化ログフォーマッター"""

    def format(self, record: logging.LogRecord) -> str:
        # ベース情報
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # モジュール情報
        if hasattr(record, "filename"):
            log_entry["file"] = record.filename
        if hasattr(record, "lineno"):
            log_entry["line"] = record.lineno
        if hasattr(record, "funcName"):
            log_entry["function"] = record.funcName

        # カスタム属性の追加
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                extra_fields[key] = value

        if extra_fields:
            log_entry["extra"] = extra_fields

        # 例外情報
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
            }

            # YamiiExceptionの場合は追加情報を含める
            if isinstance(record.exc_info[1], YamiiException):
                log_entry["exception"]["error_code"] = record.exc_info[1].error_code
                log_entry["exception"]["details"] = record.exc_info[1].details

        return json.dumps(log_entry, ensure_ascii=False, separators=(",", ":"))


class YamiiLogger:
    """統一ログシステム"""

    _loggers: dict[str, logging.Logger] = {}
    _configured = False

    @classmethod
    def configure(cls, log_level: str | None = None):
        """ログシステムを設定"""
        if cls._configured:
            return

        # 環境変数からログレベルを取得（引数が優先）
        actual_log_level = log_level or _get_log_level()

        # ルートロガーの設定
        root_logger = logging.getLogger("yamii")
        root_logger.setLevel(getattr(logging, actual_log_level.upper()))

        # コンソールハンドラー
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(console_handler)

        cls._configured = True

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """ログインスタンスを取得"""
        if not cls._configured:
            cls.configure()

        if name not in cls._loggers:
            logger_name = f"yamii.{name}" if not name.startswith("yamii.") else name
            cls._loggers[name] = logging.getLogger(logger_name)

        return cls._loggers[name]


# 便利関数群
def get_logger(name: str) -> logging.Logger:
    """ロガーを取得"""
    return YamiiLogger.get_logger(name)


def log_request(
    logger: logging.Logger, user_id: str, endpoint: str, method: str = "POST", **kwargs
):
    """リクエストログ"""
    logger.info(
        f"Request received: {method} {endpoint}",
        extra={
            "event_type": "request",
            "user_id": user_id,
            "endpoint": endpoint,
            "method": method,
            **kwargs,
        },
    )


def log_response(
    logger: logging.Logger,
    user_id: str,
    endpoint: str,
    status_code: int,
    duration_ms: float,
    **kwargs,
):
    """レスポンスログ"""
    logger.info(
        f"Response sent: {status_code}",
        extra={
            "event_type": "response",
            "user_id": user_id,
            "endpoint": endpoint,
            "status_code": status_code,
            "duration_ms": duration_ms,
            **kwargs,
        },
    )


def log_error(
    logger: logging.Logger, error: Exception, context: dict[str, Any] | None = None
):
    """エラーログ"""
    extra_info = {"event_type": "error"}
    if context:
        extra_info.update(context)

    logger.error(f"Error occurred: {str(error)}", exc_info=True, extra=extra_info)


def log_business_event(
    logger: logging.Logger, event: str, user_id: str | None = None, **kwargs
):
    """ビジネスイベントログ"""
    extra_info = {"event_type": "business_event", "business_event": event}
    if user_id:
        extra_info["user_id"] = user_id
    extra_info.update(kwargs)

    logger.info(f"Business event: {event}", extra=extra_info)

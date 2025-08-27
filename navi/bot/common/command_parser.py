"""
Command Parser
ボットコマンドの解析と処理
"""

import re
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass


class BotCommandType(Enum):
    """ボットコマンドタイプ"""
    HELP = "help"
    STATUS = "status"
    CUSTOM_PROMPT = "custom_prompt"
    PROFILE = "profile"
    SESSION_END = "session_end"
    COUNSELING = "counseling"


@dataclass
class BotCommand:
    """解析されたボットコマンド"""
    command_type: BotCommandType
    action: Optional[str] = None  # set, show, delete など
    content: Optional[str] = None  # コマンドの内容
    original_text: str = ""
    is_valid: bool = True
    error_message: Optional[str] = None
    
    @property
    def is_management_command(self) -> bool:
        """管理コマンドかどうか"""
        return self.command_type in [
            BotCommandType.HELP,
            BotCommandType.STATUS,
            BotCommandType.CUSTOM_PROMPT,
            BotCommandType.PROFILE,
            BotCommandType.SESSION_END
        ]


class CommandParser:
    """ボットコマンド解析クラス"""
    
    def __init__(self):
        self.help_keywords = ["help", "ヘルプ", "使い方", "?"]
        self.status_keywords = ["status", "ステータス", "状態"]
        self.end_keywords = ["終了", "end", "quit", "exit", "bye"]
    
    def parse_message(self, text: str, bot_name: str = "navi") -> BotCommand:
        """メッセージを解析してコマンドに変換"""
        if not text or not text.strip():
            return BotCommand(
                command_type=BotCommandType.COUNSELING,
                original_text=text,
                is_valid=False,
                error_message="空のメッセージです"
            )
        
        text = text.strip()
        original_text = text
        
        # ボット名のプレフィックスを除去
        text = self._remove_bot_prefix(text, bot_name)
        
        # コマンドタイプ判定
        command_type = self._determine_command_type(text)
        
        if command_type == BotCommandType.HELP:
            return self._parse_help_command(text, original_text)
        elif command_type == BotCommandType.STATUS:
            return self._parse_status_command(text, original_text)
        elif command_type == BotCommandType.CUSTOM_PROMPT:
            return self._parse_custom_prompt_command(text, original_text)
        elif command_type == BotCommandType.PROFILE:
            return self._parse_profile_command(text, original_text)
        elif command_type == BotCommandType.SESSION_END:
            return self._parse_session_end_command(text, original_text)
        else:
            return self._parse_counseling_command(text, original_text)
    
    def _remove_bot_prefix(self, text: str, bot_name: str) -> str:
        """ボット名プレフィックスを除去"""
        # @botname 形式
        mention_pattern = rf"@{bot_name}\s*"
        text = re.sub(mention_pattern, "", text, flags=re.IGNORECASE)
        
        # "navi " 形式
        if text.lower().startswith(f"{bot_name.lower()} "):
            text = text[len(bot_name) + 1:].strip()
        
        return text.strip()
    
    def _determine_command_type(self, text: str) -> BotCommandType:
        """コマンドタイプを判定"""
        text_lower = text.lower()
        
        # ヘルプコマンド
        if any(keyword in text_lower for keyword in [f"/{keyword}" for keyword in self.help_keywords]) or \
           any(keyword in text_lower for keyword in self.help_keywords):
            return BotCommandType.HELP
        
        # ステータスコマンド
        if any(keyword in text_lower for keyword in [f"/{keyword}" for keyword in self.status_keywords]) or \
           any(keyword in text_lower for keyword in self.status_keywords):
            return BotCommandType.STATUS
        
        # カスタムプロンプトコマンド
        if "/custom" in text_lower or "カスタムプロンプト" in text:
            return BotCommandType.CUSTOM_PROMPT
        
        # プロファイルコマンド
        if "/profile" in text_lower or "プロファイル" in text:
            return BotCommandType.PROFILE
        
        # セッション終了
        if any(keyword in text for keyword in self.end_keywords):
            return BotCommandType.SESSION_END
        
        # デフォルトは人生相談
        return BotCommandType.COUNSELING
    
    def _parse_help_command(self, text: str, original: str) -> BotCommand:
        """ヘルプコマンドの解析"""
        return BotCommand(
            command_type=BotCommandType.HELP,
            original_text=original
        )
    
    def _parse_status_command(self, text: str, original: str) -> BotCommand:
        """ステータスコマンドの解析"""
        return BotCommand(
            command_type=BotCommandType.STATUS,
            original_text=original
        )
    
    def _parse_custom_prompt_command(self, text: str, original: str) -> BotCommand:
        """カスタムプロンプトコマンドの解析"""
        text_lower = text.lower()
        
        if "show" in text_lower or "表示" in text:
            return BotCommand(
                command_type=BotCommandType.CUSTOM_PROMPT,
                action="show",
                original_text=original
            )
        elif "delete" in text_lower or "削除" in text:
            return BotCommand(
                command_type=BotCommandType.CUSTOM_PROMPT,
                action="delete",
                original_text=original
            )
        elif "set" in text_lower or "設定" in text:
            # カスタムプロンプトの内容を抽出
            set_match = re.search(r'/custom\s+set\s+(.+)', text, re.IGNORECASE | re.DOTALL)
            if set_match:
                content = set_match.group(1).strip()
                # ダブルクォート除去
                if content.startswith('"') and content.endswith('"'):
                    content = content[1:-1]
                
                return BotCommand(
                    command_type=BotCommandType.CUSTOM_PROMPT,
                    action="set",
                    content=content,
                    original_text=original,
                    is_valid=bool(content)
                )
            else:
                return BotCommand(
                    command_type=BotCommandType.CUSTOM_PROMPT,
                    action="set",
                    original_text=original,
                    is_valid=False,
                    error_message="プロンプトの内容を指定してください"
                )
        else:
            return BotCommand(
                command_type=BotCommandType.CUSTOM_PROMPT,
                action="help",
                original_text=original
            )
    
    def _parse_profile_command(self, text: str, original: str) -> BotCommand:
        """プロファイルコマンドの解析"""
        text_lower = text.lower()
        
        if "show" in text_lower or "表示" in text:
            return BotCommand(
                command_type=BotCommandType.PROFILE,
                action="show",
                original_text=original
            )
        elif "delete" in text_lower or "削除" in text:
            return BotCommand(
                command_type=BotCommandType.PROFILE,
                action="delete",
                original_text=original
            )
        elif "set" in text_lower or "設定" in text:
            # プロファイル情報を抽出
            set_match = re.search(r'/profile\s+set\s+(.+)', text, re.IGNORECASE | re.DOTALL)
            if set_match:
                content = set_match.group(1).strip()
                return BotCommand(
                    command_type=BotCommandType.PROFILE,
                    action="set",
                    content=content,
                    original_text=original,
                    is_valid=bool(content)
                )
            else:
                return BotCommand(
                    command_type=BotCommandType.PROFILE,
                    action="set",
                    original_text=original,
                    is_valid=False,
                    error_message="プロファイル情報を指定してください"
                )
        else:
            return BotCommand(
                command_type=BotCommandType.PROFILE,
                action="help",
                original_text=original
            )
    
    def _parse_session_end_command(self, text: str, original: str) -> BotCommand:
        """セッション終了コマンドの解析"""
        return BotCommand(
            command_type=BotCommandType.SESSION_END,
            original_text=original
        )
    
    def _parse_counseling_command(self, text: str, original: str) -> BotCommand:
        """人生相談コマンドの解析"""
        return BotCommand(
            command_type=BotCommandType.COUNSELING,
            content=text,
            original_text=original,
            is_valid=bool(text.strip())
        )
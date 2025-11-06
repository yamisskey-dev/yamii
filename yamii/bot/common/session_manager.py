"""
Session Manager
ユーザーセッション管理の共通機能
"""

import time
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class UserSession:
    """ユーザーセッション情報"""
    user_id: str
    session_id: str
    platform: str
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self, timeout_seconds: int) -> bool:
        """セッションが期限切れかチェック"""
        return (datetime.now() - self.last_activity).total_seconds() > timeout_seconds
    
    def update_activity(self):
        """最終活動時間を更新"""
        self.last_activity = datetime.now()


class SessionManager:
    """ユーザーセッション管理クラス"""
    
    def __init__(self, session_timeout: int = 3600):
        self.session_timeout = session_timeout
        self.sessions: Dict[str, UserSession] = {}  # user_id -> UserSession
        self.session_lookup: Dict[str, str] = {}    # session_id -> user_id
    
    def create_session(self, user_id: str, platform: str, session_id: Optional[str] = None) -> UserSession:
        """新しいセッションを作成"""
        if session_id is None:
            session_id = f"{platform}_{user_id}_{int(time.time())}"
        
        # 既存セッションがあれば削除
        if user_id in self.sessions:
            old_session = self.sessions[user_id]
            self.session_lookup.pop(old_session.session_id, None)
        
        # 新しいセッション作成
        session = UserSession(
            user_id=user_id,
            session_id=session_id,
            platform=platform
        )
        
        self.sessions[user_id] = session
        self.session_lookup[session_id] = user_id
        
        return session
    
    def get_session(self, user_id: str) -> Optional[UserSession]:
        """ユーザーIDからセッションを取得"""
        session = self.sessions.get(user_id)
        if session and not session.is_expired(self.session_timeout):
            session.update_activity()
            return session
        elif session:
            # 期限切れセッションを削除
            self.end_session(user_id)
        return None
    
    def get_session_by_id(self, session_id: str) -> Optional[UserSession]:
        """セッションIDからセッションを取得"""
        user_id = self.session_lookup.get(session_id)
        if user_id:
            return self.get_session(user_id)
        return None
    
    def end_session(self, user_id: str) -> bool:
        """セッションを終了"""
        session = self.sessions.pop(user_id, None)
        if session:
            self.session_lookup.pop(session.session_id, None)
            return True
        return False
    
    def update_session_context(self, user_id: str, context: Dict[str, Any]):
        """セッションのコンテキストを更新"""
        session = self.get_session(user_id)
        if session:
            session.context.update(context)
    
    def update_session_preferences(self, user_id: str, preferences: Dict[str, Any]):
        """セッションの設定を更新"""
        session = self.get_session(user_id)
        if session:
            session.preferences.update(preferences)
    
    def cleanup_expired_sessions(self):
        """期限切れセッションのクリーンアップ"""
        expired_users = []
        
        for user_id, session in self.sessions.items():
            if session.is_expired(self.session_timeout):
                expired_users.append(user_id)
        
        for user_id in expired_users:
            self.end_session(user_id)
    
    def get_active_sessions_count(self) -> int:
        """アクティブセッション数を取得"""
        self.cleanup_expired_sessions()
        return len(self.sessions)
    
    def get_session_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """セッション情報を取得（デバッグ用）"""
        session = self.get_session(user_id)
        if session:
            return {
                "user_id": session.user_id,
                "session_id": session.session_id,
                "platform": session.platform,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "context": session.context,
                "preferences": session.preferences
            }
        return None
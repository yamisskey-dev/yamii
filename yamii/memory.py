"""
Memory System - 人間らしい記憶管理システム
"""

from datetime import datetime
from typing import Dict, List, Optional
import json


class MemorySystem:
    """記憶システム - 会話履歴とユーザープロファイルを管理"""
    
    def __init__(self):
        self.conversations: List[Dict] = []
        self.user_profiles: Dict[str, Dict] = {}
    
    def add_conversation(self, user_id: str, user_message: str, ai_response: str, 
                        importance: int = 5, context: str = "general") -> None:
        """会話を記憶に追加"""
        conversation = {
            'id': f"conv_{datetime.now().timestamp()}",
            'user_id': user_id,
            'timestamp': datetime.now().timestamp(),
            'user_message': user_message,
            'ai_response': ai_response,
            'context': context,
            'importance': importance,
            'isActive': True
        }
        
        self.conversations.append(conversation)
        
        # ユーザープロファイルを更新
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                'name': user_id,
                'interests': [],
                'conversationStyle': 'casual',
                'lastInteraction': datetime.now().timestamp(),
                'conversationHistory': []
            }
        
        self.user_profiles[user_id]['lastInteraction'] = datetime.now().timestamp()
        self.user_profiles[user_id]['conversationHistory'].append(conversation['id'])
    
    def get_user_context(self, user_id: str, max_conversations: int = 5) -> str:
        """ユーザーの文脈情報を取得"""
        if user_id not in self.user_profiles:
            return ""
        
        # ユーザーの最近の会話を取得
        user_conversations = [
            conv for conv in self.conversations 
            if conv['user_id'] == user_id and conv['isActive']
        ]
        
        # 重要度と時間順でソート
        user_conversations.sort(
            key=lambda x: (x['importance'], x['timestamp']), 
            reverse=True
        )
        
        recent_conversations = user_conversations[:max_conversations]
        
        if not recent_conversations:
            return ""
        
        context = f"{user_id}さんとの過去の会話を参考にしてください。\n\n"
        context += "過去の会話の流れ：\n"
        
        for i, conv in enumerate(recent_conversations):
            date = datetime.fromtimestamp(conv['timestamp']).strftime('%Y-%m-%d')
            context += f"{i + 1}. [{date}] {conv['user_message']} → {conv['ai_response']}\n"
        
        return context
    
    def get_user_memory(self, user_id: str) -> Optional[Dict]:
        """ユーザーの記憶データを取得"""
        if user_id not in self.user_profiles:
            return None
        
        user_conversations = [
            conv for conv in self.conversations 
            if conv['user_id'] == user_id and conv['isActive']
        ]
        
        return {
            'conversations': user_conversations,
            'userProfile': self.user_profiles[user_id],
            'conversationContext': {
                'currentTopic': '',
                'mood': 'neutral',
                'relationshipLevel': 5
            }
        }
    
    def cleanup_old_memories(self, days_to_keep: int = 30) -> None:
        """古い記憶をクリーンアップ"""
        cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
        
        for conv in self.conversations:
            if conv['timestamp'] < cutoff_time and conv['importance'] < 6:
                conv['isActive'] = False
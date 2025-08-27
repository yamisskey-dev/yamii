#!/usr/bin/env python3
"""
セキュアプロンプトストア - E2EE対応プロンプト管理システム
PostgreSQL + E2EE暗号化によるゼロナレッジアーキテクチャ
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .encryption import E2EECrypto, EncryptedData, get_e2ee_crypto
from .database import AsyncDatabase, get_database
from .exceptions import NaviException

logger = logging.getLogger(__name__)


class SecurePromptStore:
    """
    E2EE対応セキュアプロンプトストア
    
    特徴:
    - エンドツーエンド暗号化
    - ゼロナレッジアーキテクチャ
    - 非同期PostgreSQL統合
    - 前方秘匿性対応
    """
    
    def __init__(
        self, 
        database: Optional[AsyncDatabase] = None,
        e2ee_crypto: Optional[E2EECrypto] = None
    ):
        self.database = database
        self.e2ee_crypto = e2ee_crypto or get_e2ee_crypto()
        self.logger = logger
    
    async def initialize(self) -> None:
        """セキュアストア初期化"""
        try:
            if not self.database:
                self.database = await get_database()
            
            self.logger.info("セキュアプロンプトストアを初期化しました")
            
        except Exception as e:
            self.logger.error(f"セキュアストア初期化エラー: {e}")
            raise NaviException(f"Secure store initialization failed: {e}")
    
    async def store_prompt(
        self,
        user_id: str,
        prompt_data: Dict[str, Any],
        public_key: bytes,
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> bool:
        """
        プロンプトをE2EE暗号化して保存
        
        Args:
            user_id: ユーザーID
            prompt_data: プロンプトデータ
            public_key: ユーザーの公開鍵
            title: プロンプトタイトル
            description: プロンプト説明
            
        Returns:
            bool: 保存成功の可否
        """
        try:
            if not self.database:
                await self.initialize()
            
            # プロンプトデータをJSON文字列に変換
            prompt_json = json.dumps(prompt_data, ensure_ascii=False)
            
            # E2EE暗号化
            encrypted_data = self.e2ee_crypto.encrypt(prompt_json, public_key)
            
            # データベースに保存
            prompt_id = prompt_data.get("id", f"prompt_{datetime.utcnow().timestamp()}")
            
            success = await self.database.insert_encrypted_prompt(
                user_id=user_id,
                encrypted_data=encrypted_data,
                prompt_id=prompt_id,
                title=title or prompt_data.get("title"),
                description=description or prompt_data.get("description")
            )
            
            if success:
                self.logger.info(f"プロンプトを暗号化保存: user={user_id}, prompt={prompt_id}")
            else:
                self.logger.error(f"プロンプト保存失敗: user={user_id}, prompt={prompt_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"プロンプト保存エラー: {e}")
            return False
    
    async def get_prompt(
        self,
        user_id: str,
        prompt_id: str,
        private_key: bytes
    ) -> Optional[str]:
        """
        暗号化プロンプトを取得・復号
        
        Args:
            user_id: ユーザーID
            prompt_id: プロンプトID
            private_key: ユーザーの秘密鍵
            
        Returns:
            Optional[str]: 復号されたプロンプトデータ（JSON文字列）
        """
        try:
            if not self.database:
                await self.initialize()
            
            # 暗号化データを取得
            encrypted_data = await self.database.get_encrypted_prompt(user_id, prompt_id)
            
            if not encrypted_data:
                self.logger.warning(f"プロンプトが見つかりません: user={user_id}, prompt={prompt_id}")
                return None
            
            # E2EE復号
            decrypted_json = self.e2ee_crypto.decrypt(encrypted_data, private_key)
            
            self.logger.info(f"プロンプトを復号取得: user={user_id}, prompt={prompt_id}")
            
            return decrypted_json
            
        except Exception as e:
            self.logger.error(f"プロンプト取得エラー: {e}")
            return None
    
    async def get_prompt_data(
        self,
        user_id: str,
        prompt_id: str,
        private_key: bytes
    ) -> Optional[Dict[str, Any]]:
        """
        暗号化プロンプトを取得・復号（辞書形式）
        
        Args:
            user_id: ユーザーID
            prompt_id: プロンプトID
            private_key: ユーザーの秘密鍵
            
        Returns:
            Optional[Dict[str, Any]]: 復号されたプロンプトデータ
        """
        try:
            decrypted_json = await self.get_prompt(user_id, prompt_id, private_key)
            
            if decrypted_json:
                return json.loads(decrypted_json)
            
            return None
            
        except json.JSONDecodeError as e:
            self.logger.error(f"プロンプトデータのJSON解析エラー: {e}")
            return None
        except Exception as e:
            self.logger.error(f"プロンプトデータ取得エラー: {e}")
            return None
    
    async def list_prompts(self, user_id: str) -> List[Dict[str, Any]]:
        """
        ユーザーのプロンプト一覧を取得（メタデータのみ、暗号化されていない）
        
        Args:
            user_id: ユーザーID
            
        Returns:
            List[Dict[str, Any]]: プロンプトメタデータ一覧
        """
        try:
            if not self.database:
                await self.initialize()
            
            prompts = await self.database.list_user_prompts(user_id)
            
            self.logger.info(f"プロンプト一覧取得: user={user_id}, count={len(prompts)}")
            
            return prompts
            
        except Exception as e:
            self.logger.error(f"プロンプト一覧取得エラー: {e}")
            return []
    
    async def update_prompt(
        self,
        user_id: str,
        prompt_id: str,
        prompt_data: Dict[str, Any],
        public_key: bytes,
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> bool:
        """
        プロンプトを更新（再暗号化）
        
        Args:
            user_id: ユーザーID
            prompt_id: プロンプトID
            prompt_data: 新しいプロンプトデータ
            public_key: ユーザーの公開鍵
            title: 新しいタイトル
            description: 新しい説明
            
        Returns:
            bool: 更新成功の可否
        """
        try:
            if not self.database:
                await self.initialize()
            
            # プロンプトデータをJSON文字列に変換
            prompt_json = json.dumps(prompt_data, ensure_ascii=False)
            
            # E2EE暗号化
            encrypted_data = self.e2ee_crypto.encrypt(prompt_json, public_key)
            
            # データベースで更新
            success = await self.database.update_encrypted_prompt(
                user_id=user_id,
                prompt_id=prompt_id,
                encrypted_data=encrypted_data,
                title=title,
                description=description
            )
            
            if success:
                self.logger.info(f"プロンプトを更新: user={user_id}, prompt={prompt_id}")
            else:
                self.logger.error(f"プロンプト更新失敗: user={user_id}, prompt={prompt_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"プロンプト更新エラー: {e}")
            return False
    
    async def delete_prompt(self, user_id: str, prompt_id: str) -> bool:
        """
        プロンプトを削除（論理削除）
        
        Args:
            user_id: ユーザーID
            prompt_id: プロンプトID
            
        Returns:
            bool: 削除成功の可否
        """
        try:
            if not self.database:
                await self.initialize()
            
            success = await self.database.delete_encrypted_prompt(user_id, prompt_id)
            
            if success:
                self.logger.info(f"プロンプトを削除: user={user_id}, prompt={prompt_id}")
            else:
                self.logger.error(f"プロンプト削除失敗: user={user_id}, prompt={prompt_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"プロンプト削除エラー: {e}")
            return False
    
    async def get_default_prompts(self, user_id: str, private_key: bytes) -> List[Dict[str, Any]]:
        """
        デフォルトプロンプト一覧を取得
        
        Args:
            user_id: ユーザーID
            private_key: 秘密鍵
            
        Returns:
            List[Dict[str, Any]]: デフォルトプロンプト一覧
        """
        try:
            # まず、デフォルトプロンプトが存在するかチェック
            prompts = await self.list_prompts(user_id)
            default_prompts = [p for p in prompts if p.get("is_default", False)]
            
            if not default_prompts:
                # デフォルトプロンプトがない場合は作成
                await self._create_default_prompts(user_id, private_key)
                prompts = await self.list_prompts(user_id)
                default_prompts = [p for p in prompts if p.get("is_default", False)]
            
            return default_prompts
            
        except Exception as e:
            self.logger.error(f"デフォルトプロンプト取得エラー: {e}")
            return []
    
    async def _create_default_prompts(self, user_id: str, private_key: bytes) -> None:
        """デフォルトプロンプトを作成"""
        try:
            # 公開鍵を生成（実際の実装では既存の公開鍵を使用）
            public_key, _ = self.e2ee_crypto.generate_key_pair()
            
            default_prompts = [
                {
                    "id": "default_counselor",
                    "title": "人生相談カウンセラー",
                    "description": "標準的なカウンセリング対応",
                    "prompt_text": """あなたは経験豊富で共感力の高い人生相談カウンセラーです。
相談者の気持ちに寄り添い、実践的で心に響くアドバイスを提供してください。

対応方針:
1. まず相談者の感情を理解し、共感を示す
2. 問題の本質を見極める
3. 具体的で実行可能な解決策を提案する
4. 相談者を励まし、前向きな気持ちになれるよう支援する
5. 必要に応じて専門機関への相談も提案する

絵文字は控えめに使用し、温かみのある文章を心がけてください。
深刻な問題（自殺願望など）の場合は、専門機関への相談を強く推奨してください。""",
                    "tags": ["カウンセラー", "標準", "人生相談"]
                },
                {
                    "id": "friendly_sister",
                    "title": "優しいお姉さん",
                    "description": "親しみやすい家族的なキャラクター",
                    "prompt_text": """あなたは優しくて頼りになるお姉さんです。
相談者を弟や妹のように思って、親しみやすく、でもしっかりとしたアドバイスをしてください。

特徴:
- 親しみやすい口調で話す
- 時には厳しいことも愛情を持って伝える
- 実体験を交えたアドバイスをする
- 相談者の成長を心から願っている
- 必要な時は背中を押してあげる

「〜だよ」「〜だね」などの親しみやすい語尾を使い、温かい雰囲気を作ってください。""",
                    "tags": ["親しみやすい", "家族的", "優しい"]
                }
            ]
            
            for prompt_data in default_prompts:
                await self.store_prompt(
                    user_id=user_id,
                    prompt_data=prompt_data,
                    public_key=public_key,
                    title=prompt_data["title"],
                    description=prompt_data["description"]
                )
            
            self.logger.info(f"デフォルトプロンプトを作成: user={user_id}")
            
        except Exception as e:
            self.logger.error(f"デフォルトプロンプト作成エラー: {e}")


# グローバルインスタンス
_global_secure_store: Optional[SecurePromptStore] = None


async def get_secure_prompt_store() -> SecurePromptStore:
    """グローバルセキュアプロンプトストアインスタンスを取得"""
    global _global_secure_store
    
    if _global_secure_store is None:
        _global_secure_store = SecurePromptStore()
        await _global_secure_store.initialize()
    
    return _global_secure_store


async def init_secure_store() -> SecurePromptStore:
    """セキュアストア初期化"""
    store = await get_secure_prompt_store()
    return store
"""
User settings management with encrypted PostgreSQL database storage
"""
import os
import psycopg2
import psycopg2.extras
import hashlib
import json
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class UserSettingsManager:
    """
    Encrypted user settings manager using PostgreSQL database
    """
    
    def __init__(self, db_url: str = None, key_file: str = "encryption.key"):
        self.db_url = db_url or os.getenv("DATABASE_URL", "postgresql://navi_user:your_secure_password_here@db:5432/navi")
        self.key_file = key_file
        self.cipher_suite = self._get_or_create_cipher()
        self._init_database()
    
    def _get_or_create_cipher(self) -> Fernet:
        """Get or create encryption key"""
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            # Set restrictive permissions on key file
            os.chmod(self.key_file, 0o600)
        
        return Fernet(key)
    
    def _get_connection(self):
        """Get PostgreSQL database connection"""
        return psycopg2.connect(self.db_url)
    
    def _init_database(self):
        """Initialize database with required tables"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # User settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id TEXT PRIMARY KEY,
                encrypted_data TEXT NOT NULL,
                data_hash TEXT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Custom prompts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_prompts (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                encrypted_prompt TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                data_hash TEXT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, name)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _encrypt_data(self, data: Dict[str, Any]) -> tuple[str, str]:
        """Encrypt data and create hash for integrity"""
        json_data = json.dumps(data, ensure_ascii=False, sort_keys=True)
        encrypted_data = self.cipher_suite.encrypt(json_data.encode('utf-8'))
        
        # Create hash for data integrity
        data_hash = hashlib.sha256(json_data.encode('utf-8')).hexdigest()
        
        return encrypted_data.decode('utf-8'), data_hash
    
    def _decrypt_data(self, encrypted_data: str, expected_hash: str) -> Dict[str, Any]:
        """Decrypt data and verify integrity"""
        try:
            decrypted_bytes = self.cipher_suite.decrypt(encrypted_data.encode('utf-8'))
            json_data = decrypted_bytes.decode('utf-8')
            
            # Verify data integrity
            actual_hash = hashlib.sha256(json_data.encode('utf-8')).hexdigest()
            if actual_hash != expected_hash:
                logger.error(f"Data integrity check failed. Expected: {expected_hash}, Got: {actual_hash}")
                raise ValueError("Data integrity verification failed")
            
            return json.loads(json_data)
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def save_user_settings(self, user_id: str, settings: Dict[str, Any]) -> bool:
        """Save encrypted user settings"""
        try:
            encrypted_data, data_hash = self._encrypt_data(settings)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_settings (user_id, encrypted_data, data_hash, updated_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                encrypted_data = EXCLUDED.encrypted_data,
                data_hash = EXCLUDED.data_hash,
                updated_at = EXCLUDED.updated_at
            ''', (user_id, encrypted_data, data_hash, datetime.now()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"User settings saved for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save user settings: {e}")
            return False
    
    def get_user_settings(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get decrypted user settings"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT encrypted_data, data_hash FROM user_settings WHERE user_id = %s
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                encrypted_data, data_hash = result
                return self._decrypt_data(encrypted_data, data_hash)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user settings: {e}")
            return None
    
    def save_custom_prompt(self, user_id: str, name: str, prompt_text: str,
                          description: str = "", tags: List[str] = None) -> bool:
        """Save user's single custom prompt (simplified - ignores name/desc/tags)"""
        try:
            prompt_data = {
                "prompt_text": prompt_text
            }
            
            encrypted_prompt, data_hash = self._encrypt_data(prompt_data)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Delete any existing custom prompt for this user
            cursor.execute('DELETE FROM custom_prompts WHERE user_id = %s', (user_id,))
            
            # Insert the new custom prompt (simplified fields)
            cursor.execute('''
                INSERT INTO custom_prompts
                (user_id, name, encrypted_prompt, description, tags, data_hash, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (user_id, "custom_prompt", encrypted_prompt, "",
                  json.dumps([]), data_hash, datetime.now()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Custom prompt saved for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save custom prompt: {e}")
            return False
    
    def get_custom_prompt(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's single custom prompt (simplified)"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT encrypted_prompt, data_hash, created_at, updated_at FROM custom_prompts
                WHERE user_id = %s LIMIT 1
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                encrypted_prompt, data_hash, created_at, updated_at = result
                prompt_data = self._decrypt_data(encrypted_prompt, data_hash)
                return {
                    "prompt_text": prompt_data["prompt_text"],
                    "created_at": created_at.isoformat(),
                    "updated_at": updated_at.isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get custom prompt: {e}")
            return None
    
    def has_custom_prompt(self, user_id: str) -> bool:
        """Check if user has a custom prompt"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT 1 FROM custom_prompts WHERE user_id = %s LIMIT 1', (user_id,))
            result = cursor.fetchone()
            conn.close()
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Failed to check custom prompt: {e}")
            return False
    
    def delete_custom_prompt(self, user_id: str) -> bool:
        """Delete user's custom prompt"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM custom_prompts WHERE user_id = %s', (user_id,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                logger.info(f"Custom prompt deleted for user: {user_id}")
                return True
            else:
                logger.warning(f"No custom prompt found for user: {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete custom prompt: {e}")
            return False
    
    def cleanup_old_data(self, days: int = 365) -> int:
        """Clean up old data (for GDPR compliance)"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Delete old user settings
            cursor.execute('''
                DELETE FROM user_settings 
                WHERE updated_at < NOW() - INTERVAL '%s days'
            ''', (days,))
            
            settings_deleted = cursor.rowcount
            
            # Delete old custom prompts
            cursor.execute('''
                DELETE FROM custom_prompts 
                WHERE updated_at < NOW() - INTERVAL '%s days'
            ''', (days,))
            
            prompts_deleted = cursor.rowcount
            total_deleted = settings_deleted + prompts_deleted
            
            conn.commit()
            conn.close()
            
            logger.info(f"Cleaned up {total_deleted} old records (older than {days} days)")
            return total_deleted
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return 0

# デフォルトプロンプトテンプレート
DEFAULT_PROMPT_TEMPLATES = {
    "counselor": {
        "name": "カウンセラー",
        "prompt_text": """あなたは経験豊富で共感力の高い人生相談カウンセラーです。
相談者の気持ちに寄り添い、実践的で心に響くアドバイスを提供してください。

対応方針:
1. まず相談者の感情を理解し、共感を示す
2. 問題の本質を見極める
3. 具体的で実行可能な解決策を提案する
4. 相談者を励まし、前向きな気持ちになれるよう支援する
5. 必要に応じて専門機関への相談も提案する

絵文字は控えめに使用し、温かみのある文章を心がけてください。""",
        "description": "標準的なカウンセラー役のプロンプトです。",
        "tags": ["カウンセラー", "人生相談", "標準"]
    },
    "big_sister": {
        "name": "お姉さん",
        "prompt_text": """あなたは優しくて頼りになるお姉さんです。
相談者を弟や妹のように思って、親しみやすく、でもしっかりとしたアドバイスをしてください。

特徴:
- 親しみやすい口調で話す
- 時には厳しいことも愛情を持って伝える
- 実体験を交えたアドバイスをする
- 相談者の成長を心から願っている
- 必要な時は背中を押してあげる

「〜だよ」「〜だね」などの親しみやすい語尾を使い、温かい雰囲気を作ってください。""",
        "description": "親しみやすいお姉さんキャラクターです。",
        "tags": ["お姉さん", "親しみやすい", "家族的"]
    },
    "mentor": {
        "name": "メンター",
        "prompt_text": """あなたは豊富な人生経験を持つメンターです。
相談者の成長と成功を支援することが使命です。

アプローチ:
- 質問を通して相談者に自分で答えを見つけさせる
- 長期的な視点でアドバイスする
- 具体的な行動計画を一緒に立てる
- 相談者の強みと可能性を引き出す
- 失敗を学習の機会として捉える

相談者が自分自身の力で問題を解決できるよう導いてください。""",
        "description": "成長を促すメンター役のプロンプトです。",
        "tags": ["メンター", "成長支援", "コーチング"]
    }
}

# Global instance
settings_manager = UserSettingsManager()
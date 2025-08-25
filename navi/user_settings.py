"""
User settings management with encrypted database storage
"""
import os
import sqlite3
import hashlib
import json
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class UserSettingsManager:
    """
    Encrypted user settings manager using SQLite database
    """
    
    def __init__(self, db_path: str = "user_settings.db", key_file: str = "encryption.key"):
        self.db_path = db_path
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
    
    def _init_database(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # User settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id TEXT PRIMARY KEY,
                encrypted_data TEXT NOT NULL,
                data_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Custom prompts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                encrypted_prompt TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                data_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, name)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Set restrictive permissions on database file
        os.chmod(self.db_path, 0o600)
    
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
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_settings (user_id, encrypted_data, data_hash, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, encrypted_data, data_hash, datetime.now().isoformat()))
            
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
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT encrypted_data, data_hash FROM user_settings WHERE user_id = ?
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
        """Save encrypted custom prompt"""
        try:
            prompt_data = {
                "prompt_text": prompt_text,
                "description": description,
                "tags": tags or []
            }
            
            encrypted_prompt, data_hash = self._encrypt_data(prompt_data)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO custom_prompts 
                (user_id, name, encrypted_prompt, description, tags, data_hash, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, name, encrypted_prompt, description, 
                  json.dumps(tags or []), data_hash, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Custom prompt '{name}' saved for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save custom prompt: {e}")
            return False
    
    def get_custom_prompt(self, user_id: str, name: str) -> Optional[Dict[str, Any]]:
        """Get decrypted custom prompt"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT encrypted_prompt, data_hash FROM custom_prompts 
                WHERE user_id = ? AND name = ?
            ''', (user_id, name))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                encrypted_prompt, data_hash = result
                return self._decrypt_data(encrypted_prompt, data_hash)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get custom prompt: {e}")
            return None
    
    def list_custom_prompts(self, user_id: str) -> List[Dict[str, Any]]:
        """List all custom prompts for a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT name, encrypted_prompt, description, tags, data_hash, created_at 
                FROM custom_prompts WHERE user_id = ? ORDER BY created_at DESC
            ''', (user_id,))
            
            results = cursor.fetchall()
            conn.close()
            
            prompts = []
            for row in results:
                name, encrypted_prompt, description, tags_json, data_hash, created_at = row
                
                try:
                    prompt_data = self._decrypt_data(encrypted_prompt, data_hash)
                    prompts.append({
                        "name": name,
                        "prompt_text": prompt_data["prompt_text"],
                        "description": description or prompt_data.get("description", ""),
                        "tags": json.loads(tags_json) if tags_json else prompt_data.get("tags", []),
                        "created_at": created_at
                    })
                except Exception as e:
                    logger.error(f"Failed to decrypt prompt '{name}': {e}")
                    continue
            
            return prompts
            
        except Exception as e:
            logger.error(f"Failed to list custom prompts: {e}")
            return []
    
    def delete_custom_prompt(self, user_id: str, name: str) -> bool:
        """Delete a custom prompt"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM custom_prompts WHERE user_id = ? AND name = ?
            ''', (user_id, name))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                logger.info(f"Custom prompt '{name}' deleted for user: {user_id}")
                return True
            else:
                logger.warning(f"Custom prompt '{name}' not found for user: {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete custom prompt: {e}")
            return False
    
    def cleanup_old_data(self, days: int = 365) -> int:
        """Clean up old data (for GDPR compliance)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Delete old user settings
            cursor.execute('''
                DELETE FROM user_settings 
                WHERE updated_at < datetime('now', '-' || ? || ' days')
            ''', (days,))
            
            settings_deleted = cursor.rowcount
            
            # Delete old custom prompts
            cursor.execute('''
                DELETE FROM custom_prompts 
                WHERE updated_at < datetime('now', '-' || ? || ' days')
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

# Global instance
settings_manager = UserSettingsManager()
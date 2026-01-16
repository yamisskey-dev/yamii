"""
User settings management with encrypted database storage
"""
import hashlib
import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import Any

from cryptography.fernet import Fernet

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

    def _encrypt_data(self, data: dict[str, Any]) -> tuple[str, str]:
        """Encrypt data and create hash for integrity"""
        json_data = json.dumps(data, sort_keys=True)
        encrypted_data = self.cipher_suite.encrypt(json_data.encode()).decode()
        data_hash = hashlib.sha256(json_data.encode()).hexdigest()
        return encrypted_data, data_hash

    def _decrypt_data(self, encrypted_data: str, expected_hash: str) -> dict[str, Any]:
        """Decrypt data and verify integrity"""
        try:
            decrypted_bytes = self.cipher_suite.decrypt(encrypted_data.encode())
            json_data = decrypted_bytes.decode()

            # Verify data integrity
            actual_hash = hashlib.sha256(json_data.encode()).hexdigest()
            if actual_hash != expected_hash:
                raise ValueError("Data integrity check failed")

            return json.loads(json_data)
        except Exception as e:
            logger.error(f"Failed to decrypt data: {e}")
            raise ValueError("Failed to decrypt or verify data integrity")

    def save_user_settings(self, user_id: str, settings: dict[str, Any]) -> bool:
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

            logger.info(f"Settings saved for user: {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save settings for user {user_id}: {e}")
            return False

    def get_user_settings(self, user_id: str) -> dict[str, Any] | None:
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
            logger.error(f"Failed to get settings for user {user_id}: {e}")
            return None

    def save_custom_prompt(self, user_id: str, name: str, prompt_text: str,
                          description: str = "", tags: list[str] = None) -> bool:
        """Save user's single custom prompt (simplified - ignores name/desc/tags)"""
        try:
            prompt_data = {
                "prompt_text": prompt_text
            }

            encrypted_prompt, data_hash = self._encrypt_data(prompt_data)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Delete any existing custom prompt for this user
            cursor.execute('DELETE FROM custom_prompts WHERE user_id = ?', (user_id,))

            # Insert the new custom prompt (simplified fields)
            cursor.execute('''
                INSERT INTO custom_prompts
                (user_id, name, encrypted_prompt, description, tags, data_hash, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, "custom_prompt", encrypted_prompt, "",
                  json.dumps([]), data_hash, datetime.now().isoformat()))

            conn.commit()
            conn.close()

            logger.info(f"Custom prompt saved for user: {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save custom prompt for user {user_id}: {e}")
            return False

    def get_custom_prompt(self, user_id: str) -> dict[str, Any] | None:
        """Get user's single custom prompt (simplified)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT encrypted_prompt, data_hash, created_at, updated_at FROM custom_prompts
                WHERE user_id = ? LIMIT 1
            ''', (user_id,))

            result = cursor.fetchone()
            conn.close()

            if result:
                encrypted_prompt, data_hash, created_at, updated_at = result
                prompt_data = self._decrypt_data(encrypted_prompt, data_hash)
                return {
                    "prompt_text": prompt_data["prompt_text"],
                    "created_at": created_at,
                    "updated_at": updated_at
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get custom prompt for user {user_id}: {e}")
            return None

    def has_custom_prompt(self, user_id: str) -> bool:
        """Check if user has a custom prompt"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT 1 FROM custom_prompts WHERE user_id = ? LIMIT 1', (user_id,))
            result = cursor.fetchone()
            conn.close()

            return result is not None

        except Exception as e:
            logger.error(f"Failed to check custom prompt for user {user_id}: {e}")
            return False

    def delete_custom_prompt(self, user_id: str) -> bool:
        """Delete user's custom prompt"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('DELETE FROM custom_prompts WHERE user_id = ?', (user_id,))

            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()

            if deleted_count > 0:
                logger.info(f"Custom prompt deleted for user: {user_id}")
                return True
            else:
                logger.info(f"No custom prompt found for user: {user_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete custom prompt for user {user_id}: {e}")
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

            logger.info(f"Cleaned up {total_deleted} old records ({settings_deleted} settings, {prompts_deleted} prompts)")
            return total_deleted

        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return 0

# Global instance
settings_manager = UserSettingsManager()

def get_settings_manager() -> UserSettingsManager:
    """Get the global settings manager instance"""
    return settings_manager

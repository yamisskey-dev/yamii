#!/usr/bin/env python3
"""
非同期PostgreSQLデータベースシステム
SQLAlchemy 2.0 + asyncpgを活用したモダンな非同期ORM
"""

import os
import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from contextlib import asynccontextmanager

import asyncpg
from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    AsyncSession, 
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import (
    String, Text, DateTime, JSON, LargeBinary, 
    Integer, Boolean, select, update, delete, text
)
from sqlalchemy.dialects.postgresql import UUID
import uuid

from .encryption import EncryptedData
from .exceptions import NaviException

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 ベースクラス"""
    pass


class EncryptedPrompt(Base):
    """暗号化プロンプトテーブル"""
    __tablename__ = "encrypted_prompts"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    prompt_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # 暗号化データ
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    encryption_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    # メタデータ
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), default="1.0")
    
    # タイムスタンプ
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # フラグ
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)


class UserSession(Base):
    """ユーザーセッションテーブル"""
    __tablename__ = "user_sessions"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    session_token: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    
    # 暗号化キー情報（クライアント公開鍵のハッシュなど）
    key_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    
    # セッション情報
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_accessed: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # セキュリティ
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DatabaseConfig:
    """データベース設定クラス"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "navi",
        user: str = "navi_user",
        password: str = "navi_password",
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        echo: bool = False
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.echo = echo
    
    @property
    def database_url(self) -> str:
        """データベースURL生成"""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """環境変数からの設定読み込み"""
        return cls(
            host=os.getenv("NAVI_DB_HOST", "localhost"),
            port=int(os.getenv("NAVI_DB_PORT", "5432")),
            database=os.getenv("NAVI_DB_NAME", "navi"),
            user=os.getenv("NAVI_DB_USER", "navi_user"),
            password=os.getenv("NAVI_DB_PASSWORD", "navi_password"),
            pool_size=int(os.getenv("NAVI_DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("NAVI_DB_MAX_OVERFLOW", "20")),
            echo=os.getenv("NAVI_DB_ECHO", "false").lower() == "true"
        )


class AsyncDatabase:
    """非同期PostgreSQLデータベース管理クラス"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.engine: Optional[AsyncEngine] = None
        self.session_maker: Optional[async_sessionmaker] = None
        self._connection_pool: Optional[asyncpg.Pool] = None
        
    async def initialize(self) -> None:
        """データベース初期化"""
        try:
            # SQLAlchemyエンジン作成
            self.engine = create_async_engine(
                self.config.database_url,
                echo=self.config.echo,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                # PostgreSQL固有の設定
                connect_args={
                    "command_timeout": 60,
                    "server_settings": {
                        "jit": "off"  # JITを無効化（安定性向上）
                    }
                }
            )
            
            # セッションメーカー作成
            self.session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # 接続テスト
            await self.test_connection()
            
            logger.info("データベース接続が確立されました")
            
        except Exception as e:
            logger.error(f"データベース初期化エラー: {e}")
            raise NaviException(f"Database initialization failed: {e}")
    
    async def test_connection(self) -> bool:
        """接続テスト"""
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"接続テストエラー: {e}")
            return False
    
    async def create_tables(self) -> None:
        """テーブル作成"""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("データベーステーブルを作成しました")
        except Exception as e:
            logger.error(f"テーブル作成エラー: {e}")
            raise NaviException(f"Table creation failed: {e}")
    
    async def drop_tables(self) -> None:
        """テーブル削除（テスト用）"""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            logger.info("データベーステーブルを削除しました")
        except Exception as e:
            logger.error(f"テーブル削除エラー: {e}")
            raise NaviException(f"Table dropping failed: {e}")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """セッション取得コンテキストマネージャー"""
        if not self.session_maker:
            raise NaviException("Database not initialized")
        
        async with self.session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def insert_encrypted_prompt(
        self,
        user_id: str,
        encrypted_data: EncryptedData,
        prompt_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> bool:
        """暗号化プロンプトの挿入"""
        try:
            async with self.get_session() as session:
                prompt = EncryptedPrompt(
                    user_id=user_id,
                    prompt_id=prompt_id,
                    ciphertext=encrypted_data.ciphertext,
                    nonce=encrypted_data.nonce,
                    encryption_metadata=encrypted_data.metadata,
                    title=title,
                    description=description
                )
                
                session.add(prompt)
                await session.commit()
                
                logger.info(f"暗号化プロンプト保存: user={user_id}, prompt={prompt_id}")
                return True
                
        except Exception as e:
            logger.error(f"暗号化プロンプト挿入エラー: {e}")
            return False
    
    async def get_encrypted_prompt(
        self,
        user_id: str,
        prompt_id: str
    ) -> Optional[EncryptedData]:
        """暗号化プロンプトの取得"""
        try:
            async with self.get_session() as session:
                stmt = select(EncryptedPrompt).where(
                    EncryptedPrompt.user_id == user_id,
                    EncryptedPrompt.prompt_id == prompt_id,
                    EncryptedPrompt.is_active == True
                )
                
                result = await session.execute(stmt)
                prompt = result.scalar_one_or_none()
                
                if prompt:
                    return EncryptedData(
                        ciphertext=prompt.ciphertext,
                        nonce=prompt.nonce,
                        metadata=prompt.encryption_metadata
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"暗号化プロンプト取得エラー: {e}")
            return None
    
    async def list_user_prompts(self, user_id: str) -> List[Dict[str, Any]]:
        """ユーザーのプロンプト一覧取得（メタデータのみ）"""
        try:
            async with self.get_session() as session:
                stmt = select(EncryptedPrompt).where(
                    EncryptedPrompt.user_id == user_id,
                    EncryptedPrompt.is_active == True
                ).order_by(EncryptedPrompt.created_at.desc())
                
                result = await session.execute(stmt)
                prompts = result.scalars().all()
                
                return [
                    {
                        "id": prompt.prompt_id,
                        "title": prompt.title,
                        "description": prompt.description,
                        "version": prompt.version,
                        "created_at": prompt.created_at.isoformat(),
                        "updated_at": prompt.updated_at.isoformat(),
                        "is_default": prompt.is_default
                    }
                    for prompt in prompts
                ]
                
        except Exception as e:
            logger.error(f"プロンプト一覧取得エラー: {e}")
            return []
    
    async def update_encrypted_prompt(
        self,
        user_id: str,
        prompt_id: str,
        encrypted_data: EncryptedData,
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> bool:
        """暗号化プロンプトの更新"""
        try:
            async with self.get_session() as session:
                stmt = update(EncryptedPrompt).where(
                    EncryptedPrompt.user_id == user_id,
                    EncryptedPrompt.prompt_id == prompt_id,
                    EncryptedPrompt.is_active == True
                ).values(
                    ciphertext=encrypted_data.ciphertext,
                    nonce=encrypted_data.nonce,
                    encryption_metadata=encrypted_data.metadata,
                    title=title,
                    description=description,
                    updated_at=datetime.utcnow()
                )
                
                result = await session.execute(stmt)
                await session.commit()
                
                return result.rowcount > 0
                
        except Exception as e:
            logger.error(f"暗号化プロンプト更新エラー: {e}")
            return False
    
    async def delete_encrypted_prompt(self, user_id: str, prompt_id: str) -> bool:
        """暗号化プロンプトの削除（論理削除）"""
        try:
            async with self.get_session() as session:
                stmt = update(EncryptedPrompt).where(
                    EncryptedPrompt.user_id == user_id,
                    EncryptedPrompt.prompt_id == prompt_id
                ).values(
                    is_active=False,
                    updated_at=datetime.utcnow()
                )
                
                result = await session.execute(stmt)
                await session.commit()
                
                return result.rowcount > 0
                
        except Exception as e:
            logger.error(f"暗号化プロンプト削除エラー: {e}")
            return False
    
    async def close(self) -> None:
        """データベース接続終了"""
        if self.engine:
            await self.engine.dispose()
            logger.info("データベース接続を終了しました")
    
    def is_connected(self) -> bool:
        """接続状態確認"""
        return self.engine is not None and not self.engine.closed


# グローバルインスタンス
_global_database: Optional[AsyncDatabase] = None


async def get_database() -> AsyncDatabase:
    """グローバルデータベースインスタンスを取得"""
    global _global_database
    
    if _global_database is None:
        config = DatabaseConfig.from_env()
        _global_database = AsyncDatabase(config)
        await _global_database.initialize()
    
    return _global_database


async def init_database() -> AsyncDatabase:
    """データベース初期化"""
    database = await get_database()
    await database.create_tables()
    return database


async def cleanup_database() -> None:
    """データベースクリーンアップ"""
    global _global_database
    
    if _global_database:
        await _global_database.close()
        _global_database = None
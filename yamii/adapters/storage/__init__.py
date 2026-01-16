"""
Storage Adapters
データ永続化の実装

使用例:
    from yamii.adapters.storage.file import FileStorageAdapter
    from yamii.adapters.storage.encrypted_file import EncryptedFileStorageAdapter
"""

from .encrypted_file import EncryptedFileStorageAdapter
from .file import FileStorageAdapter

__all__ = [
    "FileStorageAdapter",
    "EncryptedFileStorageAdapter",
]

"""テスト共通設定"""

import os

# プロンプトのパスはモジュール import 時に解決されるため、
# テスト収集前にリポジトリ内の config/ を指すようにする
# （デフォルトは Docker 用の /app/config でテスト環境には存在しない）
os.environ.setdefault("YAMII_CONFIG_DIR", "config")

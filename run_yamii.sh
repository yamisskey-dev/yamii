#!/bin/bash
# Navi統合サーバー起動スクリプト

set -e

# スクリプトのディレクトリに移動
cd "$(dirname "$0")"

# 環境変数ファイルが存在する場合は読み込む
if [ -f .env ]; then
    echo "環境変数ファイル .env を読み込み中..."
    export $(grep -v '^#' .env | xargs)
fi

# デフォルト値設定
export HOST=${HOST:-"0.0.0.0"}
export PORT=${PORT:-"8000"}
export LOG_LEVEL=${LOG_LEVEL:-"INFO"}
export ENABLE_MISSKEY_BOT=${ENABLE_MISSKEY_BOT:-"false"}
export API_ONLY=${API_ONLY:-"false"}

echo "=== Navi統合サーバー起動設定 ==="
echo "ホスト: $HOST"
echo "ポート: $PORT"
echo "ログレベル: $LOG_LEVEL"
echo "Misskeyボット: $ENABLE_MISSKEY_BOT"
echo "APIのみモード: $API_ONLY"
echo "================================"

# Python仮想環境が存在する場合はアクティベート
if [ -d "venv" ]; then
    echo "Python仮想環境をアクティベート中..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "Python仮想環境をアクティベート中..."
    source .venv/bin/activate
fi

# 必要な依存関係をインストール
echo "依存関係を確認中..."
pip install -e . --quiet

# サーバー起動
echo "Naviサーバーを起動中..."
python start_yamii.py

echo "Naviサーバーが停止しました。"
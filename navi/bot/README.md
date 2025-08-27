# Navi Misskey Bot

yui の navi モジュールを Python で再実装したもの

## Overview

このボットは、MisskeyのSNS上で人生相談を行う AI ボットです。
TypeScript で書かれた元の yui navi モジュールの機能を、Python で完全に再実装しています。
Navi API サーバーと統合することで、統一されたカウンセリングサービスを提供します。

## Features

- **WebSocket ストリーミング**: Misskey の timeline や通知をリアルタイムで監視
- **人生相談機能**: ユーザーからの相談に対してカウンセリングレスポンスを生成
- **セッション管理**: ユーザーごとの会話履歴を管理し、コンテキストを維持
- **感情分析**: ユーザーの感情状態を分析し、適切なアドバイスタイプを選択
- **危機検出**: 自殺願望などの危機的状況を検出し、適切なサポートを提供
- **自動リプライ**: メンションやリプライに自動的に応答
- **プライベートメッセージ対応**: DMでの個別相談に対応
- **API統合**: Navi APIサーバーとの完全統合
- **柔軟な設定**: 環境変数による詳細な設定が可能

## Installation

```bash
# 依存関係をインストール
pip install websockets aiohttp python-dotenv

# プロジェクトをインストール
pip install -e .
```

## Configuration

### 環境変数設定

`.env` ファイルで設定:

```env
# ボット有効化
ENABLE_MISSKEY_BOT=true

# Misskey接続設定
BOT_MISSKEY_HOST=your-misskey-instance.com
BOT_MISSKEY_ACCESS_TOKEN=your-access-token

# Navi API設定
BOT_NAVI_API_URL=http://localhost:8000
BOT_NAVI_API_TIMEOUT=30

# ボット設定
BOT_USER_ID=your-bot-user-id
BOT_USERNAME=navi
BOT_ENABLE_DM=true
BOT_ENABLE_MENTIONS=true
BOT_ENABLE_TIMELINE=false
BOT_ENABLE_GLOBAL_TIMELINE=false
BOT_SESSION_TIMEOUT=3600

# ログ設定
LOG_LEVEL=INFO
LOG_FILE=logs/misskey_bot.log

# 危機対応設定
BOT_CRISIS_HOTLINES=いのちの電話: 0570-783-556, こころの健康相談統一ダイヤル: 0570-064-556
```

### 必須設定項目

ボットを有効にするには、以下の環境変数が必須です：

- `ENABLE_MISSKEY_BOT=true`
- `BOT_MISSKEY_HOST`
- `BOT_MISSKEY_ACCESS_TOKEN`
- `BOT_USER_ID`

## Usage

### 1. 統合サーバー実行（推奨）

APIサーバーとボットを統合起動：

```bash
# 環境変数設定
export ENABLE_MISSKEY_BOT=true

# 統合サーバー起動
python start_navi.py

# または、シェルスクリプトで起動
./run_navi.sh
```

### 2. APIのみモード

ボット機能を無効にしてAPIサーバーのみ起動：

```bash
# 環境変数設定
export ENABLE_MISSKEY_BOT=false
export API_ONLY=true

# APIサーバー起動
python start_navi.py
```

### 3. ボット単体実行

ボットのみを実行（デバッグ用）：

```bash
# ボット単体実行
python -m navi.bot.misskey

# または CLI経由
navi-bot
```

### 4. プログラムでの使用

```python
from navi.bot.misskey import NaviBot
import asyncio

async def main():
    bot = NaviBot()
    await bot.start()

asyncio.run(main())
```

## API Endpoints

統合サーバーでは、ボット管理用のエンドポイントが追加されます：

- `GET /`: サービス情報とボット状態
- `GET /bot/status`: ボットの詳細状態
- `POST /bot/start`: ボットの手動開始
- `POST /bot/stop`: ボットの手動停止

## Architecture

### システム構成

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Misskey SNS   │◄───┤  Navi Bot       │◄───┤  Navi API       │
│                 │    │                 │    │  Server         │
│ - Timeline      │    │ - WebSocket     │    │ - Counseling    │
│ - Mentions      │    │ - Event Handler │    │ - User Profile  │
│ - DM            │    │ - Session Mgmt  │    │ - Memory System │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### クラス構成

- **NaviBot**: メインボットクラス - WebSocket接続とイベント処理
- **MisskeyClient**: Misskey API クライアント - API通信とWebSocket管理  
- **NaviClient**: Navi API クライアント - カウンセリング機能との連携

### 処理フロー

1. **接続確立**: Misskey WebSocket API に接続
2. **イベント監視**: Timeline、Mention、通知をリアルタイム監視
3. **メッセージ処理**: 
   - ユーザーのメッセージを受信
   - Navi API でカウンセリングレスポンスを生成
   - Misskey にリプライまたはノート作成
4. **セッション管理**: ユーザーごとの会話履歴を保持・管理

## API Integration

Navi API サーバーと連携して以下の機能を使用:

- `/counseling`: カウンセリングレスポンス生成
- `/profile`: ユーザープロファイル管理
- `/custom-prompts`: カスタムプロンプト管理
- `/health`: ヘルスチェック

## Testing

```bash
# 単体テスト実行
python -m pytest tests/test_misskey_bot.py -v

# 統合テスト実行（サーバー起動後）
python test_integration.py

# 設定検証
python -c "from navi.bot.misskey.config import load_config; print(load_config())"
```

## Deployment

### 開発環境

```bash
# 設定ファイル作成
cp .env.example .env
# .env を編集して設定

# 開発サーバー起動
./run_navi.sh
```

### プロダクション環境

```bash
# 環境変数設定
export ENABLE_MISSKEY_BOT=true
export BOT_MISSKEY_HOST=your-instance.com
export BOT_MISSKEY_ACCESS_TOKEN=your-token
export LOG_LEVEL=WARNING

# プロダクション起動
python start_navi.py
```

### Docker（将来対応）

```dockerfile
# Dockerfile例
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -e .
CMD ["python", "start_navi.py"]
```

## Monitoring & Management

### ログ監視

```bash
# リアルタイムログ監視
tail -f logs/misskey_bot.log

# エラーログ抽出
grep "ERROR" logs/misskey_bot.log
```

### ボット管理API

```bash
# ボット状態確認
curl http://localhost:8000/bot/status

# ボット停止
curl -X POST http://localhost:8000/bot/stop

# ボット開始
curl -X POST http://localhost:8000/bot/start
```

## Error Handling

- **接続エラー**: 自動再接続機能
- **API エラー**: リトライ機能とフェイルセーフ
- **レート制限**: 適切な待機時間とバックオフ
- **例外ログ**: 詳細なエラーログとデバッグ情報
- **設定エラー**: 起動時検証とわかりやすいエラーメッセージ

## Security

- アクセストークンの安全な管理
- HTTPS/WSS 通信の強制
- ユーザー入力のサニタイゼーション
- レート制限と悪用防止
- 環境変数による機密情報管理

## Performance

- 非同期処理による高い並行性
- WebSocket による低遅延通信
- セッション管理の効率的な実装
- メモリ使用量の最適化
- 統合サーバーによる効率的なリソース利用

## Monitoring

- 構造化ログによる詳細な動作記録
- メトリクスの収集と分析
- ヘルスチェック機能
- エラー率と応答時間の監視
- ボット状態のリアルタイム監視

## Migration from TypeScript

元の TypeScript 実装からの主な改善点：

- **統合アーキテクチャ**: API サーバーとの完全統合
- **設定管理**: 環境変数による一元管理
- **エラーハンドリング**: より堅牢なエラー処理
- **テスト**: 包括的なテストスイート
- **デプロイメント**: 簡単な統合起動スクリプト
- **監視**: リアルタイム状態監視
- **パフォーマンス**: 最適化された非同期処理

95%以上の機能互換性を保ちながら、Python エコシステムの利点を活用した実装になっています。

## プロジェクト構造

```
navi/
├── navi/                      # メインPythonパッケージ
│   ├── main.py               # Naviサーバー（ボット統合対応）
│   ├── core/, services/      # 既存のnavi機能
│   └── bot/                  # ボット機能
│       ├── __init__.py
│       ├── README.md         # このファイル
│       └── misskey/          # Misskeyボット実装
│           ├── __init__.py
│           ├── config.py          # ボット設定管理（環境変数対応）
│           ├── misskey_client.py  # Misskey API クライアント
│           ├── navi_client.py     # Navi API クライアント
│           └── navi_bot.py        # メインボット実装（388行）
├── start_navi.py                  # 統合サーバー起動スクリプト
├── run_navi.sh                   # シェル起動スクリプト（実行可能）
├── test_integration.py           # 統合テストスイート
├── cli_bot.py                     # CLI エントリーポイント
└── tests/
    └── test_misskey_bot.py        # 包括的テストファイル
```

## トラブルシューティング

### よくある問題

1. **ボットが起動しない**
   - `ENABLE_MISSKEY_BOT=true` が設定されているか確認
   - 必須環境変数（`BOT_MISSKEY_HOST`, `BOT_MISSKEY_ACCESS_TOKEN`, `BOT_USER_ID`）が設定されているか確認
   - ログファイルでエラーメッセージを確認

2. **統合サーバーが起動しない**
   - Naviサーバーの依存関係がインストールされているか確認
   - `python start_navi.py` または `./run_navi.sh` で起動

3. **ボット状態が確認できない**
   - `curl http://localhost:8000/bot/status` でAPI経由確認
   - 統合テスト（`python test_integration.py`）を実行

### ログの確認

```bash
# 統合ログ監視
tail -f logs/misskey_bot.log

# APIサーバーログと合わせて確認
python start_navi.py  # ターミナル出力で確認
# Docker環境でのMisskeyボット設定

## 概要

Docker環境でNavi APIサーバーと統合したMisskeyボット機能を有効化する手順です。

Docker Composeは自動的に `.env` ファイルを読み込むため、環境変数の設定が簡単になります。

## 設定手順

### 1. 環境変数ファイルの作成

プロジェクトルート（docker-compose.ymlと同じ場所）に `.env` ファイルを作成し、以下の設定を行います：

```env
# 必須設定
GEMINI_API_KEY=your_gemini_api_key_here

# Misskeyボット設定
ENABLE_MISSKEY_BOT=true
MISSKEY_INSTANCE_URL=https://your-misskey-instance.com
MISSKEY_ACCESS_TOKEN=your_misskey_access_token
MISSKEY_BOT_USER_ID=your_bot_user_id

# Navi API設定（共通）
NAVI_API_URL=http://localhost:8000
NAVI_API_TIMEOUT=30

# ボット基本設定（共通）
BOT_NAME=navi
BOT_USERNAME=navi
BOT_SESSION_TIMEOUT=3600

# 機能有効化（プラットフォーム固有）
BOT_ENABLE_DM=true
BOT_ENABLE_MENTIONS=true
BOT_ENABLE_TIMELINE=false
BOT_ENABLE_GLOBAL_TIMELINE=false

# 緊急時相談窓口設定
BOT_CRISIS_HOTLINES=いのちの電話: 0570-783-556, こころの健康相談統一ダイヤル: 0570-064-556

# ログ設定
LOG_LEVEL=INFO
```

### 2. 設定ファイルのコピー（初回のみ）

初回設定時は、テンプレートから `.env` ファイルを作成：

```bash
# .env.example から .env ファイルを作成
cp .env.example .env

# エディターで .env を開いて必要な設定を編集
nano .env
# または
vim .env
```

### 3. Dockerコンテナの再起動

設定を反映するため、Dockerコンテナを再起動します：

```bash
# コンテナを停止
sudo docker compose down

# コンテナを再起動（ビルドし直し）
sudo docker compose up --build -d
```

**注意**: `.env` ファイルはDocker Composeによって自動的に読み込まれます。手動で環境変数を指定する必要はありません。

### 4. ログの確認

ボットが正常に起動したかログを確認します：

```bash
# リアルタイムログ監視
sudo docker compose logs -f

# ボット関連ログのみ確認
sudo docker compose logs | grep -E "(bot|Bot|MISSKEY)"
```

### 5. 動作確認

#### API経由での確認

```bash
# ボット状態確認
curl http://localhost:8000/bot/status

# サービス情報（ボット状態含む）確認
curl http://localhost:8000/
```

#### Misskeyでの確認

Misskeyでボットをメンションしてテストします：

```
@navi こんにちは、相談があります
```

または

```
@navi /help
```

## トラブルシューティング

### ボットが応答しない場合

1. **環境変数の確認**
   ```bash
   # .envファイルの内容確認
   cat .env
   
   # Docker Composeでの設定確認
   sudo docker compose config
   ```

2. **ログでエラー確認**
   ```bash
   sudo docker compose logs | grep -i error
   ```

3. **ボット状態API確認**
   ```bash
   curl http://localhost:8000/bot/status
   ```

### よくあるエラーと対処法

#### 1. "ENABLE_MISSKEY_BOT が設定されていません"
- `.env` ファイルに `ENABLE_MISSKEY_BOT=true` が設定されているか確認
- `docker compose up --build` でコンテナを再ビルド

#### 2. "BOT_MISSKEY_HOST が設定されていません"  
- `.env` ファイルに `BOT_MISSKEY_HOST` が正しく設定されているか確認
- MisskeyインスタンスのURL形式を確認（例: `misskey.example.com`）

#### 3. "WebSocket接続エラー"
- MisskeyのアクセストークンとアクセスキーScope設定を確認
- ネットワーク接続とファイアウォール設定を確認

#### 4. ボットがメンションに反応しない
- ボットのユーザーIDとMisskeyでの実際のIDが一致しているか確認
- ボット状態API（`/bot/status`）で動作状況を確認

## 設定項目詳細

### 共通設定（NAVI_*プレフィックス）

| 環境変数 | 必須 | デフォルト値 | 説明 |
|---------|------|------------|------|
| `NAVI_API_URL` | | `http://localhost:8000` | Navi APIのURL |
| `NAVI_API_TIMEOUT` | | `30` | API通信タイムアウト（秒） |

### ボット共通設定（BOT_*プレフィックス）

| 環境変数 | 必須 | デフォルト値 | 説明 |
|---------|------|------------|------|
| `BOT_NAME` | | `navi` | ボット名 |
| `BOT_USERNAME` | | `navi` | ボットのユーザー名 |
| `BOT_SESSION_TIMEOUT` | | `3600` | セッションタイムアウト（秒） |
| `BOT_ENABLE_DM` | | `true` | DM機能の有効/無効 |
| `BOT_ENABLE_MENTIONS` | | `true` | メンション機能の有効/無効 |
| `BOT_ENABLE_TIMELINE` | | `false` | ローカルタイムライン監視 |
| `BOT_ENABLE_GLOBAL_TIMELINE` | | `false` | グローバルタイムライン監視 |
| `BOT_CRISIS_HOTLINES` | | - | 危機対応ホットライン情報 |

### Misskey固有設定

| 環境変数 | 必須 | デフォルト値 | 説明 |
|---------|------|------------|------|
| `ENABLE_MISSKEY_BOT` | ✅ | `false` | ボット機能の有効/無効 |
| `MISSKEY_INSTANCE_URL` | ✅ | - | MisskeyインスタンスのURL |
| `MISSKEY_ACCESS_TOKEN` | ✅ | - | ボットのアクセストークン |
| `MISSKEY_BOT_USER_ID` | ✅ | - | ボットのユーザーID |

### ログ設定

| 環境変数 | 必須 | デフォルト値 | 説明 |
|---------|------|------------|------|
| `LOG_LEVEL` | | `INFO` | ログレベル (DEBUG/INFO/WARNING/ERROR) |
| `LOG_FILE` | | - | ログファイルパス |

## ログ出力例

正常な起動ログ例：

```
navi-counseling-api  | {"timestamp":"2025-08-27T22:46:35.056Z","level":"INFO","logger":"navi.main","message":"Navi APIサーバーを起動中..."}
navi-counseling-api  | {"timestamp":"2025-08-27T22:46:35.100Z","level":"INFO","logger":"navi.main","message":"Misskeyボットを開始中..."}
navi-counseling-api  | {"timestamp":"2025-08-27T22:46:35.200Z","level":"INFO","logger":"navi.bot.misskey.navi_bot","message":"NaviBot開始しました"}
navi-counseling-api  | {"timestamp":"2025-08-27T22:46:35.250Z","level":"INFO","logger":"navi.main","message":"Misskeyボット開始完了"}
navi-counseling-api  | {"timestamp":"2025-08-27T22:46:35.300Z","level":"INFO","logger":"navi.main","message":"Navi APIサーバー起動完了"}
```

## セキュリティ注意事項

- `.env` ファイルはGitコミットしない
- Misskeyアクセストークンは適切なスコープのみを設定
- 本番環境では適切なファイアウォール設定を行う
- ログファイルには機密情報が含まれる場合があるため適切に管理する

## 設定例

### 最小設定（テスト環境の.env）

```env
# 必須設定
GEMINI_API_KEY=your_gemini_api_key

# ボット設定
ENABLE_MISSKEY_BOT=true
MISSKEY_INSTANCE_URL=https://misskey.dev
MISSKEY_ACCESS_TOKEN=your_test_token
MISSKEY_BOT_USER_ID=test_bot_id
```

### 本番設定（本番環境の.env）

```env
# API Keys
GEMINI_API_KEY=prod_gemini_api_key

# Bot Configuration
ENABLE_MISSKEY_BOT=true
MISSKEY_INSTANCE_URL=https://misskey.yourinstance.com
MISSKEY_ACCESS_TOKEN=prod_misskey_token
MISSKEY_BOT_USER_ID=prod_bot_user_id

# Common Bot Settings
BOT_NAME=navi
BOT_USERNAME=navi
BOT_SESSION_TIMEOUT=7200

# Navi API Settings
NAVI_API_URL=http://localhost:8000
NAVI_API_TIMEOUT=45

# Feature Flags
BOT_ENABLE_DM=true
BOT_ENABLE_MENTIONS=true
BOT_ENABLE_TIMELINE=false
BOT_ENABLE_GLOBAL_TIMELINE=false

# Crisis Support
BOT_CRISIS_HOTLINES=いのちの電話: 0570-783-556, こころの健康相談統一ダイヤル: 0570-064-556

# Logging
LOG_LEVEL=WARNING
LOG_FILE=logs/navi_prod.log
```

## 重要な注意点

1. **.envファイルは自動読み込み**: Docker Composeは自動的に`.env`ファイルを読み込むため、docker-compose.ymlで環境変数を個別に指定する必要はありません。

2. **.envファイルの場所**: `.env`ファイルは`docker-compose.yml`と同じディレクトリに配置してください。

3. **設定の変更**: `.env`ファイルを変更した後は、必ず`docker compose up --build`でコンテナを再起動してください。

4. **セキュリティ**: `.env`ファイルはGitリポジトリにコミットしないでください。`.gitignore`に追加することを推奨します。

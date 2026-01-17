# Yamii

Zero-Knowledge メンタルヘルスAI相談API

## 特徴

- **Zero-Knowledge**: サーバーは会話内容を保存・閲覧しない
- **クライアント側暗号化**: ユーザーデータはユーザーのみ復号可能
- **ノーログ**: 会話履歴はセッション中のみ保持
- **Misskey OAuth**: Misskeyアカウントで認証
- **汎用API**: 任意のフロントエンドから利用可能

## アーキテクチャ

```
Yamix（または、任意のWebアプリ）
    ├── Misskeyログイン（OAuth）
    ├── クライアント側暗号化（Web Crypto API）
    └── 会話はブラウザ内のみ（ノーログ）
              ↓
Yamii API v3.0.0
    ├── /v1/auth/*       - Misskey OAuth認証
    ├── /v1/user-data/*  - 暗号化Blob保存（Zero-Knowledge）
    ├── /v1/counseling   - AIカウンセリング（ノーログ）
    └── /v1/health       - ヘルスチェック
              ↓
OpenAI API
```

## 関連プロジェクト

| プロジェクト | 説明 |
|-------------|------|
| **Yamii** (このリポジトリ) | Zero-Knowledge API サーバー |
| [**Yamix**](https://github.com/yamisskey-dev/yamix) | 公式フロントエンド Webアプリ |

Yamiiは汎用的なAPIサーバーとして設計されているため、Yamix以外のフロントエンドからも利用できます。

## デプロイ（Docker）

```bash
# 1. 環境変数を設定
cp .env.example .env
nano .env  # OPENAI_API_KEY を設定

# 2. 起動
docker compose up -d

# 3. 確認
curl http://localhost:8000/v1/health
```

**必須環境変数** (`.env`):
```bash
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
```

## ローカル開発

```bash
# 依存関係インストール
uv sync

# サーバー起動（FastAPI CLI）
uv run fastapi dev yamii/api/main.py
```

## APIドキュメント

サーバー起動後、以下のURLでAPIドキュメントを確認できます：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 主要エンドポイント

### 認証

```
POST /v1/auth/start     # Misskey OAuth開始
POST /v1/auth/callback  # OAuth コールバック
GET  /v1/auth/session   # セッション情報取得
POST /v1/auth/logout    # ログアウト
```

### ユーザーデータ（Zero-Knowledge）

```
PUT    /v1/user-data/blob   # 暗号化データ保存
GET    /v1/user-data/blob   # 暗号化データ取得
DELETE /v1/user-data/blob   # データ削除（GDPR対応）
```

### カウンセリング

```
POST /v1/counseling
```

**リクエスト:**
```json
{
  "message": "相談内容",
  "user_id": "ユーザーID",
  "custom_prompt": "（オプション）ユーザーについての情報"
}
```

**レスポンス:**
```json
{
  "response": "AIの応答",
  "session_id": "セッションID",
  "emotion_analysis": {
    "primary_emotion": "stress",
    "intensity": 0.6,
    "is_crisis": false
  }
}
```

## 主要機能

### 感情分析

メッセージから感情を自動検出:
- happiness, sadness, anxiety, anger, loneliness
- depression, stress, confusion, hope, neutral

### 危機検出

「死にたい」等のキーワードを検出し、専門機関への相談を案内。

### 関係性フェーズ

対話を重ねることでフェーズが進行:

| フェーズ | 説明 |
|---------|------|
| STRANGER | 初対面。丁寧な対応 |
| ACQUAINTANCE | 顔見知り。過去の会話を参照 |
| FAMILIAR | 親しい関係。自然な会話 |
| TRUSTED | 信頼関係。率直なやり取り |

### PII匿名化

OpenAI APIへの送信前に個人情報を自動マスク:
- 電話番号、メールアドレス、住所
- 生年月日、名前
- マイナンバー、カード番号

## 環境変数

| 変数 | 必須 | デフォルト | 説明 |
|------|------|-----------|------|
| `OPENAI_API_KEY` | ✅ | - | OpenAI APIキー |
| `OPENAI_MODEL` | - | gpt-4.1 | 使用モデル |
| `YAMII_DATA_DIR` | - | data | データ保存先 |
| `YAMII_DEBUG` | - | false | デバッグモード |
| `YAMII_API_KEYS` | - | - | API認証キー（カンマ区切り） |
| `API_HOST` | - | http://localhost:8000 | APIベースURL |
| `FRONTEND_URL` | - | http://localhost:3000 | フロントエンドURL |

## 開発

```bash
# テスト実行
uv run pytest tests/ -v

# 型チェック
uv run ty check yamii/

# フォーマット
uv run ruff format yamii/ tests/
```

## プロジェクト構造

```
yamii/
├── api/              # FastAPI エンドポイント
│   └── routes/       # auth, counseling, user, user_data, commands
├── domain/           # ドメインモデル・サービス
│   ├── models/       # UserState, Relationship, Emotion
│   ├── services/     # Emotion, Counseling
│   └── ports/        # インターフェース定義
├── adapters/         # 外部サービス実装
│   ├── ai/           # OpenAI（PII匿名化付き）
│   └── storage/      # ファイル / 暗号化Blobストレージ
└── core/             # ログ、設定
```

## ライセンス

MIT

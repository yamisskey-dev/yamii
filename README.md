# Yamii

Zero-Knowledge メンタルヘルスAI相談API

## 特徴

- **Zero-Knowledge（オプション）**: `/v1/user-data/blob`でクライアント側暗号化データ保存に対応
- **ノーログ**: 会話履歴はサーバーに保存しない（クライアント管理）
- **Misskey OAuth**: Misskeyアカウントで認証可能
- **API Key認証**: シンプルなAPI Key認証もサポート
- **汎用API**: 任意のフロントエンドから利用可能
- **GDPR対応**: データエクスポート・削除機能を標準実装

## アーキテクチャ

```
Yamix（または、任意のWebアプリ）
    ├── Misskeyログイン（OAuth） or API Key認証
    ├── クライアント側暗号化（Web Crypto API、オプション）
    └── 会話履歴はクライアント管理（ノーログ）
              ↓
Yamii API v3.0.0 (FastAPI)
    ├── /v1/auth/*       - Misskey OAuth認証
    ├── /v1/counseling   - AIカウンセリング（ノーログ）
    ├── /v1/users/*      - ユーザー管理（GDPR対応）
    ├── /v1/user-data/*  - 暗号化Blob保存（Zero-Knowledge）
    ├── /v1/commands/*   - Botコマンド処理
    └── /v1/health, /docs, /redoc
              ↓
OpenAI API
```

詳細なエンドポイントは [Swagger UI](http://localhost:8000/docs) で確認できます。

## 関連プロジェクト

| プロジェクト | 説明 |
|-------------|------|
| **Yamii** (このリポジトリ) | Zero-Knowledge API サーバー |
| [**Yamix**](https://github.com/yamisskey-dev/yamix) | 公式フロントエンド Webアプリ |

Yamiiは汎用的なAPIサーバーとして設計されているため、Yamix以外のフロントエンドからも利用できます。

### Yamixとの統合

YamixはYamiiを以下のように利用します：

- **認証方式**: API Key認証（`X-API-Key` ヘッダー）
  - Yamix自体のユーザー認証はMisskey MiAuthを使用
  - Yamii APIへのアクセスはYamixサーバー経由でAPI Key認証
- **使用エンドポイント**:
  - `POST /v1/counseling` - AI相談機能
  - `GET /v1/users/{userId}` - ユーザー情報取得
  - `PUT /v1/users/{userId}` - プロファイル更新
  - `DELETE /v1/users/{userId}` - AI学習データ削除
  - `GET /v1/health` - ヘルスチェック
- **会話履歴管理**: Yamixのデータベースで管理（Yamiiはノーログ）
- **Zero-Knowledge Blob**: 現在未使用（将来的な拡張用）

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

Yamii APIは **OpenAPI 3.0** 標準に準拠しています。FastAPIが自動生成する対話的なAPIドキュメントをご利用ください。

- **Swagger UI**: http://localhost:8000/docs - 対話的なAPIドキュメント
- **ReDoc**: http://localhost:8000/redoc - 見やすいリファレンス

### 認証方式

**1. Misskey OAuth (MiAuth):**
- `/v1/user-data/*` エンドポイントで使用
- OAuth Bearer トークンが必要

**2. API Key認証:**
- `/v1/counseling`, `/v1/users/*`, `/v1/commands/*` で使用
- `X-API-Key` ヘッダーで認証

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/v1/counseling
```

### 主要な概念

**ノーログ設計:**
- 会話履歴はサーバーに保存されません
- `conversation_history` パラメータでクライアント側から送信
- セッション中のみ使用され、永続化されません

**Zero-Knowledge (オプション):**
- `/v1/user-data/blob` でクライアント側暗号化データを保存可能
- サーバーは暗号文の内容を知ることができません

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

### Botコマンド（オプション）

`/v1/commands/*` エンドポイントは、Botプラットフォーム統合用の便利機能です（help, status, classify, export, clear_data）。一般的なWebアプリでは不要です。

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

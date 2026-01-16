# Yamii

**やみ**の中の**Mii**へ

Misskey向け人生相談AIボット

## デプロイ（Docker）

```bash
# 1. 環境変数を設定
cp .env.example .env
nano .env  # 4つの必須項目を設定

# 2. 起動
docker compose up -d

# 3. 確認
curl http://localhost:8000/v1/health
```

**必須環境変数** (`.env`):
```bash
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
MISSKEY_INSTANCE_URL=https://your-misskey-instance.com
MISSKEY_ACCESS_TOKEN=your_misskey_access_token
MISSKEY_BOT_USER_ID=your_bot_user_id
```

Misskey設定があればBotが自動起動します。

## ローカル開発

```bash
# 依存関係インストール
uv sync

# サーバー起動
uv run uvicorn yamii.api:app --reload --port 8000
```

### 動作確認

```bash
# ヘルスチェック
curl http://localhost:8000/v1/health

# カウンセリング
curl -X POST http://localhost:8000/v1/counseling \
  -H "Content-Type: application/json" \
  -d '{"message": "最近仕事でストレスを感じています", "user_id": "user123"}'
```

## API

### カウンセリング

```
POST /v1/counseling
```

**リクエスト:**
```json
{
  "message": "相談内容",
  "user_id": "ユーザーID",
  "session_id": "セッションID（継続会話時）"
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
  },
  "is_crisis": false
}
```

### ユーザー管理

```
GET  /v1/users/{user_id}      # ユーザー情報取得
DELETE /v1/users/{user_id}    # データ削除（GDPR対応）
```

### ヘルスチェック

```
GET /v1/health
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

```bash
OPENAI_API_KEY=sk-...          # 必須
OPENAI_MODEL=gpt-4.1           # デフォルト: gpt-4.1
YAMII_DATA_DIR=data            # データ保存先
```

## 開発

```bash
# テスト実行
uv run pytest tests/ -v

# 型チェック
uv run ty check yamii/

# フォーマット
uv run ruff format yamii/ tests/
```

## アーキテクチャ

```
yamii/
├── api/              # FastAPI エンドポイント
│   └── routes/       # counseling, user, outreach, commands
├── domain/           # ドメインモデル・サービス
│   ├── models/       # UserState（統合ユーザー状態）, Episode, Relationship
│   ├── services/     # Emotion, Counseling, Outreach
│   └── ports/        # インターフェース定義（IAIProvider, IStorage）
├── adapters/         # 外部サービス実装
│   ├── ai/           # OpenAI（PII匿名化付き）
│   └── storage/      # ファイル / 暗号化ストレージ
├── core/             # 暗号化、ログ、設定
└── bot/misskey/      # Misskey Bot（薄型: API経由で処理）
```

## ライセンス

MIT

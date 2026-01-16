# Yamii

**やみ**の中の**Mii**へ

## クイックスタート

### 1. 環境設定

```bash
git clone <repository-url>
cd yamii

# 依存関係インストール
uv sync

# 環境変数設定
cp .env.example .env
# .envでOPENAI_API_KEYを設定
```

### 2. サーバー起動

```bash
uv run uvicorn yamii.api:app --reload --port 8000
```

### 3. 動作確認

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
├── domain/           # ドメインモデル・サービス
│   ├── models/       # UserState, Episode, Relationship
│   ├── services/     # Emotion, Counseling, Outreach
│   └── ports/        # インターフェース定義
├── adapters/         # 外部サービス実装
│   ├── ai/           # OpenAI
│   └── storage/      # ファイルストレージ
├── relationship/     # 関係性管理システム
├── core/             # 暗号化、ログ、設定
└── bot/misskey/      # Misskey Bot
```

## ドキュメント

- [アーキテクチャ](docs/architecture.md)
- [Misskey Bot](docs/misskey-bot.md)
- [プライバシー保護](docs/privacy.md)

## ライセンス

MIT

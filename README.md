# YAMII - Networked Artificial Virtual Intelligence

## 🌟 特徴

### 🎯 核心機能
- **専門特化**: 人生相談に最適化されたAI応答
- **感情分析**: 8種類の感情を自動検出・分析
- **危機検知**: 自動的な緊急事態検出とサポート
- **セッション管理**: 継続的な会話履歴管理
- **記憶システム**: ユーザー毎の会話記録

### 🎨 カスタマイズ機能
- **YAMII.mdプロンプト**: 外部マークダウンファイルでプロンプト管理
- **カスタムプロンプト**: ユーザー独自のキャラクター設定
- **テンプレートシステム**: 事前定義されたプロンプトテンプレート

### 🏗️ 技術的特徴
- **FastAPI**: 高性能なPython Webフレームワーク
- **Docker対応**: 本番環境対応のコンテナ化
- **マイクロサービス**: 独立したAPI設計
- **TDD**: テスト駆動開発による高品質実装

## 🚀 クイックスタート

### 1. 環境設定

```bash
# リポジトリクローン
git clone <repository-url>
cd yamii

# 環境変数設定
cp .env.example .env
# .envファイルでGEMINI_API_KEYを設定
```

### 2. Docker起動

```bash
# コンテナビルド・起動
docker-compose up -d --build

# ヘルスチェック
curl http://localhost:8000/health
```

### 3. 基本的な使用

```bash
# 人生相談API
curl -X POST "http://localhost:8000/counseling" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "最近仕事でストレスを感じています",
    "user_id": "user123"
  }'
```

## 📚 API リファレンス

### 人生相談API

#### `POST /counseling`
人生相談のメインエンドポイント

**リクエスト:**
```json
{
  "message": "相談内容",
  "user_id": "ユーザーID",
  "user_name": "ユーザー名（任意）",
  "session_id": "セッションID（任意）",
  "prompt_id": "プロンプトID（任意）",
  "custom_prompt_id": "カスタムプロンプトID（任意）"
}
```

**レスポンス:**
```json
{
  "response": "AI の回答",
  "session_id": "セッションID",
  "timestamp": "2024-01-01T00:00:00",
  "emotion_analysis": {
    "primary_emotion": "stress",
    "intensity": 1,
    "is_crisis": false
  },
  "advice_type": "career",
  "follow_up_questions": ["フォローアップ質問"],
  "is_crisis": false
}
```

### プロンプト管理API

#### `GET /prompts`
利用可能なプロンプト一覧取得

#### `GET /prompts/{prompt_id}`
特定プロンプトの詳細取得

#### `POST /prompts/reload`
YAMII.mdファイルを再読み込み

#### `GET /prompts/search/{query}`
プロンプト検索

### カスタムプロンプトAPI

#### `POST /custom-prompts?user_id={user_id}`
カスタムプロンプト作成

#### `GET /custom-prompts?user_id={user_id}`
ユーザーのカスタムプロンプト一覧

#### `PUT /custom-prompts/{prompt_id}?user_id={user_id}`
カスタムプロンプト更新

#### `DELETE /custom-prompts/{prompt_id}?user_id={user_id}`
カスタムプロンプト削除

## 🎨 プロンプト管理

### YAMII.mdファイル

外部プロンプト管理システムです。

```markdown
### My Custom Character
**ID**: `my_character`  
**名前**: カスタムキャラクター  
**説明**: 独自のキャラクター設定

あなたは[キャラクター設定]です。
[具体的な指示や性格設定]

---
```

### 事前定義プロンプト

- `default_counselor`: 標準カウンセラー
- `friendly_sister`: 優しいお姉さん
- `wise_mentor`: 人生の師匠
- `cat_character`: 猫キャラクター
- `professional_coach`: プロフェッショナルコーチ
- `spiritual_guide`: スピリチュアルガイド

### プロンプト使用例

```bash
# 猫キャラクターで相談
curl -X POST "http://localhost:8000/counseling" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "今日は疲れました",
    "user_id": "user123",
    "prompt_id": "cat_character"
  }'
```

## 🧪 テスト

### 基本テスト実行

```bash
# 基本機能テスト
python test_aichat.py

# カスタムプロンプトテスト
python test_custom_prompts.py

# YAMII.mdローダーテスト（新しいmarkdown-it版）
python -c "from yamii.core.markdown_loader import get_yamii_loader; loader = get_yamii_loader(); print('Loaded prompts:', len(loader.prompts))"
```

### 統合テスト

```bash
# yui統合テスト
node yui/test_yamii_integration.js
```

## 🏗️ 開発環境

### ローカル開発

```bash
# 仮想環境作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt

# 開発サーバー起動
uvicorn yamii.main:app --reload --host 0.0.0.0 --port 8000
```

### 依存関係

- **Python**: 3.9+
- **FastAPI**: 0.104.1+
- **uvicorn**: 0.24.0+
- **pydantic**: 2.5.0+
- **aiohttp**: 3.9.1+
- **Google Gemini API**: 必須

## 🐳 Docker デプロイ

### 本番環境デプロイ

```bash
# 本番用起動
docker-compose -f docker-compose.yml up -d

# ログ確認
docker-compose logs -f

# スケールアップ
docker-compose up --scale yamii=3
```

### 設定オプション

環境変数で動作をカスタマイズできます：

```bash
# .env ファイル
GEMINI_API_KEY=your_api_key_here
YAMII_DEFAULT_PROMPT=default_counselor
YAMII_CRISIS_MODE=true
YAMII_EMOTION_ANALYSIS=true
```

## 📊 監視・運用

### ヘルスチェック

```bash
curl http://localhost:8000/health
```

### ログ監視

```bash
# Docker ログ
docker-compose logs -f yamii

# アプリケーションログ
tail -f yamii/logs/app.log
```

### メトリクス

- セッション数
- 相談回数
- 感情分析統計
- 危機検知件数

## 🛡️ セキュリティ

### プライバシー保護

- セッション削除機能
- 自動データ期限切れ（30日）
- ユーザー毎のデータ分離

### 危機対応

自動的な危機検知機能により、以下の場合に専門機関への相談を推奨：

- 自殺関連語句の検出
- 深刻な精神状態の表現
- 緊急性の高い相談内容

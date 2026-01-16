# アーキテクチャ

## 概要

Yamiiはクリーンアーキテクチャに基づいた設計を採用。

```
┌─────────────────────────────────────────────────────────┐
│                      API Layer                          │
│                    (FastAPI)                            │
├─────────────────────────────────────────────────────────┤
│                   Domain Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   Models    │  │  Services   │  │    Ports    │     │
│  │ - UserState │  │ - Emotion   │  │ - IStorage  │     │
│  │ - Episode   │  │ - Counsel   │  │ - IAIProvider│    │
│  │ - Relation  │  │ - Outreach  │  │             │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
├─────────────────────────────────────────────────────────┤
│                  Adapter Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   OpenAI    │  │    File     │  │   Misskey   │     │
│  │   Adapter   │  │   Storage   │  │     Bot     │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
```

## レイヤー

### API Layer (`yamii/api/`)

- FastAPIによるREST API
- リクエスト/レスポンスのバリデーション
- 依存性注入

### Domain Layer (`yamii/domain/`)

#### Models

- `UserState`: ユーザーの状態（フェーズ、信頼スコア等）
- `Episode`: 長期記憶（重要な対話の要約）
- `RelationshipPhase`: 関係性フェーズ（STRANGER→TRUSTED）

#### Services

- `EmotionService`: 感情分析
- `CounselingService`: カウンセリング応答生成
- `ProactiveOutreachService`: チェックイン判定

#### Ports

インターフェース定義（依存性逆転の原則）:

```python
class IAIProvider(Protocol):
    async def generate(self, message: str, system_prompt: str) -> str: ...

class IStorage(Protocol):
    async def load_user(self, user_id: str) -> Optional[UserState]: ...
    async def save_user(self, user_id: str, state: UserState) -> None: ...
```

### Adapter Layer (`yamii/adapters/`)

#### AI Adapter

```python
class OpenAIAdapter(IAIProvider):
    # PII匿名化付きOpenAI API呼び出し
    async def generate(self, message: str, system_prompt: str) -> str:
        # 1. PII匿名化
        result = self.anonymizer.anonymize(message)
        # 2. API呼び出し
        response = await self._call_api(result.anonymized_text, system_prompt)
        # 3. PII復元
        return self.anonymizer.deanonymize(response, result.mapping)
```

#### Storage Adapter

```python
class FileStorageAdapter(IStorage):
    # JSONファイルベースの永続化
```

## 関係性システム (`yamii/relationship/`)

```
RelationshipMemorySystem
├── PhaseManager      # フェーズ遷移管理
├── EpisodeManager    # エピソード記憶管理
└── PromptGenerator   # フェーズに応じたプロンプト生成
```

## データフロー

```
User Message
    │
    ▼
┌─────────────────┐
│ PII Anonymizer  │  ← 個人情報をマスク
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Emotion Service │  ← 感情分析・危機検出
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Relationship   │  ← ユーザー状態・フェーズ取得
│  Memory System  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Prompt Generator│  ← システムプロンプト生成
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  OpenAI API     │  ← 応答生成
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ PII Deanonymize │  ← 個人情報を復元
└────────┬────────┘
         │
         ▼
    AI Response
```

## 拡張ポイント

### 別のAIプロバイダーを追加

```python
class AnthropicAdapter(IAIProvider):
    async def generate(self, message: str, system_prompt: str) -> str:
        # Claude API呼び出し
        ...
```

### 別のストレージを追加

```python
class PostgresAdapter(IStorage):
    async def load_user(self, user_id: str) -> Optional[UserState]:
        # PostgreSQL から取得
        ...
```

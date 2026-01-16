# Misskey Bot

YamiiのMisskey連携ボット。

## セットアップ

### 1. Misskeyでボットアカウント作成

1. Misskeyインスタンスでボット用アカウントを作成
2. 設定 > API > アクセストークン生成
   - 必要な権限: `read:account`, `write:notes`

### 2. 環境変数設定

```bash
# .env
MISSKEY_INSTANCE_URL=https://your-instance.example.com
MISSKEY_ACCESS_TOKEN=your_token_here
MISSKEY_BOT_USER_ID=your_bot_user_id
YAMII_API_URL=http://localhost:8000
```

### 3. 起動

```bash
uv run python -m yamii.bot.misskey
```

## 使い方

### 基本的な相談

ボットにメンションして相談:

```
@yamii 最近仕事がつらいです
```

### コマンド

| コマンド | 説明 |
|---------|------|
| `/help` | ヘルプを表示 |
| `終了` | セッションを終了 |

## 設定オプション

```python
YamiiMisskeyBotConfig(
    misskey_instance_url="https://...",
    misskey_access_token="...",
    misskey_bot_user_id="...",
    yamii_api_url="http://localhost:8000",
    bot_name="yamii",
    request_timeout=30,
)
```

## 危機対応

ボットが危機的状況を検出した場合、応答に緊急連絡先を自動追加:

- いのちの電話: 0570-783-556
- よりそいホットライン: 0120-279-338

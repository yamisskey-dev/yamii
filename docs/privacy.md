# プライバシー保護

## PII匿名化

OpenAI APIへの送信前に個人識別情報（PII）を自動的にマスク。

### 検出対象

| 種類 | 例 | マスク後 |
|------|-----|---------|
| 電話番号 | 090-1234-5678 | [PHONE_1] |
| メールアドレス | test@example.com | [EMAIL_1] |
| 住所 | 東京都新宿区1-2-3 | [ADDRESS_1] |
| 生年月日 | 1990年5月15日 | [BIRTHDAY_1] |
| 名前 | 田中太郎さん | [NAME_1] |
| マイナンバー | 1234-5678-9012 | [MYNUMBER_1] |
| カード番号 | 1234-5678-9012-3456 | [CARD_1] |

### 動作フロー

```
ユーザー入力: "090-1234-5678に連絡してください"
        │
        ▼
匿名化: "[PHONE_1]に連絡してください"
        │
        ▼
OpenAI API呼び出し
        │
        ▼
AI応答: "[PHONE_1]に連絡します"
        │
        ▼
復元: "090-1234-5678に連絡します"
```

### 無効化

```python
OpenAIAdapter(
    api_key="...",
    enable_anonymization=False  # 匿名化を無効化
)
```

## GDPR対応

### データ削除

```bash
curl -X DELETE http://localhost:8000/v1/users/{user_id}
```

ユーザーの全データ（会話履歴、エピソード、設定）を削除。

### データエクスポート

```bash
curl http://localhost:8000/v1/users/{user_id}/export
```

## E2EE（エンドツーエンド暗号化）

カスタムプロンプトはE2EEで保護可能。

```python
from yamii.core.encryption import get_e2ee_crypto

crypto = get_e2ee_crypto()
public_key, private_key = crypto.generate_key_pair()

# 暗号化
encrypted = crypto.encrypt(data, public_key)

# 復号（秘密鍵が必要）
decrypted = crypto.decrypt(encrypted, private_key)
```

## データ保存場所

```
data/
├── users/           # ユーザー状態
│   └── {user_id}.json
├── relationships/   # 関係性データ
│   └── {user_id}.json
└── prompts.db       # 暗号化プロンプト（SQLite）
```

## セキュリティ推奨事項

1. **APIキーの管理**: `.env`ファイルをgitignoreに追加
2. **HTTPS**: 本番環境では必ずHTTPSを使用
3. **レート制限**: 必要に応じてAPI側でレート制限を実装
4. **ログ**: PIIを含むログを出力しない設定を推奨

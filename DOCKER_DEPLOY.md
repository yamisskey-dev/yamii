# Navi 人生相談APIサーバー - Docker運用ガイド

## 🚀 シンプル本番環境デプロイ手順

### 1. 事前準備

#### 必要なツール
- Docker Engine 20.10+
- Docker Compose v2.0+
- curl (ヘルスチェック用)

#### APIキー取得
Google Cloud Consoleで Gemini API キーを取得してください：
1. [Google AI Studio](https://makersuite.google.com/app/apikey) にアクセス
2. APIキーを生成
3. 生成されたキーをコピー

### 2. 環境設定

#### 環境変数ファイルの設定
```bash
# .env.example を .env にコピー
cp .env.example .env

# 必要な値を設定
nano .env
```

**必須設定項目:**
```env
GEMINI_API_KEY=your_actual_api_key_here
ENVIRONMENT=production
LOG_LEVEL=info
```

#### ディレクトリ構成確認
```bash
navi/
├── docker-compose.yml
├── Dockerfile  
├── .env
├── logs/              # ログ出力用（自動作成）
└── navi/             # アプリケーションコード
```

### 3. デプロイ

#### 本番環境デプロイ
```bash
# ビルドとコンテナ起動
docker-compose up -d --build

# ログ確認
docker-compose logs -f navi
```

### 4. 動作確認

#### ヘルスチェック
```bash
# API確認
curl http://localhost:8000/health
```

#### 人生相談API テスト
```bash
curl -X POST "http://localhost:8000/counseling" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "最近とても疲れています。どうしたらいいでしょうか？",
    "user_id": "test_user",
    "user_name": "テストユーザー"
  }'
```

### 5. 運用コマンド

#### コンテナ管理
```bash
# 起動
docker-compose up -d

# 停止
docker-compose down

# 再起動
docker-compose restart

# コンテナ状態確認
docker-compose ps

# ログ確認
docker-compose logs -f navi
```

#### アップデート手順
```bash
# 新しいイメージをビルド
docker-compose build --no-cache

# デプロイ
docker-compose up -d --force-recreate
```

#### データ管理
```bash
# データバックアップ
docker run --rm -v navi_navi_data:/data -v $(pwd):/backup alpine tar czf /backup/navi-backup.tar.gz -C /data .

# データリストア
docker run --rm -v navi_navi_data:/data -v $(pwd):/backup alpine tar xzf /backup/navi-backup.tar.gz -C /data
```

### 6. 監視とメンテナンス

#### ログ監視
```bash
# リアルタイムログ監視
docker-compose logs -f --tail=100

# エラーログのみ表示
docker-compose logs navi 2>&1 | grep ERROR
```

#### パフォーマンス監視
```bash
# コンテナリソース使用状況
docker stats navi-counseling-api
```

#### ディスク使用量管理
```bash
# 未使用イメージ削除
docker image prune -f

# 未使用ボリューム削除
docker volume prune -f
```

### 7. セキュリティ設定

#### ファイアウォール設定
```bash
# ポート開放（例：UFW）
sudo ufw allow 8000/tcp

# 他の不要ポートは閉鎖
```

### 8. トラブルシューティング

#### よくある問題

**問題1: コンテナが起動しない**
```bash
# 詳細ログ確認
docker-compose logs navi

# 設定ファイル構文チェック
docker-compose config
```

**問題2: APIが応答しない**
```bash
# コンテナ内部確認
docker exec -it navi-counseling-api /bin/bash

# プロセス確認
docker exec navi-counseling-api ps aux
```

**問題3: Gemini API エラー**
- API キーが正しく設定されているか確認
- API使用量制限に達していないか確認
- ネットワーク接続を確認

### 9. 開発環境設定

#### 開発用コマンド
```bash
# 開発モードで起動（ホットリロード）
docker-compose run --rm -p 8000:8000 -e DEBUG=true navi python -m uvicorn navi.main:app --host 0.0.0.0 --reload
```

### 10. バックアップ戦略

#### 定期バックアップスクリプト例
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
docker run --rm -v navi_navi_data:/data -v $(pwd)/backups:/backup alpine \
  tar czf /backup/navi_backup_$DATE.tar.gz -C /data .
find ./backups -name "navi_backup_*.tar.gz" -mtime +7 -delete
```

### 11. 外部アクセス設定

#### リバースプロキシ設定例（Apache）
```apache
<VirtualHost *:80>
    ServerName your-domain.com
    ProxyPass / http://localhost:8000/
    ProxyPassReverse / http://localhost:8000/
    ProxyPreserveHost On
</VirtualHost>
```

#### リバースプロキシ設定例（Nginx）
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 📞 サポート

問題が発生した場合は、以下の情報を含めてお問い合わせください：
- Docker・Docker Composeバージョン
- OS情報
- エラーログ全文
- 実行したコマンド

---

## 🎯 基本的な使用例

### クイックスタート
```bash
# 1. リポジトリクローン
git clone <repository-url>
cd navi

# 2. 環境設定
cp .env.example .env
# .envでGEMINI_API_KEYを設定

# 3. 起動
docker-compose up -d --build

# 4. 動作確認
curl http://localhost:8000/health

# 5. テスト
curl -X POST "http://localhost:8000/counseling" \
  -H "Content-Type: application/json" \
  -d '{"message":"こんにちは","user_id":"test","user_name":"テスト"}'
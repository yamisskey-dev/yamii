#!/usr/bin/env python3
"""
Navi統合テストスクリプト
APIサーバーとMisskeyボットの統合動作を検証
"""

import asyncio
import aiohttp
import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from yamii.core.logging import NaviLogger, get_logger

# テスト用環境変数の設定（統一された命名規則）
os.environ.update({
    'GEMINI_API_KEY': 'test_key_12345',
    'ENABLE_MISSKEY_BOT': 'true',
    'MISSKEY_INSTANCE_URL': 'https://test.misskey.example',
    'MISSKEY_ACCESS_TOKEN': 'test_token_67890',
    'MISSKEY_BOT_USER_ID': 'test_bot_user_123',
    'BOT_NAME': 'yamii_test',
    'BOT_USERNAME': 'yamii_test',
    'YAMII_API_URL': 'http://localhost:8000',
    'YAMII_API_TIMEOUT': '30',
    'BOT_SESSION_TIMEOUT': '3600',
    'LOG_LEVEL': 'DEBUG',
    'BOT_ENABLE_DM': 'true',
    'BOT_ENABLE_MENTIONS': 'true',
    'BOT_ENABLE_TIMELINE': 'false',
    'BOT_ENABLE_GLOBAL_TIMELINE': 'false',
})

class NaviIntegrationTester:
    """Navi統合テスター"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.logger = get_logger("integration_test")
    
    async def test_api_health(self) -> bool:
        """APIサーバーのヘルスチェック"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        self.logger.info(f"✅ APIヘルスチェック成功: {data['status']}")
                        return True
                    else:
                        self.logger.error(f"❌ APIヘルスチェック失敗: {response.status}")
                        return False
        except Exception as e:
            self.logger.error(f"❌ APIヘルスチェックエラー: {e}")
            return False
    
    async def test_api_root(self) -> bool:
        """APIルートエンドポイントテスト"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/") as response:
                    if response.status == 200:
                        data = await response.json()
                        self.logger.info(f"✅ APIルート取得成功: {data['service']}")
                        self.logger.info(f"   - Misskeyボット機能: {data.get('features', {}).get('misskey_bot', 'N/A')}")
                        if 'bot_status' in data:
                            bot_status = data['bot_status']
                            self.logger.info(f"   - ボット状態: enabled={bot_status['enabled']}, running={bot_status['running']}")
                        return True
                    else:
                        self.logger.error(f"❌ APIルート取得失敗: {response.status}")
                        return False
        except Exception as e:
            self.logger.error(f"❌ APIルート取得エラー: {e}")
            return False
    
    async def test_counseling_api(self) -> bool:
        """カウンセリングAPIテスト"""
        try:
            test_request = {
                "message": "最近悩んでいることがあります。話を聞いてもらえませんか？",
                "user_id": "test_user_001",
                "user_name": "テストユーザー"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/counseling",
                    json=test_request
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.logger.info("✅ カウンセリングAPI成功")
                        self.logger.info(f"   - レスポンス長: {len(data['response'])}文字")
                        self.logger.info(f"   - 感情分析: {data['emotion_analysis']}")
                        self.logger.info(f"   - アドバイスタイプ: {data['advice_type']}")
                        self.logger.info(f"   - 危機状態: {data['is_crisis']}")
                        return True
                    else:
                        self.logger.error(f"❌ カウンセリングAPI失敗: {response.status}")
                        error_data = await response.text()
                        self.logger.error(f"   - エラー詳細: {error_data}")
                        return False
        except Exception as e:
            self.logger.error(f"❌ カウンセリングAPIエラー: {e}")
            return False
    
    async def test_bot_status(self) -> bool:
        """ボット状態テスト"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/bot/status") as response:
                    if response.status == 200:
                        data = await response.json()
                        self.logger.info("✅ ボット状態取得成功")
                        self.logger.info(f"   - 有効: {data['enabled']}")
                        self.logger.info(f"   - 実行中: {data['running']}")
                        self.logger.info(f"   - タスク完了: {data['task_done']}")
                        return True
                    else:
                        self.logger.error(f"❌ ボット状態取得失敗: {response.status}")
                        return False
        except Exception as e:
            self.logger.error(f"❌ ボット状態取得エラー: {e}")
            return False
    
    async def run_all_tests(self) -> bool:
        """すべてのテストを実行"""
        self.logger.info("=== Navi統合テスト開始 ===")
        
        tests = [
            ("APIヘルスチェック", self.test_api_health()),
            ("APIルート", self.test_api_root()),
            ("カウンセリングAPI", self.test_counseling_api()),
            ("ボット状態", self.test_bot_status())
        ]
        
        results = []
        for test_name, test_coro in tests:
            self.logger.info(f"\n--- {test_name} テスト ---")
            result = await test_coro
            results.append((test_name, result))
        
        # 結果サマリー
        self.logger.info("\n=== テスト結果サマリー ===")
        passed = 0
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            self.logger.info(f"{status} {test_name}")
            if result:
                passed += 1
        
        success_rate = (passed / total) * 100
        self.logger.info(f"\n成功率: {passed}/{total} ({success_rate:.1f}%)")
        
        if passed == total:
            self.logger.info("🎉 全てのテストが成功しました！")
            return True
        else:
            self.logger.warning(f"⚠️  {total - passed} 個のテストが失敗しました。")
            return False

async def main():
    """メイン実行関数"""
    # ログシステム初期化
    NaviLogger.configure(
        log_level=os.getenv("LOG_LEVEL", "INFO")
    )
    
    # テストサーバーURL設定
    base_url = os.getenv("TEST_SERVER_URL", "http://localhost:8000")
    
    # テスター実行
    tester = NaviIntegrationTester(base_url)
    success = await tester.run_all_tests()
    
    # 終了コード設定
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
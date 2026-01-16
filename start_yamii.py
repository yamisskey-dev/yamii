#!/usr/bin/env python3
"""
Yamii統合サーバー起動スクリプト
APIサーバーとMisskey Botを同時起動
"""

import asyncio
import signal
import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from yamii.core.logging import YamiiLogger, get_logger
from yamii.core.config import get_settings


async def run_api_server():
    """APIサーバーを起動"""
    import uvicorn
    from yamii.api.main import app

    config = uvicorn.Config(
        app=app,
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        log_level=os.getenv("YAMII_LOG_LEVEL", "info").lower()
    )
    server = uvicorn.Server(config)
    await server.serve()


async def run_misskey_bot():
    """Misskey Botを起動"""
    from yamii.bot.misskey.yamii_bot import YamiiMisskeyBot
    from yamii.bot.misskey.config import YamiiMisskeyBotConfig

    settings = get_settings()
    logger = get_logger("bot.startup")

    # Bot設定を作成
    config = YamiiMisskeyBotConfig(
        misskey_instance_url=settings.misskey.instance_url,
        misskey_access_token=settings.misskey.access_token,
        misskey_bot_user_id=settings.misskey.bot_user_id,
    )

    logger.info(f"Misskey Bot starting: {settings.misskey.instance_url}")

    # Bot起動
    bot = YamiiMisskeyBot(config)
    await bot.start()


async def main():
    """メイン実行関数"""
    # ログシステム初期化
    YamiiLogger.configure()
    logger = get_logger("startup")

    settings = get_settings()

    logger.info("=== Yamii 統合サーバー起動 ===")
    logger.info(f"Misskey設定: {'あり' if settings.misskey.is_configured else 'なし'}")

    # 実行するタスクを収集
    tasks = []

    # APIサーバーは常に起動
    tasks.append(asyncio.create_task(run_api_server()))
    logger.info("API Server: 起動中...")

    # Misskeyが設定されていればBotも起動
    if settings.misskey.is_configured:
        tasks.append(asyncio.create_task(run_misskey_bot()))
        logger.info("Misskey Bot: 起動中...")
    else:
        logger.warning("Misskey Bot: 設定がないためスキップ")
        logger.warning("  → MISSKEY_INSTANCE_URL, MISSKEY_ACCESS_TOKEN, MISSKEY_BOT_USER_ID を設定してください")

    # シャットダウンイベント
    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("シャットダウンシグナルを受信...")
        shutdown_event.set()
        for task in tasks:
            task.cancel()

    # シグナルハンドラー登録
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        # 全タスクを並行実行
        await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        logger.info("タスクがキャンセルされました")
    finally:
        logger.info("=== Yamii 統合サーバー終了 ===")


if __name__ == "__main__":
    asyncio.run(main())

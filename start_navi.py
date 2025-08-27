#!/usr/bin/env python3
"""
Navi統合サーバー起動スクリプト
APIサーバーとMisskeyボットを統合起動

"""

import asyncio
import signal
import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from navi.core.logging import NaviLogger, get_logger

async def main():
    """メイン実行関数"""
    # ログシステム初期化
    NaviLogger.configure(
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE")
    )
    
    logger = get_logger("startup")
    
    try:
        # 環境変数チェック
        bot_enabled = os.getenv("ENABLE_MISSKEY_BOT", "false").lower() == "true"
        api_only = os.getenv("API_ONLY", "false").lower() == "true"
        
        logger.info("=== Navi統合サーバー起動 ===")
        logger.info(f"Misskeyボット: {'有効' if bot_enabled else '無効'}")
        logger.info(f"APIのみモード: {'有効' if api_only else '無効'}")
        
        if api_only:
            # APIサーバーのみ起動
            logger.info("APIサーバーのみを起動します...")
            import uvicorn
            from navi.main import app
            
            uvicorn.run(
                app,
                host=os.getenv("HOST", "0.0.0.0"),
                port=int(os.getenv("PORT", "8000")),
                log_level=os.getenv("LOG_LEVEL", "info").lower()
            )
        else:
            # APIサーバーとボットを統合起動
            logger.info("APIサーバーとボットを統合起動します...")
            import uvicorn
            from navi.main import app
            
            # Uvicornサーバー設定
            config = uvicorn.Config(
                app=app,
                host=os.getenv("HOST", "0.0.0.0"),
                port=int(os.getenv("PORT", "8000")),
                log_level=os.getenv("LOG_LEVEL", "info").lower()
            )
            
            server = uvicorn.Server(config)
            
            # シグナルハンドラー設定
            def signal_handler(signum, frame):
                logger.info(f"シグナル {signum} を受信しました。サーバーを停止します...")
                asyncio.create_task(server.shutdown())
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # サーバー起動
            await server.serve()
    
    except KeyboardInterrupt:
        logger.info("キーボード割り込みにより終了します")
    except Exception as e:
        logger.error(f"起動エラー: {e}")
        raise
    finally:
        logger.info("=== Navi統合サーバー終了 ===")

if __name__ == "__main__":
    asyncio.run(main())
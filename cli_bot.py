#!/usr/bin/env python3
"""
Navi Misskey Bot CLI
naviのMisskeyボットを起動するためのCLIツール
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path

# naviパッケージのパスを追加
sys.path.insert(0, str(Path(__file__).parent))

from navi.bot.misskey import NaviMisskeyBot, load_config, setup_logging


def create_env_file():
    """環境設定ファイルのテンプレートを作成"""
    env_template = """# Navi Misskey Bot Configuration
# 必須設定
MISSKEY_INSTANCE_URL=https://your-misskey-instance.com
MISSKEY_ACCESS_TOKEN=your_misskey_access_token_here

# Navi API設定
NAVI_API_URL=http://localhost:8000

# ボット設定
BOT_NAME=navi
BOT_DISPLAY_NAME=Navi - 人生相談AI

# ログ設定
LOG_LEVEL=INFO
LOG_FILE=logs/navi_bot.log

# タイムアウト設定
REQUEST_TIMEOUT=30
SESSION_TIMEOUT=1800

# クライシスサポート
ENABLE_CRISIS_SUPPORT=true
"""
    
    env_file = Path(".env")
    if env_file.exists():
        print(f"⚠️  {env_file} already exists. Skipping creation.")
        return False
    
    env_file.write_text(env_template)
    print(f"✅ Created {env_file}")
    print("\n📝 Please edit the .env file with your configuration:")
    print("   1. Set MISSKEY_INSTANCE_URL to your Misskey instance")
    print("   2. Set MISSKEY_ACCESS_TOKEN to your bot's access token") 
    print("   3. Configure other settings as needed")
    return True


async def run_bot():
    """ボットを実行"""
    try:
        config = load_config()
        setup_logging(config)
        
        print("🚀 Starting Navi Misskey Bot...")
        print(f"   Instance: {config.misskey_instance_url}")
        print(f"   Navi API: {config.navi_api_url}")
        print(f"   Bot Name: @{config.bot_name}")
        
        bot = NaviMisskeyBot(config)
        await bot.start()
        
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\n💡 Please check your .env file configuration")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Bot crashed: {e}")
        sys.exit(1)


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="Navi Misskey Bot - 人生相談AIボット",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # ボットを起動
  %(prog)s --init             # 設定ファイルを初期化
  %(prog)s --version          # バージョンを表示

Configuration:
  ボットは .env ファイルから設定を読み込みます。
  初回起動時は --init で設定ファイルのテンプレートを作成してください。
        """
    )
    
    parser.add_argument(
        "--init",
        action="store_true",
        help="設定ファイル (.env) のテンプレートを作成"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Navi Misskey Bot v1.0.0"
    )
    
    args = parser.parse_args()
    
    if args.init:
        create_env_file()
        return
    
    # ログディレクトリを作成
    os.makedirs("logs", exist_ok=True)
    
    # ボットを実行
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
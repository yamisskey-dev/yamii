#!/usr/bin/env python
"""
プロアクティブアウトリーチ cron ジョブ

定期的に実行して、チェックインが必要なユーザーを検出し、
Misskey Bot 経由でメッセージを送信する。

使用例:
    # 手動実行
    python -m yamii.scripts.outreach_cron

    # cron 設定例（1時間ごと）
    0 * * * * cd /path/to/yamii && python -m yamii.scripts.outreach_cron >> /var/log/yamii/outreach.log 2>&1

    # systemd timer での設定も推奨
"""

import asyncio
import sys

import aiohttp

from ..core.config import get_settings
from ..core.logging import YamiiLogger, get_logger

# ログ初期化
YamiiLogger.configure()
logger = get_logger("cron.outreach")


class OutreachCronJob:
    """プロアクティブアウトリーチ cron ジョブ"""

    def __init__(self):
        self.settings = get_settings()
        self.api_url = f"http://{self.settings.api_host}:{self.settings.api_port}"

    async def run(self) -> int:
        """
        アウトリーチジョブを実行

        Returns:
            int: 送信したメッセージ数
        """
        logger.info("Starting proactive outreach job", extra={
            "event_type": "cron_start",
            "job": "outreach",
        })

        try:
            # 1. API からアウトリーチ待ちユーザーを取得
            pending_users = await self._fetch_pending_outreach()

            if not pending_users:
                logger.info("No users need outreach at this time", extra={
                    "event_type": "cron_complete",
                    "job": "outreach",
                    "users_processed": 0,
                })
                return 0

            logger.info(f"Found {len(pending_users)} users needing outreach", extra={
                "event_type": "outreach_pending",
                "count": len(pending_users),
            })

            # 2. 各ユーザーにメッセージを送信
            sent_count = 0
            for user_info in pending_users:
                success = await self._send_outreach(user_info)
                if success:
                    sent_count += 1

            logger.info(f"Outreach job completed: {sent_count}/{len(pending_users)} messages sent", extra={
                "event_type": "cron_complete",
                "job": "outreach",
                "users_processed": len(pending_users),
                "messages_sent": sent_count,
            })

            return sent_count

        except Exception as e:
            logger.error(f"Outreach job failed: {e}", extra={
                "event_type": "cron_error",
                "job": "outreach",
                "error": str(e),
            }, exc_info=True)
            return 0

    async def _fetch_pending_outreach(self) -> list[dict]:
        """API からアウトリーチ待ちユーザーを取得"""
        url = f"{self.api_url}/v1/outreach/pending"
        headers = self._get_headers()

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("users", [])
                    else:
                        logger.warning(f"Failed to fetch pending outreach: {response.status}")
                        return []
            except aiohttp.ClientError as e:
                logger.error(f"API request failed: {e}")
                return []

    async def _send_outreach(self, user_info: dict) -> bool:
        """
        ユーザーにアウトリーチメッセージを送信

        実際の送信は Misskey Bot が行う。
        ここでは Bot API を呼び出すか、直接 Misskey API を呼ぶ。
        """
        user_id = user_info.get("user_id")
        message = user_info.get("message")
        reason = user_info.get("reason", "unknown")

        if not user_id or not message:
            logger.warning(f"Invalid user info: {user_info}")
            return False

        logger.info(f"Sending outreach to user {user_id}", extra={
            "event_type": "outreach_send",
            "user_id": user_id,
            "reason": reason,
        })

        # Misskey が設定されている場合は直接送信
        if self.settings.misskey.is_configured:
            return await self._send_misskey_dm(user_id, message)

        # API 経由でトリガー（Bot が別プロセスで動いている場合）
        return await self._trigger_via_api(user_id, message)

    async def _send_misskey_dm(self, user_id: str, message: str) -> bool:
        """Misskey DM を直接送信"""
        from ..bot.misskey.config import YamiiMisskeyBotConfig
        from ..bot.misskey.misskey_client import MisskeyClient

        try:
            # 設定を作成
            config = YamiiMisskeyBotConfig(
                misskey_instance_url=self.settings.misskey.instance_url,
                misskey_access_token=self.settings.misskey.access_token,
                misskey_bot_user_id=self.settings.misskey.bot_user_id,
            )

            # クライアントを使用して DM を送信
            async with MisskeyClient(config) as client:
                await client.send_chat_message(user_id, message)

            logger.info(f"Sent DM to user {user_id}", extra={
                "event_type": "outreach_sent",
                "user_id": user_id,
                "method": "misskey_dm",
            })
            return True

        except Exception as e:
            logger.error(f"Failed to send DM: {e}", extra={
                "event_type": "outreach_failed",
                "user_id": user_id,
                "error": str(e),
            })
            return False

    async def _trigger_via_api(self, user_id: str, message: str) -> bool:
        """API 経由でアウトリーチをトリガー"""
        url = f"{self.api_url}/v1/outreach/trigger"
        headers = self._get_headers()
        data = {
            "user_id": user_id,
            "message": message,
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, json=data, timeout=30) as response:
                    if response.status == 200:
                        logger.info(f"Triggered outreach for user {user_id}", extra={
                            "event_type": "outreach_sent",
                            "user_id": user_id,
                            "method": "api_trigger",
                        })
                        return True
                    else:
                        logger.warning(f"Failed to trigger outreach: {response.status}")
                        return False
            except aiohttp.ClientError as e:
                logger.error(f"API request failed: {e}")
                return False

    def _get_headers(self) -> dict:
        """API リクエストヘッダーを取得"""
        headers = {"Content-Type": "application/json"}

        # API キーが設定されている場合
        if self.settings.security.api_keys:
            # 最初のキーを使用（Bot 用キーを使う場合は環境変数で指定）
            import os
            api_key = os.getenv("YAMII_BOT_API_KEY") or self.settings.security.api_keys[0]
            headers[self.settings.security.api_key_header] = api_key

        return headers


async def main():
    """メインエントリーポイント"""
    job = OutreachCronJob()
    sent_count = await job.run()
    print(f"Outreach completed: {sent_count} messages sent")
    return 0 if sent_count >= 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

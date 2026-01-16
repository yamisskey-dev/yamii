"""
Yamii Misskey Bot
シンプルなMisskeyボット - メンション・リプライ・DMに応答
"""

import asyncio
import logging
from typing import Dict, Set
from datetime import datetime

from .config import YamiiMisskeyBotConfig, load_config
from .misskey_client import MisskeyClient, MisskeyNote
from .yamii_client import YamiiClient, YamiiRequest


class YamiiMisskeyBot:
    """Yamii Misskeyボット

    応答条件:
    - @yamii メンション
    - ボットへのリプライ
    - DM（visibility=specified）
    """

    def __init__(self, config: YamiiMisskeyBotConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # クライアント
        self.misskey_client = MisskeyClient(config)
        self.yamii_client = YamiiClient(config)

        # ユーザーセッション（user_id -> session_id）
        self.user_sessions: Dict[str, str] = {}

        # 処理済みノート管理（重複処理防止）
        self.processed_notes: Set[str] = set()

    async def start(self):
        """ボットを開始"""
        self.logger.info("Starting Yamii Misskey Bot...")
        self.logger.info(f"Yamii API: {self.config.yamii_api_url}")
        self.logger.info(f"Misskey: {self.config.misskey_instance_url}")

        try:
            await self.misskey_client.__aenter__()
            await self.yamii_client.__aenter__()

            # ヘルスチェック
            try:
                health = await self.yamii_client.health_check()
                self.logger.info(f"Yamii API status: {health.get('status')}")
            except Exception as e:
                self.logger.warning(f"Health check failed: {e}")

            # ストリーミング開始
            await self.misskey_client.start_streaming(self._on_streaming_message)

        except Exception as e:
            self.logger.error(f"Bot startup error: {e}")
            raise
        finally:
            await self.misskey_client.__aexit__(None, None, None)
            await self.yamii_client.__aexit__(None, None, None)

    async def _on_streaming_message(self, data: dict):
        """ストリーミングメッセージを処理"""
        try:
            if data.get("type") != "channel":
                return

            body = data.get("body", {})
            body_type = body.get("type")

            # タイムラインからのノート
            if body_type == "note":
                note_data = body["body"]
                note = self.misskey_client._parse_note(note_data)
                await self._handle_note(note)

            # メンション通知
            elif body_type == "mention":
                note_data = body["body"]
                note = self.misskey_client._parse_note(note_data)
                await self._handle_note(note)

            # 通知（リプライなど）
            elif body_type == "notification":
                notification = body["body"]
                if notification.get("type") in ["mention", "reply"] and "note" in notification:
                    note_data = notification["note"]
                    note = self.misskey_client._parse_note(note_data)
                    await self._handle_note(note)

        except Exception as e:
            self.logger.error(f"Error handling message: {e}")

    async def _handle_note(self, note: MisskeyNote):
        """ノートを処理"""
        # 重複チェック
        if note.id in self.processed_notes:
            return
        self.processed_notes.add(note.id)

        # メモリリーク防止
        if len(self.processed_notes) > 1000:
            self.processed_notes = set(list(self.processed_notes)[-500:])

        # 自分の投稿はスキップ
        if note.user_id == self.misskey_client.bot_user_id:
            return

        # 応答条件チェック: メンション or リプライ or DM
        is_mentioned = self.misskey_client.is_mentioned(note)
        is_reply = self.misskey_client.is_reply_to_bot(note)
        is_dm = self.misskey_client.is_direct_message(note)

        if not (is_mentioned or is_reply or is_dm):
            return

        self.logger.info(f"Processing: @{note.user_username} (mention={is_mentioned}, reply={is_reply}, dm={is_dm})")

        try:
            await self._handle_counseling(note)
        except Exception as e:
            self.logger.error(f"Counseling error: {e}")
            await self._send_reply(note, "申し訳ありません。処理中にエラーが発生しました。")

    async def _handle_counseling(self, note: MisskeyNote):
        """カウンセリング処理"""
        message = self.misskey_client.extract_message_from_note(note)

        # 空メッセージの場合
        if not message:
            await self._send_reply(note, "何かお話ししたいことがあれば、気軽に話しかけてください。")
            return

        # ヘルプコマンド
        if message.lower() in ["/help", "ヘルプ"]:
            help_text = (
                "**Yamii - 相談AI**\n\n"
                "話しかけるだけで相談できます。\n"
                "- メンション: @yamii 相談内容\n"
                "- リプライ: 会話を続ける\n"
                "- DM: プライベートな相談\n\n"
                "何でもお気軽にどうぞ。"
            )
            await self._send_reply(note, help_text)
            return

        # ステータスコマンド
        if message.lower() == "/status":
            try:
                health = await self.yamii_client.health_check()
                status = "正常" if health.get("status") == "healthy" else "異常"
                await self._send_reply(note, f"Yamii API: {status}")
            except Exception:
                await self._send_reply(note, "Yamii API: 接続エラー")
            return

        # カウンセリングリクエスト
        session_id = self.user_sessions.get(note.user_id)

        request = YamiiRequest(
            message=message,
            user_id=note.user_id,
            user_name=note.user_name or note.user_username,
            session_id=session_id,
            context={"platform": "misskey", "bot_name": self.config.bot_name}
        )

        response = await self.yamii_client.send_counseling_request(request)

        if response:
            # セッション記録
            self.user_sessions[note.user_id] = response.session_id

            # 危機対応
            if response.is_crisis:
                crisis_info = "\n\n".join([
                    response.response,
                    "⚠️ **相談窓口**",
                    "📞 " + "\n📞 ".join(self.config.crisis_hotline_numbers),
                    "あなたは一人ではありません。"
                ])
                await self._send_reply(note, crisis_info)
            else:
                await self._send_reply(note, response.response)
        else:
            await self._send_reply(note, "現在サービスを利用できません。しばらくお待ちください。")

    async def _send_reply(self, note: MisskeyNote, text: str):
        """返信を送信"""
        try:
            # DMにはDMで返信
            visibility = "specified" if note.visibility == "specified" else "home"
            await self.misskey_client.create_note(
                text=text,
                reply_id=note.id,
                visibility=visibility
            )
            self.logger.info(f"Replied to @{note.user_username}")
        except Exception as e:
            self.logger.error(f"Failed to send reply: {e}")


def setup_logging(config: YamiiMisskeyBotConfig):
    """ログ設定"""
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filename=config.log_file
    )


async def main():
    """メイン関数"""
    try:
        config = load_config()
        setup_logging(config)

        bot = YamiiMisskeyBot(config)
        await bot.start()

    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Bot crashed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

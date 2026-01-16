"""
Yamii Misskey Bot
シンプルなMisskeyボット - メンション・リプライ・DMに応答
プロアクティブアウトリーチ機能付き
"""

import asyncio
import logging
from collections import OrderedDict
from typing import Dict, Optional
from datetime import datetime

from .config import YamiiMisskeyBotConfig, load_config
from .misskey_client import MisskeyClient, MisskeyNote, MisskeyChatMessage
from .yamii_client import YamiiClient, YamiiRequest


class LRUSet:
    """最大サイズ付きLRUセット（重複チェック用）"""

    def __init__(self, maxsize: int = 1000):
        self.maxsize = maxsize
        self._cache: OrderedDict[str, None] = OrderedDict()

    def add(self, item: str) -> None:
        if item in self._cache:
            self._cache.move_to_end(item)
        else:
            self._cache[item] = None
            if len(self._cache) > self.maxsize:
                self._cache.popitem(last=False)

    def __contains__(self, item: str) -> bool:
        return item in self._cache


class YamiiMisskeyBot:
    """Yamii Misskeyボット

    応答条件:
    - @yamii メンション
    - ボットへのリプライ
    - DM（visibility=specified）
    - チャットメッセージ

    プロアクティブ機能:
    - 定期的にユーザーパターンを分析
    - 必要に応じてチェックインメッセージを送信
    """

    def __init__(self, config: YamiiMisskeyBotConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # クライアント
        self.misskey_client = MisskeyClient(config)
        self.yamii_client = YamiiClient(config)

        # ユーザーセッション（user_id -> session_id）
        self.user_sessions: Dict[str, str] = {}

        # 処理済みメッセージ管理（重複処理防止、LRUで自動クリーンアップ）
        self.processed_notes = LRUSet(maxsize=1000)
        self.processed_chat_messages = LRUSet(maxsize=1000)

        # プロアクティブアウトリーチタスク
        self._outreach_task: Optional[asyncio.Task] = None

    async def start(self):
        """ボットを開始"""
        self.logger.info("Starting Yamii Misskey Bot...")
        self.logger.info(f"Yamii API: {self.config.yamii_api_url}")
        self.logger.info(f"Misskey: {self.config.misskey_instance_url}")
        self.logger.info(f"Proactive outreach: {self.config.enable_proactive_outreach}")

        try:
            await self.misskey_client.__aenter__()
            await self.yamii_client.__aenter__()

            # ヘルスチェック
            try:
                health = await self.yamii_client.health_check()
                self.logger.info(f"Yamii API status: {health.get('status')}")
            except Exception as e:
                self.logger.warning(f"Health check failed: {e}")

            # プロアクティブアウトリーチスケジューラを開始
            if self.config.enable_proactive_outreach:
                self._outreach_task = asyncio.create_task(self._proactive_outreach_loop())
                self.logger.info(f"Proactive outreach scheduler started (interval: {self.config.proactive_check_interval}s)")

            # ストリーミング開始
            await self.misskey_client.start_streaming(self._on_streaming_message)

        except Exception as e:
            self.logger.error(f"Bot startup error: {e}")
            raise
        finally:
            # アウトリーチタスクをキャンセル
            if self._outreach_task:
                self._outreach_task.cancel()
                try:
                    await self._outreach_task
                except asyncio.CancelledError:
                    pass

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

            # チャットメッセージ（mainチャンネルから）
            elif body_type == "newChatMessage":
                chat_data = body["body"]
                await self._handle_chat_message(chat_data)

        except Exception as e:
            self.logger.error(f"Error handling message: {e}")

    async def _handle_note(self, note: MisskeyNote):
        """ノートを処理"""
        # 重複チェック（LRUSetで自動クリーンアップ）
        if note.id in self.processed_notes:
            return
        self.processed_notes.add(note.id)

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
        """カウンセリング処理（薄型化: コマンド判定はAPI側）"""
        message = self.misskey_client.extract_message_from_note(note)

        # メッセージ分類をAPIに委譲
        classification = await self.yamii_client.classify_message(
            message=message or "",
            user_id=note.user_id,
            platform="misskey"
        )

        # 空メッセージ
        if classification.get("is_empty"):
            empty_response = await self.yamii_client.get_empty_response()
            await self._send_reply(note, empty_response)
            return

        # コマンド処理
        if classification.get("is_command"):
            command_type = classification.get("command_type")
            if command_type == "help":
                help_text = await self.yamii_client.get_help(platform="misskey", context="note")
                await self._send_reply(note, help_text)
            elif command_type == "status":
                status_text = await self.yamii_client.get_status()
                await self._send_reply(note, status_text)
            return

        # カウンセリングリクエスト
        if classification.get("should_counsel"):
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

                # formatted_responseを使用（危機対応情報を含む）
                reply_text = response.formatted_response or response.response
                await self._send_reply(note, reply_text)
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

    async def _handle_chat_message(self, chat_data: dict):
        """チャットメッセージを処理"""
        message_id = chat_data.get("id")
        if not message_id:
            return

        # 重複チェック（LRUSetで自動クリーンアップ）
        if message_id in self.processed_chat_messages:
            return
        self.processed_chat_messages.add(message_id)

        # 自分のメッセージはスキップ
        from_user_id = chat_data.get("fromUserId")
        if from_user_id == self.misskey_client.bot_user_id:
            return

        from_user = chat_data.get("fromUser", {})
        username = from_user.get("username", "unknown")
        user_name = from_user.get("name")
        text = chat_data.get("text", "")

        self.logger.info(f"Processing chat from @{username}")

        try:
            await self._handle_chat_counseling(from_user_id, username, user_name, text)
        except Exception as e:
            self.logger.error(f"Chat counseling error: {e}")
            await self._send_chat_reply(from_user_id, "申し訳ありません。処理中にエラーが発生しました。")

    async def _handle_chat_counseling(self, user_id: str, username: str, user_name: str, text: str):
        """チャットカウンセリング処理（薄型化: コマンド判定はAPI側）"""
        # メッセージ分類をAPIに委譲
        classification = await self.yamii_client.classify_message(
            message=text or "",
            user_id=user_id,
            platform="misskey_chat"
        )

        # 空メッセージ
        if classification.get("is_empty"):
            empty_response = await self.yamii_client.get_empty_response()
            await self._send_chat_reply(user_id, empty_response)
            return

        # コマンド処理
        if classification.get("is_command"):
            command_type = classification.get("command_type")
            if command_type == "help":
                help_text = await self.yamii_client.get_help(platform="misskey", context="chat")
                await self._send_chat_reply(user_id, help_text)
            elif command_type == "status":
                status_text = await self.yamii_client.get_status()
                await self._send_chat_reply(user_id, status_text)
            return

        # カウンセリングリクエスト
        if classification.get("should_counsel"):
            session_id = self.user_sessions.get(user_id)

            request = YamiiRequest(
                message=text,
                user_id=user_id,
                user_name=user_name or username,
                session_id=session_id,
                context={"platform": "misskey_chat", "bot_name": self.config.bot_name}
            )

            response = await self.yamii_client.send_counseling_request(request)

            if response:
                # セッション記録
                self.user_sessions[user_id] = response.session_id

                # formatted_responseを使用（危機対応情報を含む）
                reply_text = response.formatted_response or response.response
                await self._send_chat_reply(user_id, reply_text)
            else:
                await self._send_chat_reply(user_id, "現在サービスを利用できません。しばらくお待ちください。")

    async def _send_chat_reply(self, user_id: str, text: str):
        """チャット返信を送信"""
        try:
            await self.misskey_client.send_chat_message(user_id, text)
            self.logger.info(f"Sent chat reply to user {user_id}")
        except Exception as e:
            self.logger.error(f"Failed to send chat reply: {e}")

    # === プロアクティブアウトリーチ ===

    async def _proactive_outreach_loop(self):
        """プロアクティブアウトリーチの定期実行ループ

        Bot APIならではの差別化機能:
        - ユーザーが連絡しなくても、パターン検出でBotから先にチェックイン
        - 不在検出、センチメント悪化、フォローアップ、マイルストーンに対応
        """
        self.logger.info("Proactive outreach loop started")

        while True:
            try:
                await asyncio.sleep(self.config.proactive_check_interval)
                await self._execute_proactive_outreach()
            except asyncio.CancelledError:
                self.logger.info("Proactive outreach loop cancelled")
                break
            except Exception as e:
                self.logger.error(f"Proactive outreach error: {e}")
                # エラーが発生しても続行

    async def _execute_proactive_outreach(self):
        """プロアクティブアウトリーチを実行"""
        self.logger.debug("Checking for users needing outreach...")

        try:
            # APIからアウトリーチが必要なユーザーを取得
            users_needing_outreach = await self.yamii_client.get_all_users_needing_outreach()

            if not users_needing_outreach:
                self.logger.debug("No users need outreach at this time")
                return

            self.logger.info(f"Found {len(users_needing_outreach)} users needing outreach")

            for outreach_data in users_needing_outreach:
                user_id = outreach_data.get("user_id")
                message = outreach_data.get("message")
                reason = outreach_data.get("reason")

                if not user_id or not message:
                    continue

                self.logger.info(f"Sending proactive outreach to {user_id} (reason: {reason})")

                try:
                    # チャットでメッセージを送信（プライバシー配慮）
                    await self.misskey_client.send_chat_message(user_id, message)
                    self.logger.info(f"Proactive outreach sent to {user_id}")
                except Exception as e:
                    self.logger.error(f"Failed to send outreach to {user_id}: {e}")

        except Exception as e:
            self.logger.error(f"Execute proactive outreach failed: {e}")


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

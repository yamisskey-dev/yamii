"""
Yamii Misskey Bot
Pythonで実装したMisskeyボット
"""

import asyncio
import logging
import re
from typing import Dict, Optional, Set
from datetime import datetime, timedelta

from .config import YamiiMisskeyBotConfig, load_config
from .misskey_client import MisskeyClient, MisskeyNote
from .yamii_client import YamiiClient, YamiiRequest


class YamiiMisskeyBot:
    """Yamii Misskeyボットメインクラス"""
    
    def __init__(self, config: YamiiMisskeyBotConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # ユーザーセッション管理
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
        self.user_preferences: Dict[str, Dict] = {}  # user_id -> preferences
        
        # クライアント
        self.misskey_client = MisskeyClient(config)
        self.yamii_client = YamiiClient(config)
        
        # 処理済みノート管理（重複処理防止）
        self.processed_notes: Set[str] = set()
        
    async def start(self):
        """ボットを開始"""
        self.logger.info("Starting Yamii Misskey Bot...")
        self.logger.info(f"Yamii API URL: {self.config.yamii_api_url}")
        self.logger.info(f"Misskey Instance: {self.config.misskey_instance_url}")
        
        # まずMisskeyクライアントとYamiiクライアントを初期化
        try:
            self.logger.info("Initializing Misskey client...")
            await self.misskey_client.__aenter__()
            self.logger.info("Misskey client initialized successfully")
            
            self.logger.info("Initializing Yamii client...")
            await self.yamii_client.__aenter__()
            self.logger.info("Yamii client initialized successfully")
            
            # yamiiサーバーの健全性チェック
            try:
                self.logger.info("Checking Yamii server health...")
                health = await self.yamii_client.health_check()
                self.logger.info(f"Yamii server status: {health.get('status')}")
            except Exception as e:
                self.logger.error(f"Yamii server health check failed: {e}")
                self.logger.error(f"Yamii API URL being used: {self.config.yamii_api_url}")
                # ヘルスチェックに失敗してもストリーミング接続は試行する
            
            # ストリーミング接続開始
            self.logger.info("Starting streaming connection...")
            try:
                # 受信ループをバックグラウンドタスクで起動
                asyncio.create_task(self.misskey_client.start_streaming(self._on_streaming_message))
                self.logger.info("Streaming connection task started")
            except Exception as e:
                self.logger.error(f"Failed to establish streaming connection: {e}")
                # 詳細なエラー情報をログ出力
                import traceback
                self.logger.error(f"Streaming error traceback: {traceback.format_exc()}")
                raise
                
        except Exception as e:
            self.logger.error(f"Critical error in bot startup: {e}")
            import traceback
            self.logger.error(f"Startup error traceback: {traceback.format_exc()}")
            raise
        finally:
            # リソースクリーンアップ
            try:
                await self.misskey_client.__aexit__(None, None, None)
                await self.yamii_client.__aexit__(None, None, None)
            except Exception as cleanup_error:
                self.logger.error(f"Error during cleanup: {cleanup_error}")
            
    async def _on_streaming_message(self, data: dict):
        """ストリーミングメッセージを処理"""
        try:
            self.logger.debug(f"Received streaming message: {data.get('type')}")
            if data.get("type") == "channel" and data.get("body", {}).get("type") == "note":
                note_data = data["body"]["body"]
                self.logger.info(f"Processing note from streaming: {note_data.get('user', {}).get('username', 'unknown')}")
                note = self.misskey_client._parse_note(note_data)
                await self._handle_note(note)
            else:
                self.logger.debug(f"Ignoring non-note message: {data.get('type')}")
                
        except Exception as e:
            self.logger.error(f"Error handling streaming message: {e}")
            
    async def _handle_note(self, note: MisskeyNote):
        """ノートを処理"""
        self.logger.info(f"Handling note from @{note.user_username}: {note.text[:50]}...")
        
        # 重複処理防止
        if note.id in self.processed_notes:
            self.logger.debug(f"Note {note.id} already processed, skipping")
            return
        self.processed_notes.add(note.id)
        
        # 古いノートIDを削除（メモリリーク防止）
        if len(self.processed_notes) > 1000:
            self.processed_notes = set(list(self.processed_notes)[-500:])
            
        # 自分の投稿はスキップ
        if note.user_id == self.misskey_client.bot_user_id:
            self.logger.debug(f"Skipping own note: {note.id}")
            return
        
        is_mentioned = self.misskey_client.is_mentioned(note)
        is_direct_message = self.misskey_client.is_direct_message(note)
        
        self.logger.info(f"Processing note {note.id}: mentioned={is_mentioned}, dm={is_direct_message}, visibility={note.visibility}")
        self.logger.debug(f"Bot user ID: {self.misskey_client.bot_user_id}, Note user: {note.user_id}")
        if note.visible_user_ids:
            self.logger.debug(f"Visible user IDs: {note.visible_user_ids}")
        
        if not is_mentioned and not is_direct_message:
            self.logger.info(f"Not mentioned and not in DM for note {note.id}, skipping")
            return
            
        self.logger.info(f"Processing mention from @{note.user_username}: {note.text[:50]}...")
        
        try:
            await self._process_mention(note)
        except Exception as e:
            self.logger.error(f"Error processing mention: {e}")
            await self._send_error_reply(note, "申し訳ございません。処理中にエラーが発生しました。")
            
    async def _process_mention(self, note: MisskeyNote):
        """メンションを処理"""
        message_text = self.misskey_client.extract_message_from_note(note)
        
        if not message_text:
            await self._send_reply(note, "人生相談をご利用いただきありがとうございます。どのようなことでお悩みでしょうか？お気軽にお話しください。")
            return
            
        # 管理コマンドをチェック
        if await self._handle_management_commands(note, message_text):
            return
            
        # プロファイルコマンドをチェック
        if await self._handle_profile_commands(note, message_text):
            return
            
        # カスタムプロンプトコマンドをチェック
        if await self._handle_custom_prompt_commands(note, message_text):
            return
            
        # yamiiコマンドをチェック
        if message_text.lower().startswith("yamii "):
            clean_message = message_text[5:].strip()
            if not clean_message:
                await self._send_reply(note, "人生相談をご利用いただきありがとうございます。どのようなことでお悩みでしょうか？お気軽にお話しください。")
                return
            message_text = clean_message
            
        # セッション終了コマンド
        if "終了" in message_text and note.user_id in self.user_sessions:
            del self.user_sessions[note.user_id]
            await self._send_reply(note, "人生相談を終了しました。また何かあればいつでもお声がけください。お疲れ様でした。")
            return
            
        # 人生相談を実行
        await self._handle_counseling(note, message_text)
        
    async def _handle_management_commands(self, note: MisskeyNote, text: str) -> bool:
        """管理コマンドを処理"""
        text_lower = text.lower().strip()
        
        if text_lower in ["/help", "ヘルプ"]:
            help_text = (
                "👁️‍🗨️ **YAMII 人生相談AI - ヘルプ**\n\n"
                "**📝 基本的な相談方法:**\n"
                "• `<相談内容>` - 人生相談を開始\n"
                "• `終了` - 相談を終了\n\n"
                "**📝 カスタムプロンプト:**\n"
                "• `/custom set <プロンプト内容>` - カスタムプロンプト設定\n"
                "• `/custom show` - カスタムプロンプト表示\n"
                "• `/custom delete` - カスタムプロンプト削除\n\n"
                "**👤 プロファイル管理:**\n"
                "• `/profile set <プロファイル情報>` - プロファイル設定\n"
                "• `/profile show` - プロファイル表示\n"
                "• `/profile delete` - プロファイル削除\n\n"
                "**⚙️ その他のコマンド:**\n"
                "• `/help` - このヘルプを表示\n"
                "• `/status` - サーバー状況確認"
            )
            await self._send_reply(note, help_text)
            return True
            
        elif text_lower in ["/status"]:
            try:
                health = await self.yamii_client.health_check()
                status_text = (
                    "🔍 **Yamii システム状況・バージョン情報:**\n\n"
                    f"**サーバー状況:**\n"
                    f"• ステータス: {'✅ 正常' if health.get('status') == 'healthy' else '❌ 異常'}\n"
                    f"• サーバーURL: {self.config.yamii_api_url}\n"
                    f"• 最終確認: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n\n"
                    f"**バージョン・機能情報:**\n"
                    f"• Yamiiボット: Python版 1.0.0\n"
                    f"• 最終更新: 2025年8月27日\n"
                    f"• 対応機能: 基本相談・カスタムプロンプト・プロファイル・感情分析・クライシス検出\n"
                    f"• プラットフォーム: Misskey"
                )
                await self._send_reply(note, status_text)
            except Exception as e:
                await self._send_reply(note, "❌ ステータス確認でエラーが発生しました。yamiiサーバーが起動していることを確認してください。")
            return True
            
        elif text_lower in ["yamii", "/start"]:
            quick_help = (
                "🚀 **Yamii クイックスタート**\n\n"
                "**今すぐ相談:**\n"
                "• 個人チャット: `<相談内容>` / パブリック: `@yamii <相談内容>`\n\n"
                "**コマンド:**\n"
                "• `/help` - 詳細ヘルプ\n"
                "• `/status` - システム状況\n"
                "• `/custom set <プロンプト>` - カスタムプロンプト\n"
                "• `/profile set <情報>` - プロファイル設定"
            )
            await self._send_reply(note, quick_help)
            return True
            
        return False
        
    async def _handle_custom_prompt_commands(self, note: MisskeyNote, text: str) -> bool:
        """カスタムプロンプトコマンドを処理"""
        if not text.lower().startswith("/custom"):
            return False
            
        try:
            if "show" in text.lower() or "表示" in text:
                prompt_data = await self.yamii_client.get_custom_prompt(note.user_id)
                if prompt_data.get("has_custom_prompt") and prompt_data.get("prompt"):
                    prompt = prompt_data["prompt"]
                    reply_text = f"📝 **現在のカスタムプロンプト:**\n\n{prompt.get('prompt_text', '')}\n\n削除: `yamii /custom delete`"
                else:
                    reply_text = "📝 **カスタムプロンプト:**\n\n現在設定されているカスタムプロンプトはありません。\n\n作成: `yamii /custom set <プロンプト内容>`"
                await self._send_reply(note, reply_text)
                return True
                
            elif "delete" in text.lower() or "削除" in text:
                success = await self.yamii_client.delete_custom_prompt(note.user_id)
                if success:
                    reply_text = "✅ カスタムプロンプトを削除しました。次回からデフォルトプロンプトを使用します。"
                else:
                    reply_text = "❌ カスタムプロンプトの削除に失敗しました。"
                await self._send_reply(note, reply_text)
                return True
                
            # カスタムプロンプト設定
            set_match = re.search(r'/custom set\s+(.+)', text, re.IGNORECASE | re.DOTALL)
            if set_match or "set" in text.lower():
                if set_match:
                    prompt_text = set_match.group(1).strip()
                    
                    # ダブルクォートで囲まれている場合は除去
                    if prompt_text.startswith('"') and prompt_text.endswith('"'):
                        prompt_text = prompt_text[1:-1]
                        
                    if not prompt_text:
                        reply_text = "❌ プロンプトの内容を入力してください。\n例: `yamii /custom set あなたは優しい先生です。丁寧に教えてください。`"
                    else:
                        success = await self.yamii_client.create_custom_prompt(note.user_id, prompt_text)
                        
                        if success:
                            # プロンプトの名前を自動生成
                            auto_name = prompt_text[:20] + ("..." if len(prompt_text) > 20 else "")
                            
                            # 確認
                            current_prompt = await self.yamii_client.get_custom_prompt(note.user_id)
                            has_prompt = current_prompt and current_prompt.get("has_custom_prompt")
                            
                            reply_text = (
                                f"✅ カスタムプロンプト「{auto_name}」を{'更新' if has_prompt else '作成'}しました！\n\n"
                                f"✨ **次回の相談から自動的に適用されます**\n\n"
                                f"📝 プロンプト内容 ({len(prompt_text)}文字):\n"
                                f"{prompt_text[:100] + '...' if len(prompt_text) > 100 else prompt_text}\n\n"
                                f"削除: `yamii /custom delete`"
                            )
                        else:
                            reply_text = "❌ カスタムプロンプトの作成に失敗しました。"
                else:
                    # 使用方法を表示
                    reply_text = (
                        "📝 **カスタムプロンプト管理:**\n\n"
                        "**作成・更新:**\n"
                        "`/custom set プロンプト内容`\n\n"
                        "**削除:**\n"
                        "`/custom delete`\n\n"
                        "**例:**\n"
                        "`/custom set あなたは優しい先生です。分からないことがあったら丁寧に教えてください。`\n\n"
                        "✨ カスタムプロンプトは1つのみ保存され、作成後すぐに自動適用されます。"
                    )
                    
                await self._send_reply(note, reply_text)
                return True
                
        except Exception as e:
            self.logger.error(f"Custom prompt command error: {e}")
            await self._send_reply(note, "カスタムプロンプト管理でエラーが発生しました。")
            
        return True
        
    async def _handle_profile_commands(self, note: MisskeyNote, text: str) -> bool:
        """プロファイルコマンドを処理"""
        text_lower = text.lower()
        
        if not text_lower.startswith("/profile"):
            return False
            
        try:
            if "show" in text_lower or "表示" in text:
                profile = await self.yamii_client.get_user_profile(note.user_id)
                
                if profile and profile.get("profile_text"):
                    profile_text = (
                        "👤 **あなたのプロファイル:**\n\n"
                        f"{profile['profile_text']}\n\n"
                        "⚙️ **設定変更:**\n"
                        "設定: `/profile set <プロファイル情報>`\n"
                        "削除: `/profile delete`"
                    )
                else:
                    profile_text = (
                        "プロファイルが設定されていません。`/profile set <プロファイル情報>` で"
                        "プロファイルを設定してください。\n\n"
                        "例: `/profile set 山田太郎、無職です。趣味は読書と散歩です。`"
                    )
                    
                await self._send_reply(note, profile_text)
                return True
                
            elif "delete" in text_lower:
                success = await self.yamii_client.delete_user_profile(note.user_id)
                if success:
                    reply_text = "✅ プロファイルを削除しました。次回からはデフォルト設定で人生相談を行います。"
                else:
                    reply_text = "❌ 削除するプロファイルが見つかりませんでした。"
                await self._send_reply(note, reply_text)
                return True
                
            # プロファイル設定
            set_match = re.search(r'/profile set\s+(.+)', text, re.IGNORECASE | re.DOTALL)
            if set_match:
                profile_info = set_match.group(1).strip()
                success = await self.yamii_client.set_user_profile(note.user_id, profile_info)
                
                if success:
                    reply_text = (
                        f"✅ プロファイルを設定しました。\n\n"
                        f"📝 **設定内容 ({len(profile_info)}文字):**\n"
                        f"{profile_info[:100] + '...' if len(profile_info) > 100 else profile_info}\n\n"
                        f"💡 この情報はAIが常に覚えておき、相談時により適切なアドバイスを提供するために使用されます。"
                    )
                else:
                    reply_text = "❌ プロファイル設定でエラーが発生しました。"
                    
                await self._send_reply(note, reply_text)
                return True
                
        except Exception as e:
            self.logger.error(f"Profile command error: {e}")
            await self._send_reply(note, "プロファイル管理でエラーが発生しました。")
            
        return True
        
    async def _handle_counseling(self, note: MisskeyNote, message: str):
        """人生相談を処理"""
        try:
            # yamiiリクエストを作成
            session_id = self.user_sessions.get(note.user_id)
            
            yamii_request = YamiiRequest(
                message=message,
                user_id=note.user_id,
                user_name=note.user_name or note.user_username,
                session_id=session_id,
                context={
                    "platform": "misskey",
                    "bot_name": self.config.bot_name
                }
            )
            
            # yamiiサーバーにリクエスト送信
            response = await self.yamii_client.send_counseling_request(yamii_request)
            
            if response:
                # セッションIDを記録
                self.user_sessions[note.user_id] = response.session_id
                
                # クライシス状況の場合は特別な対応
                if response.is_crisis:
                    crisis_message = (
                        f"{response.response}\n\n"
                        f"⚠️ **緊急時相談窓口**\n"
                        f"📞 {chr(10).join(self.config.crisis_hotline_numbers)}\n\n"
                        f"あなたは一人ではありません。"
                    )
                    await self._send_reply(note, crisis_message)
                else:
                    # 通常のカウンセリング応答
                    await self._send_reply(note, response.response)
                    
            else:
                await self._send_reply(note, "申し訳ありません。現在人生相談サービスが利用できません。時間を置いてもう一度お試しください。")
                
        except Exception as e:
            self.logger.error(f"Counseling error: {e}")
            
            # エラーの詳細分析
            error_message = "人生相談サービスでエラーが発生しました。"
            troubleshooting = ""
            
            error_str = str(e).lower()
            if "connection" in error_str or "refused" in error_str:
                error_message = "❌ yamiiサーバーに接続できませんでした。"
                troubleshooting = (
                    "\n\n🔧 **トラブルシューティング:**\n"
                    "• yamiiサーバーが起動していることを確認\n"
                    "• ネットワーク接続を確認"
                )
            elif "timeout" in error_str:
                error_message = "⏱️ サーバーからの応答がタイムアウトしました。"
                troubleshooting = (
                    "\n\n💡 **解決方法:**\n"
                    "• しばらく時間を置いてから再度お試しください\n"
                    "• 複雑な相談内容の場合は、短く分けてみてください"
                )
            elif "500" in error_str:
                error_message = "🔧 サーバー内部でエラーが発生しました。"
                troubleshooting = (
                    "\n\n📞 **サポート:**\n"
                    "• 問題が続く場合は管理者にお知らせください\n"
                    f"• エラー時刻: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}"
                )
                
            await self._send_reply(note, error_message + troubleshooting + "\n\nお手数をおかけして申し訳ございません。")
            
    async def _send_reply(self, note: MisskeyNote, text: str):
        """返信を送信"""
        try:
            await self.misskey_client.create_note(
                text=text,
                reply_id=note.id,
                visibility="home"
            )
            self.logger.info(f"Sent reply to @{note.user_username}")
        except Exception as e:
            self.logger.error(f"Failed to send reply: {e}")
            
    async def _send_error_reply(self, note: MisskeyNote, text: str):
        """エラー応答を送信"""
        await self._send_reply(note, text)


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
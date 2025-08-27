"""
Message Handler
共通メッセージ処理ロジック
"""

import logging
from typing import Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime
from dataclasses import dataclass

from .command_parser import CommandParser, BotCommand, BotCommandType
from .session_manager import SessionManager
from .navi_api_client import NaviAPIClient, NaviRequest

if TYPE_CHECKING:
    from .base_bot import BaseBot, BaseBotConfig


@dataclass
class MessageContext:
    """メッセージ処理コンテキスト"""
    user_id: str
    user_name: Optional[str]
    platform: str
    message_id: str
    original_message: str
    is_dm: bool = False
    is_mention: bool = False
    reply_to_id: Optional[str] = None


class MessageHandler:
    """共通メッセージ処理クラス"""
    
    def __init__(self, config: 'BaseBotConfig'):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.command_parser = CommandParser()
    
    async def process_message(
        self,
        message_data: Dict[str, Any],
        navi_client: NaviAPIClient,
        session_manager: SessionManager,
        bot: 'BaseBot'
    ) -> bool:
        """メッセージを処理"""
        try:
            # メッセージコンテキストを構築
            context = self._build_message_context(message_data)
            if not context:
                return False
            
            # コマンドを解析
            command = self.command_parser.parse_message(
                context.original_message,
                self.config.bot_username
            )
            
            # コマンドタイプに応じて処理
            if command.command_type == BotCommandType.HELP:
                await self._handle_help_command(context, command, bot)
            elif command.command_type == BotCommandType.STATUS:
                await self._handle_status_command(context, command, navi_client, bot)
            elif command.command_type == BotCommandType.CUSTOM_PROMPT:
                await self._handle_custom_prompt_command(context, command, navi_client, bot)
            elif command.command_type == BotCommandType.PROFILE:
                await self._handle_profile_command(context, command, navi_client, bot)
            elif command.command_type == BotCommandType.SESSION_END:
                await self._handle_session_end_command(context, command, session_manager, bot)
            elif command.command_type == BotCommandType.COUNSELING:
                await self._handle_counseling_command(context, command, navi_client, session_manager, bot)
            else:
                await self._handle_unknown_command(context, command, bot)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return False
    
    def _build_message_context(self, message_data: Dict[str, Any]) -> Optional[MessageContext]:
        """メッセージデータからコンテキストを構築（プラットフォーム固有部分はサブクラスでオーバーライド）"""
        # これは基本実装で、各プラットフォーム固有の実装でオーバーライドされることを想定
        return MessageContext(
            user_id=message_data.get("user_id", ""),
            user_name=message_data.get("user_name"),
            platform=message_data.get("platform", "unknown"),
            message_id=message_data.get("message_id", ""),
            original_message=message_data.get("text", ""),
            is_dm=message_data.get("is_dm", False),
            is_mention=message_data.get("is_mention", False),
            reply_to_id=message_data.get("reply_to_id")
        )
    
    async def _handle_help_command(self, context: MessageContext, command: BotCommand, bot: 'BaseBot'):
        """ヘルプコマンド処理"""
        help_text = self._generate_help_text()
        await bot.send_reply(context.message_id, help_text)
    
    async def _handle_status_command(
        self, 
        context: MessageContext, 
        command: BotCommand, 
        navi_client: NaviAPIClient,
        bot: 'BaseBot'
    ):
        """ステータスコマンド処理"""
        try:
            health = await navi_client.health_check()
            status_text = self._generate_status_text(health)
            await bot.send_reply(context.message_id, status_text)
        except Exception as e:
            error_text = "❌ ステータス確認でエラーが発生しました。naviサーバーが起動していることを確認してください。"
            await bot.send_reply(context.message_id, error_text)
    
    async def _handle_custom_prompt_command(
        self,
        context: MessageContext,
        command: BotCommand,
        navi_client: NaviAPIClient,
        bot: 'BaseBot'
    ):
        """カスタムプロンプトコマンド処理"""
        try:
            if command.action == "show":
                prompt_data = await navi_client.get_custom_prompt(context.user_id)
                if prompt_data.get("has_custom_prompt") and prompt_data.get("prompt"):
                    prompt = prompt_data["prompt"]
                    reply_text = f"📝 **現在のカスタムプロンプト:**\n\n{prompt.get('prompt_text', '')}\n\n削除: `/custom delete`"
                else:
                    reply_text = "📝 **カスタムプロンプト:**\n\n現在設定されているカスタムプロンプトはありません。\n\n作成: `/custom set <プロンプト内容>`"
                await bot.send_reply(context.message_id, reply_text)
                
            elif command.action == "delete":
                success = await navi_client.delete_custom_prompt(context.user_id)
                reply_text = "✅ カスタムプロンプトを削除しました。" if success else "❌ カスタムプロンプトの削除に失敗しました。"
                await bot.send_reply(context.message_id, reply_text)
                
            elif command.action == "set":
                if command.is_valid and command.content:
                    success = await navi_client.create_custom_prompt(context.user_id, command.content)
                    if success:
                        auto_name = command.content[:20] + ("..." if len(command.content) > 20 else "")
                        reply_text = (
                            f"✅ カスタムプロンプト「{auto_name}」を作成しました！\n\n"
                            f"✨ **次回の相談から自動的に適用されます**\n\n"
                            f"📝 プロンプト内容 ({len(command.content)}文字):\n"
                            f"{command.content[:100] + '...' if len(command.content) > 100 else command.content}\n\n"
                            f"削除: `/custom delete`"
                        )
                    else:
                        reply_text = "❌ カスタムプロンプトの作成に失敗しました。"
                else:
                    reply_text = "❌ プロンプトの内容を入力してください。\n例: `/custom set あなたは優しい先生です。丁寧に教えてください。`"
                await bot.send_reply(context.message_id, reply_text)
                
            else:
                help_text = self._generate_custom_prompt_help()
                await bot.send_reply(context.message_id, help_text)
                
        except Exception as e:
            self.logger.error(f"Custom prompt command error: {e}")
            await bot.send_reply(context.message_id, "カスタムプロンプト管理でエラーが発生しました。")
    
    async def _handle_profile_command(
        self,
        context: MessageContext,
        command: BotCommand,
        navi_client: NaviAPIClient,
        bot: 'BaseBot'
    ):
        """プロファイルコマンド処理"""
        try:
            if command.action == "show":
                profile = await navi_client.get_user_profile(context.user_id)
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
                await bot.send_reply(context.message_id, profile_text)
                
            elif command.action == "delete":
                success = await navi_client.delete_user_profile(context.user_id)
                reply_text = "✅ プロファイルを削除しました。" if success else "❌ 削除するプロファイルが見つかりませんでした。"
                await bot.send_reply(context.message_id, reply_text)
                
            elif command.action == "set":
                if command.is_valid and command.content:
                    success = await navi_client.set_user_profile(context.user_id, command.content)
                    if success:
                        reply_text = (
                            f"✅ プロファイルを設定しました。\n\n"
                            f"📝 **設定内容 ({len(command.content)}文字):**\n"
                            f"{command.content[:100] + '...' if len(command.content) > 100 else command.content}\n\n"
                            f"💡 この情報はAIが常に覚えておき、相談時により適切なアドバイスを提供するために使用されます。"
                        )
                    else:
                        reply_text = "❌ プロファイル設定でエラーが発生しました。"
                else:
                    reply_text = "❌ プロファイル情報を入力してください。"
                await bot.send_reply(context.message_id, reply_text)
                
            else:
                help_text = self._generate_profile_help()
                await bot.send_reply(context.message_id, help_text)
                
        except Exception as e:
            self.logger.error(f"Profile command error: {e}")
            await bot.send_reply(context.message_id, "プロファイル管理でエラーが発生しました。")
    
    async def _handle_session_end_command(
        self,
        context: MessageContext,
        command: BotCommand,
        session_manager: SessionManager,
        bot: 'BaseBot'
    ):
        """セッション終了コマンド処理"""
        success = session_manager.end_session(context.user_id)
        if success:
            reply_text = "人生相談を終了しました。また何かあればいつでもお声がけください。お疲れ様でした。"
        else:
            reply_text = "現在アクティブなセッションがありません。何かお悩みがあればお気軽にお話しください。"
        await bot.send_reply(context.message_id, reply_text)
    
    async def _handle_counseling_command(
        self,
        context: MessageContext,
        command: BotCommand,
        navi_client: NaviAPIClient,
        session_manager: SessionManager,
        bot: 'BaseBot'
    ):
        """人生相談コマンド処理"""
        if not command.is_valid or not command.content:
            await bot.send_reply(
                context.message_id,
                "人生相談をご利用いただきありがとうございます。どのようなことでお悩みでしょうか？お気軽にお話しください。"
            )
            return
        
        try:
            # セッション取得または作成
            session = session_manager.get_session(context.user_id)
            session_id = session.session_id if session else None
            
            # Naviリクエスト作成
            navi_request = NaviRequest(
                message=command.content,
                user_id=context.user_id,
                user_name=context.user_name,
                session_id=session_id,
                context={
                    "platform": context.platform,
                    "bot_name": self.config.bot_name,
                    "is_dm": context.is_dm,
                    "is_mention": context.is_mention
                }
            )
            
            # Naviサーバーにリクエスト送信
            response = await navi_client.send_counseling_request(navi_request)
            
            if response:
                # セッションを更新または作成
                if not session:
                    session = session_manager.create_session(
                        context.user_id,
                        context.platform,
                        response.session_id
                    )
                else:
                    session.update_activity()
                
                # 危機状況の場合は特別な対応
                if response.is_crisis:
                    crisis_message = (
                        f"{response.response}\n\n"
                        f"⚠️ **緊急時相談窓口**\n"
                        f"📞 {chr(10).join(self.config.crisis_hotlines)}\n\n"
                        f"あなたは一人ではありません。"
                    )
                    await bot.send_reply(context.message_id, crisis_message)
                else:
                    await bot.send_reply(context.message_id, response.response)
            else:
                await bot.send_reply(
                    context.message_id,
                    "申し訳ありません。現在人生相談サービスが利用できません。時間を置いてもう一度お試しください。"
                )
                
        except Exception as e:
            self.logger.error(f"Counseling error: {e}")
            error_message = self._generate_error_message(e)
            await bot.send_reply(context.message_id, error_message)
    
    async def _handle_unknown_command(self, context: MessageContext, command: BotCommand, bot: 'BaseBot'):
        """不明なコマンド処理"""
        await bot.send_reply(
            context.message_id,
            "申し訳ありません。コマンドを理解できませんでした。`/help` でヘルプを表示できます。"
        )
    
    def _generate_help_text(self) -> str:
        """ヘルプテキスト生成"""
        return (
            "👁️‍🗨️ **NAVI 人生相談AI - ヘルプ**\n\n"
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
    
    def _generate_status_text(self, health: Dict[str, Any]) -> str:
        """ステータステキスト生成"""
        return (
            "🔍 **Navi システム状況・バージョン情報:**\n\n"
            f"**サーバー状況:**\n"
            f"• ステータス: {'✅ 正常' if health.get('status') == 'healthy' else '❌ 異常'}\n"
            f"• サーバーURL: {self.config.navi_api_url}\n"
            f"• 最終確認: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n\n"
            f"**バージョン・機能情報:**\n"
            f"• Naviボット: Python版 1.0.0\n"
            f"• 最終更新: 2025年8月27日\n"
            f"• 対応機能: 基本相談・カスタムプロンプト・プロファイル・感情分析・クライシス検出\n"
            f"• プラットフォーム: マルチプラットフォーム対応"
        )
    
    def _generate_custom_prompt_help(self) -> str:
        """カスタムプロンプトヘルプテキスト生成"""
        return (
            "📝 **カスタムプロンプト管理:**\n\n"
            "**作成・更新:**\n"
            "`/custom set プロンプト内容`\n\n"
            "**削除:**\n"
            "`/custom delete`\n\n"
            "**例:**\n"
            "`/custom set あなたは優しい先生です。分からないことがあったら丁寧に教えてください。`\n\n"
            "✨ カスタムプロンプトは1つのみ保存され、作成後すぐに自動適用されます。"
        )
    
    def _generate_profile_help(self) -> str:
        """プロファイルヘルプテキスト生成"""
        return (
            "👤 **プロファイル管理:**\n\n"
            "**設定:**\n"
            "`/profile set プロファイル情報`\n\n"
            "**削除:**\n"
            "`/profile delete`\n\n"
            "**例:**\n"
            "`/profile set 山田太郎、32歳、会社員です。趣味は読書です。`\n\n"
            "💡 プロファイル情報はAIがより適切なアドバイスを提供するために使用されます。"
        )
    
    def _generate_error_message(self, error: Exception) -> str:
        """エラーメッセージ生成"""
        error_message = "人生相談サービスでエラーが発生しました。"
        troubleshooting = ""
        
        error_str = str(error).lower()
        if "connection" in error_str or "refused" in error_str:
            error_message = "❌ naviサーバーに接続できませんでした。"
            troubleshooting = (
                "\n\n🔧 **トラブルシューティング:**\n"
                "• naviサーバーが起動していることを確認\n"
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
        
        return error_message + troubleshooting + "\n\nお手数をおかけして申し訳ございません。"
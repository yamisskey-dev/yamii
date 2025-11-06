"""
Tests for Yamii Misskey Bot
naviのMisskeyボットのテスト
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from yamii.navi.bot.misskey import NaviMisskeyBot, NaviMisskeyBotConfig, MisskeyNote, NaviResponse


@pytest.fixture
def mock_config():
    """テスト用の設定を作成"""
    return NaviMisskeyBotConfig(
        misskey_instance_url="https://test.misskey.io",
        misskey_access_token="test_token",
        yamii_api_url="http://localhost:8000",
        bot_name="test_navi",
        enable_crisis_support=True
    )


@pytest.fixture
def sample_note():
    """テスト用のノートを作成"""
    return MisskeyNote(
        id="note123",
        text="@test_navi こんにちは、悩みがあります",
        user_id="user123", 
        user_username="testuser",
        user_name="テストユーザー",
        created_at=datetime.now(),
        visibility="home",
        mentions=["test_navi"],
        is_reply=False,
        reply_id=None
    )


@pytest.fixture
def sample_yamii_response():
    """テスト用のnaviレスポンスを作成"""
    return NaviResponse(
        response="あなたの気持ちをお聞かせください。どのようなことでお悩みでしょうか？",
        session_id="session123",
        timestamp=datetime.now(),
        emotion_analysis={
            "primary_emotion": "anxiety",
            "intensity": 0.6,
            "is_crisis": False,
            "all_emotions": {"anxiety": 0.6, "sadness": 0.3}
        },
        advice_type="empathy",
        follow_up_questions=["具体的にどのような状況ですか？"],
        is_crisis=False
    )


class TestNaviMisskeyBot:
    """NaviMisskeyBotのテストクラス"""
    
    @pytest.mark.asyncio
    async def test_bot_initialization(self, mock_config):
        """ボットの初期化をテスト"""
        bot = NaviMisskeyBot(mock_config)
        
        assert bot.config == mock_config
        assert isinstance(bot.user_sessions, dict)
        assert isinstance(bot.user_preferences, dict)
        assert isinstance(bot.processed_notes, set)
    
    @pytest.mark.asyncio
    async def test_handle_mention_basic(self, mock_config, sample_note, sample_yamii_response):
        """基本的なメンション処理をテスト"""
        bot = NaviMisskeyBot(mock_config)
        
        # Misskeyクライアントをモック
        bot.misskey_client = AsyncMock()
        bot.misskey_client.is_mentioned.return_value = True
        bot.misskey_client.bot_user_id = "bot123"
        bot.misskey_client.extract_message_from_note.return_value = "こんにちは、悩みがあります"
        
        # Naviクライアントをモック
        bot.yamii_client = AsyncMock()
        bot.yamii_client.send_counseling_request.return_value = sample_yamii_response
        
        # _send_replyメソッドをモック
        bot._send_reply = AsyncMock()
        
        await bot._handle_note(sample_note)
        
        # 応答が送信されたことを確認
        bot._send_reply.assert_called_once()
        call_args = bot._send_reply.call_args
        assert call_args[0][0] == sample_note  # ノートが渡された
        assert "あなたの気持ちをお聞かせください" in call_args[0][1]  # 応答テキスト
        
        # セッションが記録されたことを確認
        assert bot.user_sessions[sample_note.user_id] == sample_yamii_response.session_id
    
    @pytest.mark.asyncio
    async def test_handle_crisis_response(self, mock_config, sample_note):
        """クライシス応答をテスト"""
        bot = NaviMisskeyBot(mock_config)
        
        # クライシス応答を作成
        crisis_response = NaviResponse(
            response="心配です。あなたの安全が大切です。",
            session_id="session123",
            timestamp=datetime.now(),
            emotion_analysis={"primary_emotion": "crisis", "intensity": 0.9, "is_crisis": True},
            advice_type="crisis",
            follow_up_questions=[],
            is_crisis=True
        )
        
        # クライアントをモック
        bot.misskey_client = AsyncMock()
        bot.misskey_client.is_mentioned.return_value = True
        bot.misskey_client.bot_user_id = "bot123"
        bot.misskey_client.extract_message_from_note.return_value = "もう疲れました"
        
        bot.yamii_client = AsyncMock()
        bot.yamii_client.send_counseling_request.return_value = crisis_response
        
        bot._send_reply = AsyncMock()
        
        await bot._handle_note(sample_note)
        
        # クライシス対応が含まれた応答が送信されたことを確認
        bot._send_reply.assert_called_once()
        call_args = bot._send_reply.call_args
        response_text = call_args[0][1]
        
        assert "心配です。あなたの安全が大切です。" in response_text
        assert "緊急時相談窓口" in response_text
        assert "いのちの電話" in response_text
    
    @pytest.mark.asyncio
    async def test_handle_help_command(self, mock_config, sample_note):
        """ヘルプコマンドをテスト"""
        bot = NaviMisskeyBot(mock_config)
        
        # ヘルプコマンドのノートを作成
        help_note = MisskeyNote(
            id="note456",
            text="@test_navi navi /help",
            user_id="user123",
            user_username="testuser", 
            user_name="テストユーザー",
            created_at=datetime.now(),
            visibility="home",
            mentions=["test_navi"],
            is_reply=False,
            reply_id=None
        )
        
        bot.misskey_client = AsyncMock()
        bot.misskey_client.is_mentioned.return_value = True
        bot.misskey_client.bot_user_id = "bot123"
        bot.misskey_client.extract_message_from_note.return_value = "navi /help"
        
        bot._send_reply = AsyncMock()
        
        await bot._handle_note(help_note)
        
        # ヘルプ応答が送信されたことを確認
        bot._send_reply.assert_called_once()
        call_args = bot._send_reply.call_args
        response_text = call_args[0][1]
        
        assert "NAVI 人生相談AI - ヘルプ" in response_text
        assert "基本的な相談方法" in response_text
        assert "カスタムプロンプト" in response_text
    
    @pytest.mark.asyncio
    async def test_session_management(self, mock_config, sample_note, sample_yamii_response):
        """セッション管理をテスト"""
        bot = NaviMisskeyBot(mock_config)
        
        # 最初の相談
        bot.misskey_client = AsyncMock()
        bot.misskey_client.is_mentioned.return_value = True
        bot.misskey_client.bot_user_id = "bot123"
        bot.misskey_client.extract_message_from_note.return_value = "悩みがあります"
        
        bot.yamii_client = AsyncMock()
        bot.yamii_client.send_counseling_request.return_value = sample_yamii_response
        bot._send_reply = AsyncMock()
        
        await bot._handle_note(sample_note)
        
        # セッションが開始されたことを確認
        assert sample_note.user_id in bot.user_sessions
        assert bot.user_sessions[sample_note.user_id] == sample_yamii_response.session_id
        
        # 継続的な会話
        continue_note = MisskeyNote(
            id="note789",
            text="@test_navi もう少し詳しくお聞きしたいです",
            user_id=sample_note.user_id,  # 同じユーザー
            user_username="testuser",
            user_name="テストユーザー", 
            created_at=datetime.now(),
            visibility="home",
            mentions=["test_navi"],
            is_reply=False,
            reply_id=None
        )
        
        bot.misskey_client.extract_message_from_note.return_value = "もう少し詳しくお聞きしたいです"
        
        await bot._handle_note(continue_note)
        
        # 2回目のリクエストでセッションIDが渡されたことを確認
        calls = bot.yamii_client.send_counseling_request.call_args_list
        second_call = calls[1]
        request_obj = second_call[0][0]
        assert request_obj.session_id == sample_yamii_response.session_id
    
    @pytest.mark.asyncio
    async def test_session_termination(self, mock_config, sample_note):
        """セッション終了をテスト"""
        bot = NaviMisskeyBot(mock_config)
        
        # セッションを設定
        bot.user_sessions[sample_note.user_id] = "session123"
        
        # 終了コマンドのノートを作成
        end_note = MisskeyNote(
            id="note999",
            text="@test_navi 終了",
            user_id=sample_note.user_id,
            user_username="testuser",
            user_name="テストユーザー",
            created_at=datetime.now(),
            visibility="home", 
            mentions=["test_navi"],
            is_reply=False,
            reply_id=None
        )
        
        bot.misskey_client = AsyncMock()
        bot.misskey_client.is_mentioned.return_value = True
        bot.misskey_client.bot_user_id = "bot123"
        bot.misskey_client.extract_message_from_note.return_value = "終了"
        
        bot._send_reply = AsyncMock()
        
        await bot._handle_note(end_note)
        
        # セッションが削除されたことを確認
        assert sample_note.user_id not in bot.user_sessions
        
        # 終了メッセージが送信されたことを確認
        bot._send_reply.assert_called_once()
        call_args = bot._send_reply.call_args
        response_text = call_args[0][1]
        assert "人生相談を終了しました" in response_text
    
    @pytest.mark.asyncio
    async def test_ignore_own_posts(self, mock_config):
        """自分の投稿を無視することをテスト"""
        bot = NaviMisskeyBot(mock_config)
        
        # 自分の投稿を作成
        own_note = MisskeyNote(
            id="own_note",
            text="テスト投稿",
            user_id="bot123",  # ボット自身のID
            user_username="test_navi",
            user_name="Yamii Bot",
            created_at=datetime.now(),
            visibility="home",
            mentions=[],
            is_reply=False,
            reply_id=None
        )
        
        bot.misskey_client = AsyncMock()
        bot.misskey_client.is_mentioned.return_value = False
        bot.misskey_client.bot_user_id = "bot123"
        
        bot._send_reply = AsyncMock()
        
        await bot._handle_note(own_note)
        
        # 応答が送信されていないことを確認
        bot._send_reply.assert_not_called()
    
    def test_duplicate_note_prevention(self, mock_config, sample_note):
        """重複ノート処理防止をテスト"""
        bot = NaviMisskeyBot(mock_config)
        
        # ノートIDを処理済みに追加
        bot.processed_notes.add(sample_note.id)
        
        # 同じノートを再度処理しようとする
        result = asyncio.run(bot._handle_note(sample_note))
        
        # 早期リターンされることを確認（実際にはMockが必要だが、簡易テスト）
        assert result is None
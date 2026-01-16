"""
Tests for Yamii Misskey Bot
yamiiのMisskeyボットのテスト
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from yamii.bot.misskey import (
    MisskeyNote,
    YamiiMisskeyBot,
    YamiiMisskeyBotConfig,
    YamiiResponse,
)


@pytest.fixture
def mock_config():
    """テスト用の設定を作成"""
    return YamiiMisskeyBotConfig(
        misskey_instance_url="https://test.misskey.io",
        misskey_access_token="test_token",
        misskey_bot_user_id="bot123",
        yamii_api_url="http://localhost:8000",
        bot_name="test_yamii",
    )


@pytest.fixture
def sample_note():
    """テスト用のノートを作成"""
    return MisskeyNote(
        id="note123",
        text="@test_yamii こんにちは、悩みがあります",
        user_id="user123",
        user_username="testuser",
        user_name="テストユーザー",
        created_at=datetime.now(),
        visibility="home",
        mentions=["test_yamii"],
        is_reply=False,
        reply_id=None
    )


@pytest.fixture
def sample_yamii_response():
    """テスト用のyamiiレスポンスを作成"""
    return YamiiResponse(
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


class TestYamiiMisskeyBot:
    """YamiiMisskeyBotのテストクラス"""

    @pytest.mark.asyncio
    async def test_bot_initialization(self, mock_config):
        """ボットの初期化をテスト"""
        bot = YamiiMisskeyBot(mock_config)

        assert bot.config == mock_config
        assert isinstance(bot.user_sessions, dict)
        # processed_notesはLRUSetでset-likeなインターフェースを持つ
        assert hasattr(bot.processed_notes, 'add')
        assert hasattr(bot.processed_notes, '__contains__')

    @pytest.mark.asyncio
    async def test_handle_mention(self, mock_config, sample_note, sample_yamii_response):
        """メンション処理をテスト"""
        bot = YamiiMisskeyBot(mock_config)

        bot.misskey_client = Mock()
        bot.misskey_client.is_mentioned.return_value = True
        bot.misskey_client.is_reply_to_bot.return_value = False
        bot.misskey_client.is_direct_message.return_value = False
        bot.misskey_client.bot_user_id = "bot123"
        bot.misskey_client.extract_message_from_note.return_value = "こんにちは、悩みがあります"

        bot.yamii_client = AsyncMock()
        # Bot薄型化: API側でメッセージ分類
        bot.yamii_client.classify_message.return_value = {
            "is_command": False,
            "is_empty": False,
            "should_counsel": True,
        }
        bot.yamii_client.send_counseling_request.return_value = sample_yamii_response

        bot._send_reply = AsyncMock()

        await bot._handle_note(sample_note)

        bot._send_reply.assert_called_once()
        call_args = bot._send_reply.call_args
        assert call_args[0][0] == sample_note
        assert "あなたの気持ちをお聞かせください" in call_args[0][1]
        assert bot.user_sessions[sample_note.user_id] == sample_yamii_response.session_id

    @pytest.mark.asyncio
    async def test_handle_reply(self, mock_config, sample_yamii_response):
        """リプライ処理をテスト"""
        bot = YamiiMisskeyBot(mock_config)

        reply_note = MisskeyNote(
            id="note456",
            text="もう少し詳しく聞きたいです",
            user_id="user123",
            user_username="testuser",
            user_name="テストユーザー",
            created_at=datetime.now(),
            visibility="home",
            mentions=[],
            is_reply=True,
            reply_id="note123"
        )

        bot.misskey_client = Mock()
        bot.misskey_client.is_mentioned.return_value = False
        bot.misskey_client.is_reply_to_bot.return_value = True
        bot.misskey_client.is_direct_message.return_value = False
        bot.misskey_client.bot_user_id = "bot123"
        bot.misskey_client.extract_message_from_note.return_value = "もう少し詳しく聞きたいです"

        bot.yamii_client = AsyncMock()
        bot.yamii_client.classify_message.return_value = {
            "is_command": False,
            "is_empty": False,
            "should_counsel": True,
        }
        bot.yamii_client.send_counseling_request.return_value = sample_yamii_response

        bot._send_reply = AsyncMock()

        await bot._handle_note(reply_note)

        bot._send_reply.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_dm(self, mock_config, sample_yamii_response):
        """DM処理をテスト"""
        bot = YamiiMisskeyBot(mock_config)

        dm_note = MisskeyNote(
            id="note789",
            text="プライベートな相談があります",
            user_id="user123",
            user_username="testuser",
            user_name="テストユーザー",
            created_at=datetime.now(),
            visibility="specified",
            mentions=[],
            is_reply=False,
            reply_id=None,
            visible_user_ids=["bot123"]
        )

        bot.misskey_client = Mock()
        bot.misskey_client.is_mentioned.return_value = False
        bot.misskey_client.is_reply_to_bot.return_value = False
        bot.misskey_client.is_direct_message.return_value = True
        bot.misskey_client.bot_user_id = "bot123"
        bot.misskey_client.extract_message_from_note.return_value = "プライベートな相談があります"

        bot.yamii_client = AsyncMock()
        bot.yamii_client.classify_message.return_value = {
            "is_command": False,
            "is_empty": False,
            "should_counsel": True,
        }
        bot.yamii_client.send_counseling_request.return_value = sample_yamii_response

        bot._send_reply = AsyncMock()

        await bot._handle_note(dm_note)

        bot._send_reply.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_crisis_response(self, mock_config, sample_note):
        """クライシス応答をテスト"""
        bot = YamiiMisskeyBot(mock_config)

        crisis_response = YamiiResponse(
            response="心配です。あなたの安全が大切です。",
            session_id="session123",
            timestamp=datetime.now(),
            emotion_analysis={"primary_emotion": "crisis", "intensity": 0.9, "is_crisis": True},
            advice_type="crisis",
            follow_up_questions=[],
            is_crisis=True,
            # API側から返される整形済みレスポンス
            formatted_response="心配です。あなたの安全が大切です。\n\n⚠️ **相談窓口**\n📞 いのちの電話: 0570-783-556\n\nあなたは一人ではありません。",
            crisis_resources=["いのちの電話: 0570-783-556"],
        )

        bot.misskey_client = Mock()
        bot.misskey_client.is_mentioned.return_value = True
        bot.misskey_client.is_reply_to_bot.return_value = False
        bot.misskey_client.is_direct_message.return_value = False
        bot.misskey_client.bot_user_id = "bot123"
        bot.misskey_client.extract_message_from_note.return_value = "もう疲れました"

        bot.yamii_client = AsyncMock()
        bot.yamii_client.classify_message.return_value = {
            "is_command": False,
            "is_empty": False,
            "should_counsel": True,
        }
        bot.yamii_client.send_counseling_request.return_value = crisis_response

        bot._send_reply = AsyncMock()

        await bot._handle_note(sample_note)

        bot._send_reply.assert_called_once()
        call_args = bot._send_reply.call_args
        response_text = call_args[0][1]

        assert "心配です。あなたの安全が大切です。" in response_text
        assert "相談窓口" in response_text

    @pytest.mark.asyncio
    async def test_handle_help_command(self, mock_config, sample_note):
        """ヘルプコマンドをテスト"""
        bot = YamiiMisskeyBot(mock_config)

        help_note = MisskeyNote(
            id="note456",
            text="@test_yamii /help",
            user_id="user123",
            user_username="testuser",
            user_name="テストユーザー",
            created_at=datetime.now(),
            visibility="home",
            mentions=["test_yamii"],
            is_reply=False,
            reply_id=None
        )

        bot.misskey_client = Mock()
        bot.misskey_client.is_mentioned.return_value = True
        bot.misskey_client.is_reply_to_bot.return_value = False
        bot.misskey_client.is_direct_message.return_value = False
        bot.misskey_client.bot_user_id = "bot123"
        bot.misskey_client.extract_message_from_note.return_value = "/help"

        # Bot薄型化: API側でコマンド判定＋レスポンス取得
        bot.yamii_client = AsyncMock()
        bot.yamii_client.classify_message.return_value = {
            "is_command": True,
            "command_type": "help",
            "is_empty": False,
            "should_counsel": False,
        }
        bot.yamii_client.get_help.return_value = """**Yamii - 相談AI**

話しかけるだけで相談できます。
- メンション: @yamii 相談内容
- リプライ: 会話を続ける
- DM: プライベートな相談

何でもお気軽にどうぞ。"""

        bot._send_reply = AsyncMock()

        await bot._handle_note(help_note)

        bot._send_reply.assert_called_once()
        call_args = bot._send_reply.call_args
        response_text = call_args[0][1]

        assert "Yamii" in response_text
        assert "メンション" in response_text
        assert "リプライ" in response_text

    @pytest.mark.asyncio
    async def test_session_continues(self, mock_config, sample_note, sample_yamii_response):
        """セッション継続をテスト"""
        bot = YamiiMisskeyBot(mock_config)

        bot.misskey_client = Mock()
        bot.misskey_client.is_mentioned.return_value = True
        bot.misskey_client.is_reply_to_bot.return_value = False
        bot.misskey_client.is_direct_message.return_value = False
        bot.misskey_client.bot_user_id = "bot123"
        bot.misskey_client.extract_message_from_note.return_value = "悩みがあります"

        bot.yamii_client = AsyncMock()
        bot.yamii_client.classify_message.return_value = {
            "is_command": False,
            "is_empty": False,
            "should_counsel": True,
        }
        bot.yamii_client.send_counseling_request.return_value = sample_yamii_response
        bot._send_reply = AsyncMock()

        await bot._handle_note(sample_note)

        assert sample_note.user_id in bot.user_sessions
        assert bot.user_sessions[sample_note.user_id] == sample_yamii_response.session_id

        # 継続会話
        continue_note = MisskeyNote(
            id="note789",
            text="@test_yamii もう少し詳しくお聞きしたいです",
            user_id=sample_note.user_id,
            user_username="testuser",
            user_name="テストユーザー",
            created_at=datetime.now(),
            visibility="home",
            mentions=["test_yamii"],
            is_reply=False,
            reply_id=None
        )

        bot.misskey_client.extract_message_from_note.return_value = "もう少し詳しくお聞きしたいです"

        await bot._handle_note(continue_note)

        calls = bot.yamii_client.send_counseling_request.call_args_list
        second_call = calls[1]
        request_obj = second_call[0][0]
        assert request_obj.session_id == sample_yamii_response.session_id

    @pytest.mark.asyncio
    async def test_ignore_own_posts(self, mock_config):
        """自分の投稿を無視することをテスト"""
        bot = YamiiMisskeyBot(mock_config)

        own_note = MisskeyNote(
            id="own_note",
            text="テスト投稿",
            user_id="bot123",
            user_username="test_yamii",
            user_name="Yamii Bot",
            created_at=datetime.now(),
            visibility="home",
            mentions=[],
            is_reply=False,
            reply_id=None
        )

        bot.misskey_client = Mock()
        bot.misskey_client.is_mentioned.return_value = False
        bot.misskey_client.is_reply_to_bot.return_value = False
        bot.misskey_client.is_direct_message.return_value = False
        bot.misskey_client.bot_user_id = "bot123"

        bot._send_reply = AsyncMock()

        await bot._handle_note(own_note)

        bot._send_reply.assert_not_called()

    def test_duplicate_note_prevention(self, mock_config, sample_note):
        """重複ノート処理防止をテスト"""
        bot = YamiiMisskeyBot(mock_config)

        bot.processed_notes.add(sample_note.id)

        result = asyncio.run(bot._handle_note(sample_note))

        assert result is None


class TestMisskeyClient:
    """MisskeyClientのテスト"""

    def test_is_direct_message(self, mock_config):
        """DMチェックをテスト"""
        from yamii.bot.misskey import MisskeyClient

        client = MisskeyClient(mock_config)
        client.bot_user_id = "bot123"

        dm_note = MisskeyNote(
            id="note1",
            text="こんにちは",
            user_id="user123",
            user_username="testuser",
            user_name="テスト",
            created_at=datetime.now(),
            visibility="specified",
            mentions=[],
            is_reply=False,
            reply_id=None,
            visible_user_ids=["bot123", "user456"]
        )
        assert client.is_direct_message(dm_note) is True

        normal_note = MisskeyNote(
            id="note2",
            text="こんにちは",
            user_id="user123",
            user_username="testuser",
            user_name="テスト",
            created_at=datetime.now(),
            visibility="home",
            mentions=[],
            is_reply=False,
            reply_id=None
        )
        assert client.is_direct_message(normal_note) is False

    def test_is_reply_to_bot(self, mock_config):
        """リプライチェックをテスト"""
        from yamii.bot.misskey import MisskeyClient

        client = MisskeyClient(mock_config)

        reply_note = MisskeyNote(
            id="note1",
            text="返信です",
            user_id="user123",
            user_username="testuser",
            user_name="テスト",
            created_at=datetime.now(),
            visibility="home",
            mentions=[],
            is_reply=True,
            reply_id="parent_note"
        )
        assert client.is_reply_to_bot(reply_note) is True

        normal_note = MisskeyNote(
            id="note2",
            text="通常投稿",
            user_id="user123",
            user_username="testuser",
            user_name="テスト",
            created_at=datetime.now(),
            visibility="home",
            mentions=[],
            is_reply=False,
            reply_id=None
        )
        assert client.is_reply_to_bot(normal_note) is False

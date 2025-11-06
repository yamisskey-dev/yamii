"""
ユーザープロファイル機能のテスト
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any, List, Optional
import json
import tempfile
import shutil
from pathlib import Path

from yamii.user_profile import UserProfileManager, PERSONALITY_OPTIONS, CHARACTERISTIC_OPTIONS


class TestUserProfileManager:
    """ユーザープロファイル管理のテストクラス"""

    @pytest.fixture
    def temp_data_dir(self):
        """テスト用の一時ディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def profile_manager(self, temp_data_dir):
        """テスト用のプロファイル管理インスタンス"""
        return UserProfileManager(temp_data_dir)

    def test_profile_manager_initialization(self, profile_manager):
        """プロファイル管理の初期化テスト"""
        assert profile_manager.profiles_file.exists()
        
        data = profile_manager._load_profiles_data()
        assert "profiles" in data
        assert "created_at" in data
        assert "version" in data

    def test_set_and_get_user_profile(self, profile_manager):
        """プロファイル設定と取得のテスト"""
        user_id = "test_user"
        name = "テスト太郎"
        occupation = "エンジニア"
        personality = "聞き役"
        characteristics = ["技術に詳しい", "メンタルヘルス重視"]
        additional_info = "プライバシー重視のMisskeyサーバー管理"

        # プロファイル設定
        success = profile_manager.set_user_profile(
            user_id=user_id,
            name=name,
            occupation=occupation,
            personality=personality,
            characteristics=characteristics,
            additional_info=additional_info
        )
        assert success

        # プロファイル取得
        profile = profile_manager.get_user_profile(user_id)
        assert profile is not None
        assert profile["name"] == name
        assert profile["occupation"] == occupation
        assert profile["personality"] == personality
        assert profile["characteristics"] == characteristics
        assert profile["additional_info"] == additional_info

    def test_partial_profile_update(self, profile_manager):
        """部分的なプロファイル更新のテスト"""
        user_id = "test_user"
        
        # 初回設定
        profile_manager.set_user_profile(user_id=user_id, name="初期名前")
        
        # 部分更新
        profile_manager.set_user_profile(user_id=user_id, occupation="新しい職業")
        
        # 確認
        profile = profile_manager.get_user_profile(user_id)
        assert profile["name"] == "初期名前"  # 既存値は保持
        assert profile["occupation"] == "新しい職業"  # 新しい値は更新

    def test_delete_user_profile(self, profile_manager):
        """プロファイル削除のテスト"""
        user_id = "test_user"
        
        # プロファイル作成
        profile_manager.set_user_profile(user_id=user_id, name="テスト")
        assert profile_manager.get_user_profile(user_id) is not None
        
        # プロファイル削除
        success = profile_manager.delete_user_profile(user_id)
        assert success
        
        # 削除確認
        assert profile_manager.get_user_profile(user_id) is None
        
        # 存在しないプロファイルの削除
        success2 = profile_manager.delete_user_profile("nonexistent")
        assert not success2

    def test_generate_prompt_from_profile(self, profile_manager):
        """プロファイルベースプロンプト生成のテスト"""
        user_id = "test_user"
        
        # プロファイルなしの場合
        prompt1 = profile_manager.generate_prompt_from_profile(user_id)
        assert "経験豊富で共感力の高い人生相談カウンセラー" in prompt1
        
        # プロファイル設定後
        profile_manager.set_user_profile(
            user_id=user_id,
            name="ひろ",
            occupation="ひきこもり",
            personality="聞き役",
            characteristics=["技術に詳しい", "音楽好き"],
            additional_info="情報セキュリティとボカロ音楽が好き"
        )
        
        prompt2 = profile_manager.generate_prompt_from_profile(user_id)
        assert "ひろ" in prompt2
        assert "ひきこもり" in prompt2
        assert "聞き役" in prompt2
        assert "傾聴を重視し" in prompt2
        assert "技術に詳しい、音楽好き" in prompt2
        assert "情報セキュリティとボカロ音楽が好き" in prompt2

    def test_personality_based_prompt_adjustment(self, profile_manager):
        """性格に応じたプロンプト調整のテスト"""
        user_id = "test_user"
        
        # 聞き役性格
        profile_manager.set_user_profile(user_id=user_id, personality="聞き役")
        prompt1 = profile_manager.generate_prompt_from_profile(user_id)
        assert "傾聴を重視し" in prompt1
        
        # 励まし性格
        profile_manager.set_user_profile(user_id=user_id, personality="励まし")
        prompt2 = profile_manager.generate_prompt_from_profile(user_id)
        assert "前向きな励まし" in prompt2
        
        # 率直性格
        profile_manager.set_user_profile(user_id=user_id, personality="率直")
        prompt3 = profile_manager.generate_prompt_from_profile(user_id)
        assert "率直で建設的な" in prompt3

    def test_profile_stats(self, profile_manager):
        """プロファイル統計のテスト"""
        # 初期状態
        stats = profile_manager.get_profile_stats()
        assert stats["total_profiles"] == 0
        assert stats["complete_profiles"] == 0
        assert stats["completion_rate"] == 0
        
        # 不完全なプロファイル
        profile_manager.set_user_profile("user1", name="名前のみ")
        stats = profile_manager.get_profile_stats()
        assert stats["total_profiles"] == 1
        assert stats["complete_profiles"] == 0
        assert stats["completion_rate"] == 0
        
        # 完全なプロファイル
        profile_manager.set_user_profile("user2", name="完全", occupation="職業", personality="性格")
        stats = profile_manager.get_profile_stats()
        assert stats["total_profiles"] == 2
        assert stats["complete_profiles"] == 1
        assert stats["completion_rate"] == 50.0

    def test_list_all_profiles(self, profile_manager):
        """プロファイル一覧取得のテスト"""
        # 初期状態
        profiles = profile_manager.list_all_profiles()
        assert len(profiles) == 0
        
        # プロファイル追加
        profile_manager.set_user_profile("user1", name="ユーザー1")
        profile_manager.set_user_profile("user2", name="ユーザー2")
        
        profiles = profile_manager.list_all_profiles()
        assert len(profiles) == 2
        assert any(p["name"] == "ユーザー1" for p in profiles)
        assert any(p["name"] == "ユーザー2" for p in profiles)

    def test_personality_and_characteristic_options(self):
        """性格と特徴の選択肢テスト"""
        assert isinstance(PERSONALITY_OPTIONS, list)
        assert len(PERSONALITY_OPTIONS) > 0
        assert "聞き役" in PERSONALITY_OPTIONS
        assert "励まし" in PERSONALITY_OPTIONS
        
        assert isinstance(CHARACTERISTIC_OPTIONS, list)
        assert len(CHARACTERISTIC_OPTIONS) > 0
        assert "技術に詳しい" in CHARACTERISTIC_OPTIONS
        assert "メンタルヘルス重視" in CHARACTERISTIC_OPTIONS


class TestProfileIntegration:
    """プロファイル機能統合テスト"""

    def test_chatgpt_style_profile_example(self):
        """ChatGPT形式プロファイル例のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = UserProfileManager(temp_dir)
            
            # ChatGPT風の設定例
            manager.set_user_profile(
                user_id="hiro",
                name="ひろ",
                occupation="ひきこもり",
                personality="聞き役",
                characteristics=["メンタルヘルス重視", "技術に詳しい", "音楽好き", "プライバシー保護"],
                additional_info="""大学受験に失敗して不本意入学した大学を不登校になってからひきこもり、
情報セキュリティとボカロ音楽とオルタナティブロックが好き、
プライバシー保護とメンタルヘルスがコンセプトのMisskeyサーバーの開発と管理をしている、
ギターを弾きたいけど弾けない、仮想通貨やVRなどに興味"""
            )
            
            prompt = manager.generate_prompt_from_profile("hiro")
            
            # 期待する内容が含まれているか確認
            assert "ひろ" in prompt
            assert "ひきこもり" in prompt
            assert "聞き役" in prompt
            assert "傾聴を重視し" in prompt
            assert "メンタルヘルス重視" in prompt
            assert "技術に詳しい" in prompt
            assert "音楽好き" in prompt
            assert "プライバシー保護" in prompt
            assert "情報セキュリティ" in prompt
            assert "ボカロ音楽" in prompt


if __name__ == "__main__":
    pytest.main([__file__])
"""
カスタムプロンプト機能のテスト
"""

import pytest
import json
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

from navi.custom_prompt import CustomPromptManager, DEFAULT_PROMPT_TEMPLATES
from navi.counseling_service import CounselingService, CounselingRequest

class TestCustomPromptManager:
    """カスタムプロンプト管理のテスト"""
    
    def setup_method(self):
        """テスト前の準備"""
        self.test_dir = tempfile.mkdtemp()
        self.manager = CustomPromptManager(self.test_dir)
        self.test_user_id = "test_user_123"
        
    def teardown_method(self):
        """テスト後のクリーンアップ"""
        shutil.rmtree(self.test_dir)
    
    def test_create_custom_prompt(self):
        """カスタムプロンプト作成のテスト"""
        prompt_id = self.manager.create_custom_prompt(
            user_id=self.test_user_id,
            name="テスト猫キャラ",
            prompt_text="あなたは可愛い猫のキャラクターです。語尾に「にゃん」をつけて話してください。",
            description="猫のキャラクターで相談に乗る",
            tags=["猫", "可愛い", "親しみやすい"]
        )
        
        assert prompt_id is not None
        assert len(prompt_id) > 0
        
        # 作成されたプロンプトを確認
        prompt = self.manager.get_custom_prompt(prompt_id)
        assert prompt is not None
        assert prompt["name"] == "テスト猫キャラ"
        assert prompt["user_id"] == self.test_user_id
        assert "猫" in prompt["tags"]
        assert prompt["is_active"] is True
        assert prompt["usage_count"] == 0
    
    def test_get_user_prompts(self):
        """ユーザーのプロンプト一覧取得テスト"""
        # 複数のプロンプトを作成
        prompt1_id = self.manager.create_custom_prompt(
            self.test_user_id, "プロンプト1", "テスト1", "説明1", ["タグ1"]
        )
        prompt2_id = self.manager.create_custom_prompt(
            self.test_user_id, "プロンプト2", "テスト2", "説明2", ["タグ2"]
        )
        
        # 別のユーザーのプロンプト
        self.manager.create_custom_prompt(
            "other_user", "他のプロンプト", "テスト", "説明", ["タグ"]
        )
        
        user_prompts = self.manager.get_user_prompts(self.test_user_id)
        
        assert len(user_prompts) == 2
        prompt_ids = [p["id"] for p in user_prompts]
        assert prompt1_id in prompt_ids
        assert prompt2_id in prompt_ids
    
    def test_update_custom_prompt(self):
        """カスタムプロンプト更新テスト"""
        prompt_id = self.manager.create_custom_prompt(
            self.test_user_id, "オリジナル", "オリジナルテキスト"
        )
        
        # 更新
        success = self.manager.update_custom_prompt(
            prompt_id, self.test_user_id,
            name="更新後",
            prompt_text="更新されたテキスト",
            tags=["新しいタグ"]
        )
        
        assert success is True
        
        updated_prompt = self.manager.get_custom_prompt(prompt_id)
        assert updated_prompt["name"] == "更新後"
        assert updated_prompt["prompt_text"] == "更新されたテキスト"
        assert "新しいタグ" in updated_prompt["tags"]
    
    def test_delete_custom_prompt(self):
        """カスタムプロンプト削除テスト"""
        prompt_id = self.manager.create_custom_prompt(
            self.test_user_id, "削除テスト", "削除されるプロンプト"
        )
        
        success = self.manager.delete_custom_prompt(prompt_id, self.test_user_id)
        assert success is True
        
        # 削除後は非アクティブになる
        prompt = self.manager.get_custom_prompt(prompt_id)
        assert prompt["is_active"] is False
        
        # ユーザーのプロンプト一覧からは除外される
        user_prompts = self.manager.get_user_prompts(self.test_user_id)
        prompt_ids = [p["id"] for p in user_prompts]
        assert prompt_id not in prompt_ids
    
    def test_increment_usage(self):
        """使用回数インクリメントテスト"""
        prompt_id = self.manager.create_custom_prompt(
            self.test_user_id, "使用回数テスト", "テスト"
        )
        
        # 使用回数を増加
        self.manager.increment_usage(prompt_id)
        self.manager.increment_usage(prompt_id)
        
        prompt = self.manager.get_custom_prompt(prompt_id)
        assert prompt["usage_count"] == 2
    
    def test_search_prompts(self):
        """プロンプト検索テスト"""
        self.manager.create_custom_prompt(
            self.test_user_id, "猫キャラ", "猫のキャラクター", "可愛い猫", ["猫", "キャラ"]
        )
        self.manager.create_custom_prompt(
            self.test_user_id, "犬キャラ", "犬のキャラクター", "忠実な犬", ["犬", "キャラ"]
        )
        
        # テキスト検索
        results = self.manager.search_prompts(self.test_user_id, query="猫")
        assert len(results) == 1
        assert "猫キャラ" in results[0]["name"]
        
        # タグ検索
        results = self.manager.search_prompts(self.test_user_id, tags=["キャラ"])
        assert len(results) == 2
    
    def test_access_control(self):
        """アクセス制御テスト"""
        user1 = "user1"
        user2 = "user2"
        
        prompt_id = self.manager.create_custom_prompt(
            user1, "ユーザー1のプロンプト", "テスト"
        )
        
        # ユーザー2が更新を試行
        success = self.manager.update_custom_prompt(prompt_id, user2, name="悪意ある更新")
        assert success is False
        
        # ユーザー2が削除を試行
        success = self.manager.delete_custom_prompt(prompt_id, user2)
        assert success is False
    
    def test_default_templates(self):
        """デフォルトテンプレートのテスト"""
        assert "counselor" in DEFAULT_PROMPT_TEMPLATES
        assert "big_sister" in DEFAULT_PROMPT_TEMPLATES
        assert "mentor" in DEFAULT_PROMPT_TEMPLATES
        
        counselor_template = DEFAULT_PROMPT_TEMPLATES["counselor"]
        assert "name" in counselor_template
        assert "prompt_text" in counselor_template
        assert "description" in counselor_template
        assert "tags" in counselor_template


class TestCustomPromptIntegration:
    """カスタムプロンプトと相談サービスの統合テスト"""
    
    def setup_method(self):
        """テスト前の準備"""
        self.test_dir = tempfile.mkdtemp()
        self.prompt_manager = CustomPromptManager(self.test_dir)
        
        # モックAPIキー（実際のテストでは使用されない）
        self.mock_api_key = "test_api_key"
        
    def teardown_method(self):
        """テスト後のクリーンアップ"""
        shutil.rmtree(self.test_dir)
    
    def test_prompt_selection(self):
        """プロンプト選択のテスト"""
        user_id = "test_user"
        
        # カスタムプロンプトを作成
        custom_prompt_id = self.prompt_manager.create_custom_prompt(
            user_id=user_id,
            name="テスト猫キャラ",
            prompt_text="あなたは優しい猫のキャラクターです。相談者を「にゃん」と呼んで、温かく接してください。"
        )
        
        # CounselingServiceを初期化
        service = CounselingService(self.mock_api_key, self.prompt_manager)
        
        # カスタムプロンプトIDを指定したリクエスト
        request = CounselingRequest(
            message="最近悩みがあります",
            user_id=user_id,
            custom_prompt_id=custom_prompt_id
        )
        
        # プロンプト取得をテスト
        prompt = service._get_prompt_for_request(request)
        assert "優しい猫のキャラクター" in prompt
        assert "にゃん" in prompt
    
    def test_default_prompt_fallback(self):
        """デフォルトプロンプトフォールバックのテスト"""
        service = CounselingService(self.mock_api_key, self.prompt_manager)
        
        # カスタムプロンプトIDを指定しないリクエスト
        request = CounselingRequest(
            message="相談があります",
            user_id="test_user"
        )
        
        prompt = service._get_prompt_for_request(request)
        assert "経験豊富で共感力の高い人生相談カウンセラー" in prompt
    
    def test_nonexistent_prompt_fallback(self):
        """存在しないプロンプトIDのフォールバック"""
        service = CounselingService(self.mock_api_key, self.prompt_manager)
        
        request = CounselingRequest(
            message="相談があります",
            user_id="test_user",
            custom_prompt_id="nonexistent_prompt_id"
        )
        
        prompt = service._get_prompt_for_request(request)
        assert "経験豊富で共感力の高い人生相談カウンセラー" in prompt


if __name__ == "__main__":
    # 簡単な実行テスト
    print("カスタムプロンプト機能のテストを実行中...")
    
    # テンポラリディレクトリでテスト実行
    test_dir = tempfile.mkdtemp()
    try:
        manager = CustomPromptManager(test_dir)
        
        # プロンプト作成テスト
        print("✓ プロンプト作成テスト")
        prompt_id = manager.create_custom_prompt(
            "test_user", "テスト", "テストプロンプト", "説明", ["テスト"]
        )
        
        # 取得テスト
        print("✓ プロンプト取得テスト")
        prompt = manager.get_custom_prompt(prompt_id)
        assert prompt is not None
        
        # 一覧取得テスト
        print("✓ プロンプト一覧テスト")
        prompts = manager.get_user_prompts("test_user")
        assert len(prompts) == 1
        
        print("🎉 カスタムプロンプト機能のテストが完了しました!")
        
    finally:
        shutil.rmtree(test_dir)
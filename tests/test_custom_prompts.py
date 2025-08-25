"""
カスタムプロンプト機能のテスト（暗号化データベース版）
"""

import pytest
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

from navi.user_settings import UserSettingsManager, DEFAULT_PROMPT_TEMPLATES
from navi.counseling_service import CounselingService, CounselingRequest

class TestCustomPromptManager:
    """カスタムプロンプト管理のテスト（暗号化データベース版）"""
    
    def setup_method(self):
        """テスト前の準備"""
        self.test_dir = tempfile.mkdtemp()
        self.test_db = str(Path(self.test_dir) / "test.db")
        self.test_key = str(Path(self.test_dir) / "test.key")
        self.manager = UserSettingsManager(self.test_db, self.test_key)
        self.test_user_id = "test_user_123"
        
    def teardown_method(self):
        """テスト後のクリーンアップ"""
        shutil.rmtree(self.test_dir)
    
    def test_save_custom_prompt(self):
        """カスタムプロンプト保存のテスト"""
        success = self.manager.save_custom_prompt(
            user_id=self.test_user_id,
            name="テスト猫キャラ",
            prompt_text="あなたは可愛い猫のキャラクターです。語尾に「にゃん」をつけて話してください。",
            description="猫のキャラクターで相談に乗る",
            tags=["猫", "可愛い", "親しみやすい"]
        )
        
        assert success is True
        
        # 保存されたプロンプトを確認
        prompt = self.manager.get_custom_prompt(self.test_user_id, "テスト猫キャラ")
        assert prompt is not None
        assert "猫のキャラクター" in prompt["prompt_text"]
        assert "にゃん" in prompt["prompt_text"]
        assert prompt["description"] == "猫のキャラクターで相談に乗る"
        assert "猫" in prompt["tags"]
    
    def test_list_custom_prompts(self):
        """カスタムプロンプト一覧取得テスト"""
        # 複数のプロンプトを作成
        self.manager.save_custom_prompt(
            self.test_user_id, "プロンプト1", "テスト1", "説明1", ["タグ1"]
        )
        self.manager.save_custom_prompt(
            self.test_user_id, "プロンプト2", "テスト2", "説明2", ["タグ2"]
        )
        
        # 別のユーザーのプロンプト
        self.manager.save_custom_prompt(
            "other_user", "他のプロンプト", "テスト", "説明", ["タグ"]
        )
        
        user_prompts = self.manager.list_custom_prompts(self.test_user_id)
        
        assert len(user_prompts) == 2
        prompt_names = [p["name"] for p in user_prompts]
        assert "プロンプト1" in prompt_names
        assert "プロンプト2" in prompt_names
        assert "他のプロンプト" not in prompt_names
    
    def test_delete_custom_prompt(self):
        """カスタムプロンプト削除テスト"""
        self.manager.save_custom_prompt(
            self.test_user_id, "削除テスト", "削除されるプロンプト"
        )
        
        success = self.manager.delete_custom_prompt(self.test_user_id, "削除テスト")
        assert success is True
        
        # 削除後は取得できない
        prompt = self.manager.get_custom_prompt(self.test_user_id, "削除テスト")
        assert prompt is None
        
        # ユーザーのプロンプト一覧からも除外される
        user_prompts = self.manager.list_custom_prompts(self.test_user_id)
        prompt_names = [p["name"] for p in user_prompts]
        assert "削除テスト" not in prompt_names
    
    def test_access_control(self):
        """アクセス制御テスト"""
        user1 = "user1"
        user2 = "user2"
        
        self.manager.save_custom_prompt(
            user1, "ユーザー1のプロンプト", "テスト"
        )
        
        # ユーザー2が取得を試行
        prompt = self.manager.get_custom_prompt(user2, "ユーザー1のプロンプト")
        assert prompt is None
        
        # ユーザー2が削除を試行
        success = self.manager.delete_custom_prompt(user2, "ユーザー1のプロンプト")
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
        self.test_db = str(Path(self.test_dir) / "test.db")
        self.test_key = str(Path(self.test_dir) / "test.key")
        self.settings_manager = UserSettingsManager(self.test_db, self.test_key)
        
        # モックAPIキー（実際のテストでは使用されない）
        self.mock_api_key = "test_api_key"
        
    def teardown_method(self):
        """テスト後のクリーンアップ"""
        shutil.rmtree(self.test_dir)
    
    def test_prompt_selection(self):
        """プロンプト選択のテスト"""
        user_id = "test_user"
        
        # カスタムプロンプトを作成
        self.settings_manager.save_custom_prompt(
            user_id=user_id,
            name="テスト猫キャラ",
            prompt_text="あなたは優しい猫のキャラクターです。相談者を「にゃん」と呼んで、温かく接してください。"
        )
        
        # ユーザー設定でカスタムプロンプトを指定
        user_settings = {
            "prompt_preference": {
                "custom_prompt_name": "テスト猫キャラ"
            }
        }
        self.settings_manager.save_user_settings(user_id, user_settings)
        
        # CounselingServiceを初期化
        service = CounselingService(self.mock_api_key, None)
        
        # カスタムプロンプト名を指定したリクエスト
        request = CounselingRequest(
            message="最近悩みがあります",
            user_id=user_id,
            custom_prompt_id="テスト猫キャラ"
        )
        
        # プロンプト取得をテスト
        prompt = service._get_prompt_for_request(request)
        assert "優しい猫のキャラクター" in prompt
        assert "にゃん" in prompt
    
    def test_default_prompt_fallback(self):
        """デフォルトプロンプトフォールバックのテスト"""
        service = CounselingService(self.mock_api_key, None)
        
        # カスタムプロンプトIDを指定しないリクエスト
        request = CounselingRequest(
            message="相談があります",
            user_id="test_user"
        )
        
        prompt = service._get_prompt_for_request(request)
        assert "経験豊富で共感力の高い人生相談カウンセラー" in prompt
    
    def test_nonexistent_prompt_fallback(self):
        """存在しないプロンプトIDのフォールバック"""
        service = CounselingService(self.mock_api_key, None)
        
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
        test_db = str(Path(test_dir) / "test.db")
        test_key = str(Path(test_dir) / "test.key")
        manager = UserSettingsManager(test_db, test_key)
        
        # プロンプト作成テスト
        print("✓ プロンプト作成テスト")
        success = manager.save_custom_prompt(
            "test_user", "テスト", "テストプロンプト", "説明", ["テスト"]
        )
        assert success is True
        
        # 取得テスト
        print("✓ プロンプト取得テスト")
        prompt = manager.get_custom_prompt("test_user", "テスト")
        assert prompt is not None
        
        # 一覧取得テスト
        print("✓ プロンプト一覧テスト")
        prompts = manager.list_custom_prompts("test_user")
        assert len(prompts) == 1
        
        print("🎉 カスタムプロンプト機能のテストが完了しました!")
        
    finally:
        shutil.rmtree(test_dir)
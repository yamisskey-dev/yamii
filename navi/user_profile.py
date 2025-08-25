"""
ユーザープロファイル管理システム
ChatGPT形式のカスタムプロンプト生成に対応
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid
from pathlib import Path


class UserProfile:
    """ユーザープロファイルクラス"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.name: Optional[str] = None
        self.occupation: Optional[str] = None
        self.personality: Optional[str] = None
        self.characteristics: List[str] = []
        self.additional_info: Optional[str] = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()


class UserProfileManager:
    """ユーザープロファイル管理クラス"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.profiles_file = self.data_dir / "user_profiles.json"
        self.data_dir.mkdir(exist_ok=True)
        
        # プロファイルファイルを初期化
        self._ensure_profiles_file()
    
    def _ensure_profiles_file(self):
        """プロファイルファイルの存在を確認し、なければ作成"""
        if not self.profiles_file.exists():
            default_data = {
                "profiles": {},
                "created_at": datetime.now().isoformat(),
                "version": "1.0"
            }
            self._save_profiles_data(default_data)
    
    def _load_profiles_data(self) -> Dict[str, Any]:
        """プロファイルデータを読み込み"""
        try:
            with open(self.profiles_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"profiles": {}, "created_at": datetime.now().isoformat(), "version": "1.0"}
    
    def _save_profiles_data(self, data: Dict[str, Any]):
        """プロファイルデータを保存"""
        with open(self.profiles_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def set_user_profile(self, user_id: str, name: Optional[str] = None, 
                        occupation: Optional[str] = None, personality: Optional[str] = None,
                        characteristics: List[str] = None, additional_info: Optional[str] = None) -> bool:
        """ユーザープロファイルを設定"""
        data = self._load_profiles_data()
        
        if user_id not in data["profiles"]:
            data["profiles"][user_id] = {
                "user_id": user_id,
                "name": None,
                "occupation": None,
                "personality": None,
                "characteristics": [],
                "additional_info": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        
        profile = data["profiles"][user_id]
        
        # プロファイル情報を更新
        if name is not None:
            profile["name"] = name
        if occupation is not None:
            profile["occupation"] = occupation
        if personality is not None:
            profile["personality"] = personality
        if characteristics is not None:
            profile["characteristics"] = characteristics
        if additional_info is not None:
            profile["additional_info"] = additional_info
        
        profile["updated_at"] = datetime.now().isoformat()
        
        self._save_profiles_data(data)
        return True
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """ユーザープロファイルを取得"""
        data = self._load_profiles_data()
        return data["profiles"].get(user_id)
    
    def delete_user_profile(self, user_id: str) -> bool:
        """ユーザープロファイルを削除"""
        data = self._load_profiles_data()
        
        if user_id in data["profiles"]:
            del data["profiles"][user_id]
            self._save_profiles_data(data)
            return True
        
        return False
    
    def generate_prompt_from_profile(self, user_id: str, base_context: str = "人生相談") -> str:
        """プロファイルから動的プロンプトを生成"""
        profile = self.get_user_profile(user_id)
        
        if not profile:
            # デフォルトプロンプト
            return self._get_default_counseling_prompt()
        
        # ChatGPT形式のプロファイルベースプロンプト生成
        prompt_parts = []
        
        # 基本設定
        prompt_parts.append("あなたは経験豊富で共感力の高い人生相談カウンセラーです。")
        
        # ユーザー情報を考慮した対応方針
        if profile.get("name"):
            prompt_parts.append(f"相談者の名前は「{profile['name']}」です。")
        
        if profile.get("occupation"):
            prompt_parts.append(f"相談者の職業・状況: {profile['occupation']}")
        
        if profile.get("personality"):
            prompt_parts.append(f"相談者が求める性格・対応スタイル: {profile['personality']}")
            
            # 性格に応じた対応調整
            personality = profile['personality'].lower()
            if "聞き役" in personality:
                prompt_parts.append("特に傾聴を重視し、相談者の話をじっくりと聞く姿勢を大切にしてください。")
            elif "励まし" in personality:
                prompt_parts.append("前向きな励ましとサポートを中心としたアプローチを取ってください。")
            elif "率直" in personality:
                prompt_parts.append("率直で建設的なアドバイスを提供し、必要に応じて厳しい現実も伝えてください。")
        
        if profile.get("characteristics"):
            char_str = "、".join(profile['characteristics'])
            prompt_parts.append(f"相談者の特徴・要望: {char_str}")
        
        if profile.get("additional_info"):
            prompt_parts.append(f"追加情報: {profile['additional_info']}")
        
        # 共通の対応方針
        prompt_parts.extend([
            "",
            "対応方針:",
            "1. 相談者の個人的背景と特徴を理解し、それに適した対応を行う",
            "2. 相談者の感情に共感し、受容的な態度を維持する", 
            "3. 相談者の価値観や生活スタイルを尊重する",
            "4. 具体的で実践的なアドバイスを、相談者の状況に合わせて提供する",
            "5. 必要に応じて専門機関への相談を提案する",
            "",
            "相談者が安心して話せる雰囲気を作り、その人らしい解決策を一緒に見つけることを心がけてください。"
        ])
        
        return "\n".join(prompt_parts)
    
    def _get_default_counseling_prompt(self) -> str:
        """デフォルトの人生相談プロンプト"""
        return """あなたは経験豊富で共感力の高い人生相談カウンセラーです。
相談者の気持ちに寄り添い、実践的で心に響くアドバイスを提供してください。

対応方針:
1. まず相談者の感情を理解し、共感を示す
2. 問題の本質を見極める
3. 具体的で実行可能な解決策を提案する
4. 相談者を励まし、前向きな気持ちになれるよう支援する
5. 必要に応じて専門機関への相談も提案する

絵文字は控えめに使用し、温かみのある文章を心がけてください。
深刻な問題（自殺願望など）の場合は、専門機関への相談を強く推奨してください。"""
    
    def list_all_profiles(self) -> List[Dict[str, Any]]:
        """すべてのプロファイル一覧を取得（管理者用）"""
        data = self._load_profiles_data()
        return list(data["profiles"].values())
    
    def get_profile_stats(self) -> Dict[str, Any]:
        """プロファイル統計情報を取得"""
        data = self._load_profiles_data()
        profiles = data["profiles"]
        
        total_profiles = len(profiles)
        complete_profiles = sum(1 for p in profiles.values() 
                              if p.get("name") and p.get("occupation") and p.get("personality"))
        
        return {
            "total_profiles": total_profiles,
            "complete_profiles": complete_profiles,
            "completion_rate": (complete_profiles / total_profiles * 100) if total_profiles > 0 else 0
        }


# プロファイル設定用の便利な定数
PERSONALITY_OPTIONS = [
    "聞き役",
    "励まし",  
    "率直",
    "機知に富む",
    "Z世代",
    "伝統的",
    "前向きな考え方"
]

CHARACTERISTIC_OPTIONS = [
    "おしゃべり",
    "機知に富む", 
    "率直",
    "励まし",
    "Z世代",
    "伝統的",
    "前向きな考え方",
    "メンタルヘルス重視",
    "プライバシー保護",
    "技術に詳しい",
    "音楽好き",
    "創作活動"
]
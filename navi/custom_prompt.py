"""
カスタムプロンプト管理システム
ユーザーが独自のキャラクター・命令を設定できる機能
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid
from pathlib import Path


class CustomPromptManager:
    """カスタムプロンプト管理クラス"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.prompts_file = self.data_dir / "custom_prompts.json"
        self.data_dir.mkdir(exist_ok=True)
        
        # デフォルトプロンプトを初期化
        self._ensure_prompts_file()
    
    def _ensure_prompts_file(self):
        """プロンプトファイルの存在を確認し、なければ作成"""
        if not self.prompts_file.exists():
            default_data = {
                "prompts": {},
                "created_at": datetime.now().isoformat(),
                "version": "1.0"
            }
            self._save_prompts_data(default_data)
    
    def _load_prompts_data(self) -> Dict[str, Any]:
        """プロンプトデータを読み込み"""
        try:
            with open(self.prompts_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"prompts": {}, "created_at": datetime.now().isoformat(), "version": "1.0"}
    
    def _save_prompts_data(self, data: Dict[str, Any]):
        """プロンプトデータを保存"""
        with open(self.prompts_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def create_custom_prompt(self, user_id: str, name: str, prompt_text: str, 
                           description: str = "", tags: List[str] = None) -> str:
        """カスタムプロンプトを作成"""
        data = self._load_prompts_data()
        
        prompt_id = str(uuid.uuid4())
        
        custom_prompt = {
            "id": prompt_id,
            "name": name,
            "prompt_text": prompt_text,
            "description": description,
            "tags": tags or [],
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "usage_count": 0,
            "is_active": True
        }
        
        data["prompts"][prompt_id] = custom_prompt
        self._save_prompts_data(data)
        
        return prompt_id
    
    def get_custom_prompt(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """カスタムプロンプトを取得"""
        data = self._load_prompts_data()
        return data["prompts"].get(prompt_id)
    
    def get_user_prompts(self, user_id: str) -> List[Dict[str, Any]]:
        """ユーザーのカスタムプロンプト一覧を取得"""
        data = self._load_prompts_data()
        user_prompts = []
        
        for prompt_data in data["prompts"].values():
            if prompt_data["user_id"] == user_id and prompt_data["is_active"]:
                user_prompts.append(prompt_data)
        
        # 更新日時でソート
        user_prompts.sort(key=lambda x: x["updated_at"], reverse=True)
        return user_prompts
    
    def update_custom_prompt(self, prompt_id: str, user_id: str, 
                           name: str = None, prompt_text: str = None,
                           description: str = None, tags: List[str] = None) -> bool:
        """カスタムプロンプトを更新"""
        data = self._load_prompts_data()
        
        if prompt_id not in data["prompts"]:
            return False
        
        prompt_data = data["prompts"][prompt_id]
        
        # 所有者確認
        if prompt_data["user_id"] != user_id:
            return False
        
        # 更新
        if name is not None:
            prompt_data["name"] = name
        if prompt_text is not None:
            prompt_data["prompt_text"] = prompt_text
        if description is not None:
            prompt_data["description"] = description
        if tags is not None:
            prompt_data["tags"] = tags
        
        prompt_data["updated_at"] = datetime.now().isoformat()
        
        self._save_prompts_data(data)
        return True
    
    def delete_custom_prompt(self, prompt_id: str, user_id: str) -> bool:
        """カスタムプロンプトを削除（論理削除）"""
        data = self._load_prompts_data()
        
        if prompt_id not in data["prompts"]:
            return False
        
        prompt_data = data["prompts"][prompt_id]
        
        # 所有者確認
        if prompt_data["user_id"] != user_id:
            return False
        
        # 論理削除
        prompt_data["is_active"] = False
        prompt_data["updated_at"] = datetime.now().isoformat()
        
        self._save_prompts_data(data)
        return True
    
    def increment_usage(self, prompt_id: str):
        """使用回数をインクリメント"""
        data = self._load_prompts_data()
        
        if prompt_id in data["prompts"]:
            data["prompts"][prompt_id]["usage_count"] += 1
            self._save_prompts_data(data)
    
    def search_prompts(self, user_id: str, query: str = "", tags: List[str] = None) -> List[Dict[str, Any]]:
        """プロンプトを検索"""
        user_prompts = self.get_user_prompts(user_id)
        results = []
        
        for prompt in user_prompts:
            # テキスト検索
            if query:
                if (query.lower() in prompt["name"].lower() or
                    query.lower() in prompt["description"].lower() or
                    query.lower() in prompt["prompt_text"].lower()):
                    results.append(prompt)
                continue
            
            # タグ検索
            if tags:
                prompt_tags = set(prompt["tags"])
                search_tags = set(tags)
                if prompt_tags.intersection(search_tags):
                    results.append(prompt)
                continue
            
            # クエリもタグも指定されていない場合は全て返す
            results.append(prompt)
        
        return results


# デフォルトプロンプトテンプレート
DEFAULT_PROMPT_TEMPLATES = {
    "counselor": {
        "name": "カウンセラー",
        "prompt_text": """あなたは経験豊富で共感力の高い人生相談カウンセラーです。
相談者の気持ちに寄り添い、実践的で心に響くアドバイスを提供してください。

対応方針:
1. まず相談者の感情を理解し、共感を示す
2. 問題の本質を見極める
3. 具体的で実行可能な解決策を提案する
4. 相談者を励まし、前向きな気持ちになれるよう支援する
5. 必要に応じて専門機関への相談も提案する

絵文字は控えめに使用し、温かみのある文章を心がけてください。""",
        "description": "標準的なカウンセラー役のプロンプトです。",
        "tags": ["カウンセラー", "人生相談", "標準"]
    },
    "big_sister": {
        "name": "お姉さん",
        "prompt_text": """あなたは優しくて頼りになるお姉さんです。
相談者を弟や妹のように思って、親しみやすく、でもしっかりとしたアドバイスをしてください。

特徴:
- 親しみやすい口調で話す
- 時には厳しいことも愛情を持って伝える
- 実体験を交えたアドバイスをする
- 相談者の成長を心から願っている
- 必要な時は背中を押してあげる

「〜だよ」「〜だね」などの親しみやすい語尾を使い、温かい雰囲気を作ってください。""",
        "description": "親しみやすいお姉さんキャラクターです。",
        "tags": ["お姉さん", "親しみやすい", "家族的"]
    },
    "mentor": {
        "name": "メンター",
        "prompt_text": """あなたは豊富な人生経験を持つメンターです。
相談者の成長と成功を支援することが使命です。

アプローチ:
- 質問を通して相談者に自分で答えを見つけさせる
- 長期的な視点でアドバイスする
- 具体的な行動計画を一緒に立てる
- 相談者の強みと可能性を引き出す
- 失敗を学習の機会として捉える

相談者が自分自身の力で問題を解決できるよう導いてください。""",
        "description": "成長を促すメンター役のプロンプトです。",
        "tags": ["メンター", "成長支援", "コーチング"]
    }
}
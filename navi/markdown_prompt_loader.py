"""
NAVI.mdファイルからプロンプトを読み込むMarkdownパーサー
CLAUDE.mdやGEMINI.mdのような外部プロンプト管理システム
"""

import os
import re
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MarkdownPromptLoader:
    """NAVI.mdファイルからプロンプトを読み込むクラス"""
    
    def __init__(self, navi_md_path: str = "NAVI.md"):
        self.navi_md_path = Path(navi_md_path)
        self.prompts: Dict[str, Dict[str, Any]] = {}
        self.default_prompt_id = "default_counselor"
        self._load_prompts()
    
    def _load_prompts(self):
        """NAVI.mdファイルを読み込んでプロンプトを解析"""
        try:
            if not self.navi_md_path.exists():
                logger.warning(f"NAVI.md file not found at {self.navi_md_path}")
                self._create_fallback_prompts()
                return
            
            with open(self.navi_md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self._parse_markdown_content(content)
            logger.info(f"Loaded {len(self.prompts)} prompts from NAVI.md")
            
        except Exception as e:
            logger.error(f"Failed to load NAVI.md: {e}")
            self._create_fallback_prompts()
    
    def _parse_markdown_content(self, content: str):
        """Markdownコンテンツを解析してプロンプトを抽出"""
        # H3見出しでセクションを分割
        sections = re.split(r'\n### ', content)
        
        for section in sections[1:]:  # 最初の要素はファイルヘッダーなのでスキップ
            try:
                prompt_data = self._parse_prompt_section(section)
                if prompt_data and 'id' in prompt_data:
                    self.prompts[prompt_data['id']] = prompt_data
            except Exception as e:
                logger.warning(f"Failed to parse prompt section: {e}")
                continue
    
    def _parse_prompt_section(self, section: str) -> Optional[Dict[str, Any]]:
        """個別のプロンプトセクションを解析"""
        lines = section.strip().split('\n')
        if not lines:
            return None
        
        # タイトル（最初の行）
        title = lines[0].strip()
        
        # メタデータ解析
        prompt_data = {
            'title': title,
            'id': None,
            'name': title,
            'description': '',
            'prompt_text': '',
            'tags': [],
        }
        
        content_start = 0
        for i, line in enumerate(lines[1:], 1):
            line = line.strip()
            
            # ID解析
            id_match = re.match(r'\*\*ID\*\*:\s*`([^`]+)`', line)
            if id_match:
                prompt_data['id'] = id_match.group(1)
                continue
            
            # 名前解析
            name_match = re.match(r'\*\*名前\*\*:\s*(.+)', line)
            if name_match:
                prompt_data['name'] = name_match.group(1).strip()
                continue
            
            # 説明解析
            desc_match = re.match(r'\*\*説明\*\*:\s*(.+)', line)
            if desc_match:
                prompt_data['description'] = desc_match.group(1).strip()
                continue
            
            # 区切り線または空行でメタデータ終了
            if line == '---' or (line == '' and i > 2):
                content_start = i + 1
                break
        
        # プロンプト本文を抽出
        if content_start < len(lines):
            prompt_text_lines = lines[content_start:]
            # 次のセクション（---）までを取得
            content_lines = []
            for line in prompt_text_lines:
                if line.strip() == '---':
                    break
                content_lines.append(line)
            
            prompt_data['prompt_text'] = '\n'.join(content_lines).strip()
        
        # IDが設定されている場合のみ有効なプロンプトとして返す
        if prompt_data['id']:
            return prompt_data
        
        return None
    
    def _create_fallback_prompts(self):
        """NAVI.mdが見つからない場合のフォールバックプロンプト"""
        logger.info("Creating fallback prompts")
        
        self.prompts = {
            'default_counselor': {
                'id': 'default_counselor',
                'title': '人生相談カウンセラー',
                'name': '人生相談カウンセラー',
                'description': '標準的なカウンセリング対応',
                'prompt_text': '''あなたは経験豊富で共感力の高い人生相談カウンセラーです。
相談者の気持ちに寄り添い、実践的で心に響くアドバイスを提供してください。

対応方針:
1. まず相談者の感情を理解し、共感を示す
2. 問題の本質を見極める
3. 具体的で実行可能な解決策を提案する
4. 相談者を励まし、前向きな気持ちになれるよう支援する
5. 必要に応じて専門機関への相談も提案する

絵文字は控えめに使用し、温かみのある文章を心がけてください。
深刻な問題（自殺願望など）の場合は、専門機関への相談を強く推奨してください。''',
                'tags': ['カウンセラー', '標準', '人生相談']
            }
        }
    
    def get_prompt(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """指定されたIDのプロンプトを取得"""
        return self.prompts.get(prompt_id)
    
    def get_prompt_text(self, prompt_id: str) -> str:
        """指定されたIDのプロンプトテキストを取得（フォールバック付き）"""
        prompt = self.get_prompt(prompt_id)
        if prompt:
            return prompt['prompt_text']
        
        # フォールバック
        if prompt_id != self.default_prompt_id:
            logger.warning(f"Prompt '{prompt_id}' not found, falling back to default")
            return self.get_prompt_text(self.default_prompt_id)
        
        # デフォルトも見つからない場合の最終フォールバック
        return """あなたは人生相談に対応するAIアシスタントです。
相談者の気持ちに寄り添い、建設的なアドバイスを提供してください。"""
    
    def list_prompts(self) -> List[Dict[str, Any]]:
        """利用可能なプロンプト一覧を取得"""
        return list(self.prompts.values())
    
    def get_prompt_info(self, prompt_id: str) -> Dict[str, Any]:
        """プロンプトの情報を取得（テキスト以外）"""
        prompt = self.get_prompt(prompt_id)
        if not prompt:
            return {
                'id': prompt_id,
                'name': 'Unknown',
                'description': 'Prompt not found',
                'found': False
            }
        
        return {
            'id': prompt['id'],
            'title': prompt['title'],
            'name': prompt['name'],
            'description': prompt['description'],
            'tags': prompt.get('tags', []),
            'found': True
        }
    
    def reload(self):
        """プロンプトをリロード"""
        self.prompts.clear()
        self._load_prompts()
        logger.info("Prompts reloaded from NAVI.md")
    
    def search_prompts(self, query: str) -> List[Dict[str, Any]]:
        """プロンプトを検索"""
        results = []
        query_lower = query.lower()
        
        for prompt in self.prompts.values():
            if (query_lower in prompt['name'].lower() or 
                query_lower in prompt['description'].lower() or
                query_lower in prompt['title'].lower()):
                results.append(prompt)
        
        return results
    
    def validate_prompt_id(self, prompt_id: str) -> bool:
        """プロンプトIDが有効かチェック"""
        return prompt_id in self.prompts
    
    def get_available_prompt_ids(self) -> List[str]:
        """利用可能なプロンプトIDの一覧"""
        return list(self.prompts.keys())


# グローバルインスタンス（シングルトンパターン）
_global_prompt_loader: Optional[MarkdownPromptLoader] = None


def get_prompt_loader() -> MarkdownPromptLoader:
    """グローバルプロンプトローダーのインスタンスを取得"""
    global _global_prompt_loader
    
    if _global_prompt_loader is None:
        _global_prompt_loader = MarkdownPromptLoader()
    
    return _global_prompt_loader


def reload_prompts():
    """プロンプトをリロード"""
    global _global_prompt_loader
    if _global_prompt_loader:
        _global_prompt_loader.reload()
    else:
        _global_prompt_loader = MarkdownPromptLoader()


# 便利関数
def get_prompt_text(prompt_id: str) -> str:
    """プロンプトテキストを取得"""
    return get_prompt_loader().get_prompt_text(prompt_id)


def list_available_prompts() -> List[Dict[str, Any]]:
    """利用可能なプロンプト一覧を取得"""
    return get_prompt_loader().list_prompts()


def validate_prompt_id(prompt_id: str) -> bool:
    """プロンプトIDが有効かチェック"""
    return get_prompt_loader().validate_prompt_id(prompt_id)
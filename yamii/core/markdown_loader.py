#!/usr/bin/env python3
"""
YAMII.mdからプロンプトを読み込む軽量なマークダウンローダー
Typerの依存関係でインストールされたmarkdown-itを活用
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
from markdown_it import MarkdownIt

logger = logging.getLogger(__name__)


class YamiiMarkdownLoader:
    """YAMII.mdから開発者向けプロンプトを読み込む軽量クラス"""
    
    def __init__(self, yamii_md_path: str = "YAMII.md"):
        self.yamii_md_path = Path(yamii_md_path)
        self.prompts: Dict[str, Dict[str, Any]] = {}
        self.md_parser = MarkdownIt()
        self._load_prompts()
    
    def _load_prompts(self):
        """YAMII.mdファイルを読み込んでプロンプトを解析"""
        try:
            if not self.yamii_md_path.exists():
                logger.warning(f"YAMII.md file not found at {self.yamii_md_path}")
                self._create_fallback_prompts()
                return
            
            with open(self.yamii_md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # markdown-itでパース
            tokens = self.md_parser.parse(content)
            self._parse_tokens(tokens)
            logger.info(f"Loaded {len(self.prompts)} prompts from YAMII.md")
            
        except Exception as e:
            logger.error(f"Failed to load YAMII.md: {e}")
            self._create_fallback_prompts()
    
    def _parse_tokens(self, tokens):
        """markdown-itのトークンを解析してプロンプトを抽出"""
        current_prompt = None
        collecting_content = False
        content_lines = []
        
        for token in tokens:
            # H3見出し（### プロンプト名）でセクション開始
            if token.type == 'heading_open' and token.tag == 'h3':
                # 前のプロンプトを保存
                if current_prompt and content_lines:
                    current_prompt['prompt_text'] = '\n'.join(content_lines).strip()
                    if current_prompt.get('id'):
                        self.prompts[current_prompt['id']] = current_prompt
                
                # 新しいプロンプト開始
                current_prompt = {
                    'title': '',
                    'id': None,
                    'name': '',
                    'description': '',
                    'prompt_text': '',
                    'tags': []
                }
                content_lines = []
                collecting_content = False
                
            elif token.type == 'inline' and current_prompt and not current_prompt['title']:
                # H3見出しのテキスト（タイトル）
                current_prompt['title'] = token.content.strip()
                current_prompt['name'] = token.content.strip()
                
            elif token.type == 'inline' and current_prompt:
                # **ID**: `prompt_id` のような形式を検出
                content = token.content
                if '**ID**:' in content and '`' in content:
                    # ID抽出
                    import re
                    id_match = re.search(r'`([^`]+)`', content)
                    if id_match:
                        current_prompt['id'] = id_match.group(1)
                
                elif '**説明**:' in content:
                    # 説明抽出
                    description = content.replace('**説明**:', '').strip()
                    current_prompt['description'] = description
                
                # プロンプト本文の収集を開始（コードブロック内または区切り線後）
                elif collecting_content or token.content.strip().startswith('あなたは'):
                    collecting_content = True
                    content_lines.append(token.content)
                    
            elif token.type == 'fence' and current_prompt:
                # コードブロック内のプロンプトテキスト
                current_prompt['prompt_text'] = token.content.strip()
                collecting_content = False
                
            elif token.type == 'inline' and collecting_content and current_prompt:
                # 通常のテキストとしてプロンプト内容を収集
                content_lines.append(token.content)
        
        # 最後のプロンプトを保存
        if current_prompt and (current_prompt.get('prompt_text') or content_lines):
            if content_lines and not current_prompt.get('prompt_text'):
                current_prompt['prompt_text'] = '\n'.join(content_lines).strip()
            if current_prompt.get('id'):
                self.prompts[current_prompt['id']] = current_prompt
    
    def _create_fallback_prompts(self):
        """YAMII.mdが見つからない場合のフォールバックプロンプト"""
        logger.info("Creating fallback CLI prompts")
        
        self.prompts = {
            'cli_expert': {
                'id': 'cli_expert',
                'title': 'CLI開発エキスパート',
                'name': 'CLI開発エキスパート',
                'description': 'Typer/CLI開発専門',
                'prompt_text': '''あなたはTyperとCLI開発のエキスパートです。
美しく使いやすいコマンドラインツールの設計と実装をサポートします。

専門分野：
- Typer CLI フレームワーク
- Rich による美しい出力
- CLI設計パターン
- ユーザーエクスペリエンス
- エラーハンドリング

開発者が効率的で保守可能なCLIツールを作成できるよう支援してください。''',
                'tags': ['CLI', 'Typer', 'Rich']
            }
        }


# シングルトンパターンのグローバルインスタンス
_global_loader: Optional[YamiiMarkdownLoader] = None


def get_yamii_loader() -> YamiiMarkdownLoader:
    """グローバルYamiiMarkdownLoaderインスタンスを取得"""
    global _global_loader
    
    if _global_loader is None:
        _global_loader = YamiiMarkdownLoader()
    
    return _global_loader
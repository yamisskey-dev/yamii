#!/usr/bin/env python3
"""
Yamii CLI - プラットフォーム非依存の人生相談AIサーバー CLI
FastAPI of CLIsであるTyperを使用した管理・操作ツール
"""

import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# 既存のサービスをインポート
from yamii.core.dependencies import DependencyContainer
from yamii.core.markdown_loader import get_yamii_loader

app = typer.Typer(
    name="yamii",
    help="Yamii - プラットフォーム非依存の人生相談AIサーバー管理CLI",
    add_completion=False,
    rich_markup_mode="rich"
)

console = Console()

# 共通の依存性注入コンテナを使用
container = DependencyContainer()

@app.command()
def server(
    host: str = typer.Option("127.0.0.1", help="サーバーのホストアドレス"),
    port: int = typer.Option(8000, help="サーバーのポート番号"),
    reload: bool = typer.Option(False, help="開発モードでの自動リロード")
):
    """
    FastAPI サーバーを起動します
    """
    console.print(Panel(
        f"[bold blue]Yamii API Server[/bold blue]\n"
        f"🚀 起動中: http://{host}:{port}\n"
        f"📚 ドキュメント: http://{host}:{port}/docs",
        title="サーバー起動"
    ))
    
    import uvicorn
    from yamii.main import app as fastapi_app
    
    uvicorn.run(
        "navi.main:app",
        host=host,
        port=port,
        reload=reload,
        access_log=True
    )

@app.command()
def prompts(
    action: str = typer.Argument(..., help="アクション: list, show, test"),
    prompt_id: Optional[str] = typer.Option(None, help="プロンプトID")
):
    """
    プロンプト管理コマンド
    """
    loader = get_yamii_loader()
    prompts = loader.prompts
    
    if action == "list":
        console.print("[bold green]利用可能なプロンプト一覧[/bold green]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan")
        table.add_column("タイトル", style="white")
        table.add_column("文字数", justify="right", style="yellow")
        
        for pid, prompt in prompts.items():
            title = prompt.get('title', 'タイトルなし')
            char_count = len(prompt.get('prompt_text', ''))
            table.add_row(pid, title, str(char_count))
        
        console.print(table)
        
    elif action == "show":
        if not prompt_id:
            console.print("[red]エラー: --prompt-id オプションが必要です[/red]")
            raise typer.Exit(1)
            
        if prompt_id in prompts:
            prompt = prompts[prompt_id]
            console.print(Panel(
                f"[bold]タイトル:[/bold] {prompt.get('title', 'N/A')}\n"
                f"[bold]名前:[/bold] {prompt.get('name', 'N/A')}\n"
                f"[bold]説明:[/bold] {prompt.get('description', 'N/A')}\n"
                f"[bold]内容:[/bold]\n{prompt.get('prompt_text', 'N/A')}",
                title=f"プロンプト: {prompt_id}",
                border_style="blue"
            ))
        else:
            console.print(f"[red]エラー: プロンプト '{prompt_id}' が見つかりません[/red]")
            raise typer.Exit(1)
            
    elif action == "test":
        console.print("[bold yellow]プロンプトテスト機能（未実装）[/bold yellow]")
        console.print("将来の実装でプロンプトの品質テストを行います")
    else:
        console.print(f"[red]エラー: 不明なアクション '{action}'[/red]")
        console.print("使用可能: list, show, test")
        raise typer.Exit(1)

@app.command()
def health():
    """
    APIサーバーのヘルスチェックを実行
    """
    import requests
    from datetime import datetime
    
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            console.print(Panel(
                f"[bold green]✅ APIサーバーは正常に動作中[/bold green]\n"
                f"📊 ステータス: {data['status']}\n"
                f"🏷️  バージョン: {data['version']}\n" 
                f"⏰ チェック時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                title="ヘルスチェック結果"
            ))
        else:
            console.print(f"[red]❌ APIサーバーエラー: {response.status_code}[/red]")
            
    except requests.exceptions.RequestException as e:
        console.print(Panel(
            f"[red]❌ APIサーバーに接続できません[/red]\n"
            f"エラー: {str(e)}\n"
            f"💡 'navi server' でサーバーを起動してください",
            title="接続エラー",
            border_style="red"
        ))

@app.command()
def version():
    """
    バージョン情報を表示
    """
    console.print(Panel(
        f"[bold blue]Yamii CLI[/bold blue] v1.0.0\n"
        f"🔧 Built with [bold]Typer[/bold] - The FastAPI of CLIs\n"
        f"🚀 Powered by [bold]FastAPI[/bold]",
        title="バージョン情報"
    ))

if __name__ == "__main__":
    app()
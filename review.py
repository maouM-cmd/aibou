"""
review.py -- 振り返り・知識整理コマンド

使い方:
    python review.py          # 今日の振り返り
    python review.py stats    # 知識ベースの統計
    python review.py all      # 全知識のサマリー
"""

import sys
import io
import os

# Windows cp932 対策: UTF-8 ストリームを作成
_utf8_out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from aibou import Aibou

# Rich Console を UTF-8 ストリームに向ける
console = Console(file=_utf8_out, force_terminal=True)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "today"

    # stats と all は API キー不要（ローカルファイルのみ）
    if mode == "stats":
        from aibou import KnowledgeBase
        kb = KnowledgeBase()
        _show_stats_from_kb(kb)
        return
    elif mode == "all":
        from aibou import KnowledgeBase
        kb = KnowledgeBase()
        _show_all_knowledge_from_kb(kb)
        return

    # today はローカルLLMを呼び出す
    model_name = os.environ.get("AIBOU_MODEL", "llama3")
    aibou = Aibou(model=model_name)

    if mode == "today":
        _review_today(aibou)
    else:
        console.print(f"[yellow]未知のモード: {mode}[/yellow]")
        console.print("[dim]使い方: python review.py [today|stats|all][/dim]")


def _review_today(aibou: Aibou):
    """今日の振り返り"""
    console.print(
        Panel(
            "[bold]>> 今日の振り返り[/bold]",
            border_style="yellow",
        )
    )

    with console.status("[cyan]振り返り中...[/cyan]"):
        review = aibou.review_today()

    console.print(
        Panel(
            Markdown(review),
            title="[bold cyan]AIBOU の振り返り[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )


def _show_stats(aibou: Aibou):
    """知識ベースの統計"""
    _show_stats_from_kb(aibou.kb)


def _show_stats_from_kb(kb):
    """知識ベースの統計（KnowledgeBase直接）"""
    stats = kb.stats

    table = Table(title="知識ベース統計")
    table.add_column("項目", style="cyan")
    table.add_column("値", style="white")

    table.add_row("総ファイル数", str(stats["total_files"]))
    table.add_row("総文字数", f"{stats['total_chars']:,}")

    for cat, count in stats["categories"].items():
        label = {"tips": "[Tip]", "patterns": "[Pattern]", "preferences": "[Pref]", "journal": "[Log]"}.get(
            cat, f"[{cat}]"
        )
        table.add_row(f"  {label} {cat}", str(count))

    console.print(table)


def _show_all_knowledge(aibou: Aibou):
    """全知識のサマリー"""
    _show_all_knowledge_from_kb(aibou.kb)


def _show_all_knowledge_from_kb(kb):
    """全知識のサマリー（KnowledgeBase直接）"""
    entries = kb.get_all()

    console.print(
        Panel(
            f"[bold]全知識一覧[/bold] ({len(entries)} ファイル)",
            border_style="cyan",
        )
    )

    for entry in entries:
        preview = "\n".join(entry["content"].split("\n")[:3])
        label = {
            "tips": "[Tip]",
            "patterns": "[Pattern]",
            "preferences": "[Pref]",
            "journal": "[Log]",
        }.get(entry["category"], f"[{entry['category']}]")

        console.print(f"\n{label} [bold]{entry['path']}[/bold]")
        console.print(f"[dim]{preview}[/dim]")


if __name__ == "__main__":
    main()

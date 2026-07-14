"""
learn.py -- 学びを記録するコマンド

使い方:
    python learn.py "Clineで Plan->Act の順番で使うと手戻りゼロになった"
    python learn.py "Next.jsのhydration errorはdynamic importで解決" --category tips
    python learn.py  (引数なしで対話モード)
"""

import sys
import io
import os

_utf8_out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from aibou import Aibou

console = Console(file=_utf8_out, force_terminal=True)


def main():
    model_name = os.environ.get("AIBOU_MODEL", "llama3")
    aibou = Aibou(model=model_name)

    # 引数がある場合はワンショットモード
    if len(sys.argv) > 1:
        content = " ".join(sys.argv[1:])

        # --category オプションの処理
        category = "journal"
        if "--category" in content:
            parts = content.split("--category")
            content = parts[0].strip()
            category = parts[1].strip().split()[0] if parts[1].strip() else "journal"

        saved_path = aibou.learn(content, category=category)
        console.print(
            Panel(
                f"[green][OK] 記録しました！[/green]\n\n"
                f"[dim]内容:[/dim] {content}\n"
                f"[dim]カテゴリ:[/dim] {category}\n"
                f"[dim]保存先:[/dim] {saved_path}",
                title="[bold cyan]AIBOU -- 学び記録[/bold cyan]",
                border_style="cyan",
            )
        )
        return

    # 対話モード
    console.print(
        Panel(
            "[bold cyan]学び記録モード[/bold cyan]\n\n"
            "[dim]今日学んだこと、発見したことを記録しよう。[/dim]\n"
            "[dim]空行で送信、'quit' で終了。[/dim]",
            border_style="cyan",
        )
    )

    while True:
        console.print("\n[bold]何を学んだ？[/bold]")
        lines = []
        while True:
            line = input()
            if line.lower() == "quit":
                console.print("[dim]また何か学んだら教えて！[/dim]")
                return
            if line == "":
                break
            lines.append(line)

        if not lines:
            continue

        content = "\n".join(lines)

        category = Prompt.ask(
            "[dim]カテゴリ[/dim]",
            choices=["journal", "tips", "patterns", "preferences"],
            default="journal",
        )

        saved_path = aibou.learn(content, category=category)
        console.print(f"[green][OK] 記録しました -> {saved_path}[/green]")

        stats = aibou.get_stats()
        console.print(
            f"[dim]知識ベース: {stats['total_files']} ファイル / "
            f"{stats['total_chars']:,} 文字[/dim]"
        )


if __name__ == "__main__":
    main()

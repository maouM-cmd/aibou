"""
ask.py -- 相棒に質問するコマンド

使い方:
    python ask.py "Clineで効率よく作業する方法は？"
    python ask.py "前にhydration errorでハマった時どうしたっけ？"
    python ask.py  (引数なしで対話モード)
"""

import sys
import io
import os

_utf8_out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from aibou import Aibou

console = Console(file=_utf8_out, force_terminal=True)


def main():
    # モデルは aibou.DEFAULT_MODEL（環境変数 AIBOU_MODEL で上書き可能）に統一
    aibou = Aibou()

    # 引数がある場合はワンショットモード
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        answer = aibou.ask(question)
        console.print(
            Panel(
                Markdown(answer),
                title="[bold cyan]AIBOU[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )
        return

    # 対話モード
    console.print(
        Panel(
            "[bold cyan]AIBOU -- 相棒AI[/bold cyan]\n\n"
            "[dim]何でも聞いて。過去の経験も踏まえて答えるよ。[/dim]\n\n"
            f"[dim]知識ベース: {aibou.get_stats()['total_files']} ファイル / "
            f"{aibou.get_stats()['total_chars']:,} 文字の知識を蓄積中[/dim]\n\n"
            "[dim yellow]コマンド: /quit (終了) | /stats (統計) | "
            "/learn (学び記録) | /review (今日の振り返り)[/dim]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    while True:
        try:
            user_input = Prompt.ask("\n[bold white]あなた[/bold white]")

            if not user_input.strip():
                continue

            if user_input.startswith("/"):
                if user_input == "/quit":
                    console.print("[dim]またね！[/dim]")
                    break
                elif user_input == "/stats":
                    stats = aibou.get_stats()
                    console.print(
                        Panel(
                            f"ファイル数: {stats['total_files']}\n"
                            f"総文字数: {stats['total_chars']:,}\n"
                            f"カテゴリ: {stats['categories']}",
                            title="知識ベース統計",
                            border_style="cyan",
                        )
                    )
                    continue
                elif user_input.startswith("/learn"):
                    content = user_input[6:].strip()
                    if not content:
                        content = Prompt.ask("[dim]何を学んだ？[/dim]")
                    if content:
                        path = aibou.learn(content)
                        console.print(f"[green][OK] 記録しました -> {path}[/green]")
                    continue
                elif user_input == "/review":
                    with console.status("[cyan]今日を振り返り中...[/cyan]"):
                        review = aibou.review_today()
                    console.print(
                        Panel(
                            Markdown(review),
                            title="今日の振り返り",
                            border_style="yellow",
                            padding=(1, 2),
                        )
                    )
                    continue
                elif user_input == "/clear":
                    aibou.reset_conversation()
                    console.print("[green][OK] 会話リセット（知識は保持）[/green]")
                    continue
                else:
                    console.print(f"[yellow]未知のコマンド: {user_input}[/yellow]")
                    continue

            with console.status("[cyan]考え中...[/cyan]", spinner="dots"):
                answer = aibou.ask(user_input)

            console.print(
                Panel(
                    Markdown(answer),
                    title="[bold cyan]AIBOU[/bold cyan]",
                    border_style="cyan",
                    padding=(1, 2),
                )
            )

        except KeyboardInterrupt:
            console.print("\n[dim]またね！[/dim]")
            break
        except Exception as e:
            console.print(f"[red]エラー: {e}[/red]")


if __name__ == "__main__":
    main()

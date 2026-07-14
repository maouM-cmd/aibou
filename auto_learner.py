"""
auto_learner.py — AIBOUの自律学習システム

定期的にWeb（RSSフィードなど）から最新のAI関連ニュースやトレンドを取得し、
AIBOUの知識ベースに自動で要約・保存する。
"""

import sys
import io
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

from aibou import Aibou

_utf8_out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 情報ソース（AI関連のRSSフィード。ZennのAIトピックなど）
RSS_FEEDS = [
    "https://zenn.dev/topics/ai/feed",
    "https://zenn.dev/topics/llm/feed",
    "https://zenn.dev/topics/prompt/feed"
]

def fetch_latest_news() -> list:
    """RSSフィードから最新記事を取得する"""
    news_items = []
    for url in RSS_FEEDS:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read()
                root = ET.fromstring(content)
                
                # RSS 2.0 フォーマットのパース
                for item in root.findall('./channel/item')[:3]:  # 各フィード最新3件
                    title = item.find('title').text if item.find('title') is not None else ""
                    desc = item.find('description').text if item.find('description') is not None else ""
                    
                    # HTMLタグなどを簡単に除去
                    desc_clean = desc.replace('<p>', '').replace('</p>', '').replace('<br>', '\n')
                    
                    if title:
                        news_items.append(f"・{title}\n  概要: {desc_clean[:200]}...")
        except Exception as e:
            print(f"[AutoLearner] RSS取得エラー ({url}): {e}", file=_utf8_out)
            
    return news_items

def run_auto_learning(aibou: Aibou):
    """取得したニュースをOllamaに要約させ、知識として保存する"""
    print("[AutoLearner] 最新のAIトレンドを取得中...", file=_utf8_out)
    
    news_list = fetch_latest_news()
    if not news_list:
        print("[AutoLearner] 最新情報は見つかりませんでした。", file=_utf8_out)
        return

    news_text = "\n\n".join(news_list)
    
    prompt = (
        "あなたはAIエンジニア育成メンターです。\n"
        "以下のWebから取得した最新のAIトレンドニュースを読み、\n"
        "ユーザー（AIエンジニア）にとって実務で役立ちそうな知識、新しいツールの使い方、"
        "プロンプトのコツなどを抽出し、Markdown形式で「最新のAI活用ノウハウ」として要約してください。\n\n"
        f"【最新ニュース】\n{news_text}\n\n"
        "出力は、AIエンジニアへのアドバイスとして活用できる形にしてください。"
    )
    
    print("[AutoLearner] ニュースを分析・学習中...", file=_utf8_out)
    try:
        # 自動学習の内部処理なので会話履歴には残さない
        summary = aibou.ask(prompt, remember=False)
        if summary and "特になし" not in summary:
            # tipsカテゴリとして保存
            saved_path = aibou.learn(f"【Web自動学習による最新トレンド】\n\n{summary}", category="tips")
            print(f"[AutoLearner] 新しい知識を習得し、保存しました: {saved_path}", file=_utf8_out)
    except Exception as e:
        print(f"[AutoLearner] 学習エラー: {e}", file=_utf8_out)

if __name__ == "__main__":
    # モデルは aibou.DEFAULT_MODEL（環境変数 AIBOU_MODEL で上書き可能）に統一
    aibou = Aibou()
    run_auto_learning(aibou)

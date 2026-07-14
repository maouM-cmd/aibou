# 🤖 AIBOU — 相棒AI

**あなたの学び・経験・好みを蓄積し、どんどん賢くなる「もう一人の自分」**

完全ローカル動作（Ollama + ChromaDB）。APIキー不要・課金なし・データは外に出ない。

## セットアップ

```bash
# 1. Ollamaとモデル（初回のみ）
ollama pull hermes3:8b

# 2. Python依存
pip install -r requirements.txt
```

モデルを変えたい時は環境変数 `AIBOU_MODEL` で上書き（例: メモリが厳しい時は
`set AIBOU_MODEL=llama3.2:1b`）。既定は `hermes3:8b`（`aibou.py`の`DEFAULT_MODEL`）。

## 3つの入口

### 1. デスクトップ常駐（メイン）

```bash
run_aibou.bat
```

- 画面右下にアイコンが常駐
- **ダブルクリック → テキストで質問**（吹き出しで回答）
- Ctrl+Shift+Space → 音声で質問
- 終了時に今日のPCアクティビティから日報を自動生成してjournalに保存
- 起動時に自動Web学習をしたい場合は `set AIBOU_AUTOLEARN=1`

### 2. CLI

```bash
python ask.py "Clineで効率よく作業する方法は？"   # ワンショット
python ask.py                                    # 対話モード
python learn.py "Plan→Actの順番で使うと手戻りゼロになる"
python review.py stats                           # 知識ベース統計
```

### 3. サーバー + Chrome拡張

```bash
python server.py   # http://localhost:8000
```

`extension/` をChromeの拡張機能（デベロッパーモード）で読み込むと、
閲覧中のページに対して過去の知識に基づく助言をくれる。

## 知識ベースの構造

```
knowledge/               ← AIBOUが書き込む場所（learnコマンド・自動日報）
├── tips/           💡 ツール活用Tips
├── patterns/       🔁 解決パターン
├── preferences/    ⚙️ あなたの好み・判断基準
└── journal/        📓 日々の学びログ

外部ソース（読み取り専用・自動で肥え続ける）:
C:\Users\admin\AIgakusyu\
├── digests/        毎日自動生成されるAIニュースdigest
├── reports/        cross-review等の横断レポート
├── docs/           設計文書・ガイド
└── journal/        AIgakusyu側の学習ログ
```

AIgakusyu側は**一切変更されない**（AIBOUは読むだけ）。digestは毎日22:00に
自動生成されるため、AIBOUの知識は何もしなくても毎日増える。

## コンセプト

- **普通のAI**: 毎回ゼロからスタート
- **AIBOU**: あなたの全経験＋毎日の自動収集情報を蓄積。使うほど賢くなる

## 対話モードのコマンド

| コマンド | 説明 |
|---|---|
| `/learn <内容>` | 学びを記録 |
| `/review` | 今日の振り返り |
| `/stats` | 知識ベース統計 |
| `/clear` | 会話リセット（知識は保持） |
| `/quit` | 終了 |

## 注意（メモリ）

デスクトップ版・サーバー・CLIを**同時に複数起動しない**こと。それぞれが
埋め込みモデルを読み込むため、メモリ不足で知識ベースが無効化される
（その場合も回答自体は動く。起動時ログに [Warning] が出たら他を閉じて再起動）。
hermes3:8bが重い環境は `set AIBOU_MODEL=llama3.2:1b` で軽量化できる。

## テスト

```bash
python -m pytest test_aibou_kb.py -q
```

## Qwen Cloudで動かす場合（ハッカソン提出用）

ふだんのローカル利用（Ollama）には影響しません。切り替えたい時だけ以下の環境変数を設定してください。

```bash
pip install openai

set AIBOU_PROVIDER=qwen
set DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
python ask.py "こんにちは"
```

詳細（Alibaba Cloudへのデプロイ手順・提出情報）は [`deploy/DEPLOYMENT.md`](deploy/DEPLOYMENT.md)・[`SUBMISSION.md`](SUBMISSION.md)・[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) を参照。

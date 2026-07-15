# Devpost提出用サマリー（Global AI Hackathon Series with Qwen Cloud）

このファイルの内容をDevpostの「Enter a Submission」フォームにそのままコピペしてください。

## Track
**Track 1: MemoryAgent**

## プロジェクト名
AIBOU（相棒）— もう一人の自分になる永続記憶エージェント

## 概要（テキスト説明）
AIBOUは、ユーザーの学び・経験・好みを蓄積し、セッションをまたいでどんどん賢くなる個人用相棒AIです。もともとOllamaでローカル運用している**日常使用中**のツールで、今回のハッカソンでQwen Cloudに対応させました。

- **永続記憶**: ChromaDB（ベクトルDB）で知識ベースを永続化し、質問のたびに関連する過去の経験を意味検索して文脈に組み込む
- **育ち続ける記憶**: `learn`コマンドでの明示的な記録、RSS自動収集、外部プロジェクト（AIgakusyu）からの知見取り込みにより、使うほど賢くなる
- **3つの入口**: CLI、デスクトップ常駐（画面監視・音声対話）、Chrome拡張（閲覧中ページへのアドバイス）
- **本番運用中のツールへの技術差し込み**: 既存のOllamaベース運用を一切壊さずに、環境変数一つでQwen Cloudへ切り替え可能なプロバイダ抽象化を実装（`AIBOU_PROVIDER=qwen`）。実サービスに新技術を安全に統合するエンジニアリング上の工夫。

## Qwen Cloud統合について
`aibou.py`の`_call_qwen_raw()`が、Qwen Cloud（DashScope OpenAI互換API、`https://dashscope-intl.aliyuncs.com/compatible-mode/v1`）を呼び出します。既存の`_call_ollama_raw()`が内部でプロバイダ分岐し、呼び出し元（CLI/デスクトップ/サーバー）は無変更で両対応します。

**スコープについて**: Qwenモードでは、知識ベース検索を踏まえた通常のQ&A応答をデモしています（Function Calling/ツール呼び出しはOllama側の実装に依存しており、今回のTrack1(MemoryAgent)の評価軸である「記憶の永続化とセッションをまたいだ賢さ」には直接影響しないため、時間的制約の中でスコープ外としました）。

## コードリポジトリ
https://github.com/maouM-cmd/aibou
（ライセンス: MIT、`LICENSE`ファイル参照）

## Alibaba Cloudデプロイの証拠
**未対応**（このプロジェクトはAlibaba Cloud上へのデプロイは行っていません。判断の経緯は以下の通りです）

- コード上はAlibaba Cloudのサービス（DashScope／Qwen Cloud、`https://dashscope-intl.aliyuncs.com/compatible-mode/v1`）を[`aibou.py`](aibou.py)の`_call_qwen_raw()`で呼び出しており、Alibaba CloudのAPI自体は利用しています
- バックエンド（`server.py`）自体のAlibaba Cloud ECS等へのホスティングは、新規クラウドアカウント作成・支払い情報登録が必要になるため、今回は見送りました
- デプロイ手順自体は[`deploy/DEPLOYMENT.md`](deploy/DEPLOYMENT.md)・[`Dockerfile`](Dockerfile)として用意済みで、実行すれば即デプロイ可能な状態です（今後対応する場合の準備は完了）

## アーキテクチャ図
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## デモ動画（3分以内）
`<撮影後にYouTube/Vimeo等の公開URLをここに記入>`

**推奨構成**:
1. (0:00-0:30) コンセプト説明：「学ぶほど賢くなる相棒AI」、日常使用中であること
2. (0:30-1:30) ローカル(Ollama)での動作デモ：知識ベース検索→回答
3. (1:30-2:30) Qwen Cloud切り替えデモ：`AIBOU_PROVIDER=qwen`で同じ質問→ローカルからQwen Cloud(DashScope)へAPI呼び出しが成功する様子を確認
4. (2:30-3:00) まとめ：ChromaDBによる永続記憶、今後の展望（Alibaba Cloudへのデプロイは`deploy/DEPLOYMENT.md`として準備済み、という位置づけで触れてもよい）

## ブログ/SNS投稿（任意・Bonus Prize対象）
`<投稿後にURLを記入>`

# アーキテクチャ

AIBOUは「ユーザーの学び・経験・好みを蓄積し、セッションをまたいでどんどん賢くなる」永続記憶エージェント（Track 1: MemoryAgent）です。

```mermaid
flowchart TB
    subgraph Client["入口（3種類）"]
        CLI["CLI\n(ask.py / learn.py / review.py)"]
        Desktop["デスクトップ常駐\n(app.py)"]
        Ext["Chrome拡張\n(extension/)"]
    end

    subgraph Backend["Aibou コアロジック (aibou.py)"]
        Ask["Aibou.ask()"]
        Loop["_run_agent_loop()\n(Function Calling, 最大5回)"]
        Provider{"provider分岐"}
        Ollama["_call_ollama_raw()\nローカルOllama\n(hermes3:8b)"]
        Qwen["_call_qwen_raw()\nQwen Cloud\n(DashScope OpenAI互換API)"]
    end

    subgraph Memory["永続記憶 (KnowledgeBase)"]
        Chroma[("ChromaDB\nPersistentClient\n(.chroma_db)")]
        MD["knowledge/\ntips・patterns・preferences・journal"]
        Ext2["外部ソース\n(AIgakusyu digests等, 読み取り専用)"]
    end

    subgraph Cloud["Alibaba Cloud (デプロイ先)"]
        ECS["ECS / Simple Application Server"]
        Docker["Docker コンテナ\n(server.py = FastAPI)"]
    end

    CLI --> Ask
    Desktop --> Ask
    Ext -->|"POST /context, /ask"| Docker
    Docker --> Ask

    Ask --> Chroma
    MD --> Chroma
    Ext2 --> Chroma
    Ask --> Loop
    Loop --> Provider
    Provider -->|"AIBOU_PROVIDER=ollama\n(既定・ローカル利用)"| Ollama
    Provider -->|"AIBOU_PROVIDER=qwen\n(ハッカソン提出用)"| Qwen
    ECS --> Docker
```

## ポイント

- **記憶の永続化**: `KnowledgeBase`(`aibou.py`)がMarkdown知識(`knowledge/`)をChromaDBでベクトル化・永続化。質問のたびに`search()`で関連する過去の知識を検索し、文脈として組み込む（`recalling critical memories within limited context windows`の要件に対応）。
- **セッションをまたいだ賢さ**: `learn.py`で明示的に記録した知見、`auto_learner.py`によるRSS自動収集、AIgakusyu外部ソースの取り込みにより、使うほど知識ベースが育つ。
- **プロバイダ切り替え設計**: 本番運用中の個人ツールを壊さずに新技術（Qwen Cloud）を差し込むため、`_call_ollama_raw()`内部で`self.provider`によって処理を分岐。呼び出し元（CLI/デスクトップ/サーバー）は一切変更不要。
- **デプロイ**: `server.py`(FastAPI)をDocker化し、Alibaba Cloud ECS上で稼働。`AIBOU_PROVIDER=qwen`環境変数でQwen Cloudモードに切り替える。

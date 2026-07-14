"""
aibou.py — 相棒AIのコアロジック (V3: ベクトル検索・Ollama版)

知識ベース（markdownファイル群）を ChromaDB でベクトル化し、
「意味（ニュアンス）」で過去の経験を検索できるようにした進化版。
"""

import os
import glob
import json
import urllib.request
from datetime import datetime
from pathlib import Path

# ベクトルデータベース
# プロジェクトのルートディレクトリ
BASE_DIR = Path(__file__).parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
DB_DIR = BASE_DIR / ".chroma_db"
PROMPTS_DIR = BASE_DIR / "prompts"

# 全入口（ask.py / app.py / server.py / auto_learner.py）で共有するデフォルトモデル。
# 環境変数 AIBOU_MODEL で上書き可能（例: メモリが厳しい時は llama3.2:1b）
DEFAULT_MODEL = os.environ.get("AIBOU_MODEL", "hermes3:8b")

# Qwen Cloud (DashScope OpenAI互換モード) 用の設定。AIBOU_PROVIDER=qwen の時のみ使用。
# https://docs.qwencloud.com/developer-guides/getting-started/first-api-call
DEFAULT_QWEN_MODEL = os.environ.get("AIBOU_QWEN_MODEL", "qwen3.7-plus")
DEFAULT_QWEN_BASE_URL = os.environ.get(
    "AIBOU_QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
)

# 会話履歴の上限メッセージ数（user+assistantで20 = 10往復。無制限に伸ばすと
# コンテキストが肥大しローカルLLMの応答品質・速度が劣化するため）
MAX_HISTORY_MESSAGES = 20

# 外部知識ソース（読み取り専用でベクトル化する。AIBOUからは一切書き込まない）。
# AIgakusyuは毎日digest/cross-reviewが自動生成されるため、接続するだけで
# 知識ベースが育ち続ける。ディレクトリが存在しなければ黙ってスキップする
EXTERNAL_SOURCES = {
    "aigakusyu": [
        Path("C:/Users/admin/AIgakusyu/digests"),
        Path("C:/Users/admin/AIgakusyu/reports"),
        Path("C:/Users/admin/AIgakusyu/docs"),
        Path("C:/Users/admin/AIgakusyu/journal"),
    ],
}


class KnowledgeBase:
    """
    ローカルの知識ベースを管理し、ChromaDBを用いてベクトル検索を提供するクラス。
    """

    def __init__(self, data_dir: str | Path = KNOWLEDGE_DIR,
                 external_sources: dict | None = None, db_dir: str | Path = DB_DIR):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        # 外部ソース（読み取り専用）。Noneならモジュール定数を使う
        self.external_sources = EXTERNAL_SOURCES if external_sources is None else external_sources

        # 重いライブラリの遅延インポート
        import chromadb

        # ChromaDBの初期化 (永続化)
        self.chroma_client = chromadb.PersistentClient(path=str(db_dir))
        self.collection = self.chroma_client.get_or_create_collection(name="aibou_knowledge")

        self._entries = []
        self._sync_db()

    def _collect_md_files(self) -> list[tuple[str, str, str]]:
        """(絶対パス, DB用id, カテゴリ) のリストを返す。
        自前knowledge/はrel_pathをidに、外部ソースは ext:<name>/<相対パス> をidにして衝突を防ぐ"""
        collected = []

        for path in glob.glob(str(self.data_dir / "**/*.md"), recursive=True):
            rel_path = os.path.relpath(path, self.data_dir)
            category = rel_path.split(os.sep)[0] if os.sep in rel_path else "general"
            collected.append((path, rel_path, category))

        for source_name, dirs in self.external_sources.items():
            for src_dir in dirs:
                src_dir = Path(src_dir)
                if not src_dir.exists():
                    continue  # 外部ソースが無くても止まらない
                for path in glob.glob(str(src_dir / "**/*.md"), recursive=True):
                    rel_path = os.path.relpath(path, src_dir)
                    doc_id = f"ext:{source_name}/{src_dir.name}/{rel_path}"
                    collected.append((path, doc_id, f"ext:{source_name}"))

        return collected

    def _sync_db(self):
        """Markdownファイル（自前knowledge/＋外部ソース）とChromaDBの同期を行う"""
        self._entries = []

        docs = []
        metadatas = []
        ids = []

        for path, doc_id, category in self._collect_md_files():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()

                entry = {
                    "path": doc_id,
                    "filename": os.path.basename(path),
                    "category": category,
                    "content": content,
                }
                self._entries.append(entry)

                # DB用のデータ構築
                docs.append(content)
                metadatas.append({"category": category, "path": doc_id})
                ids.append(doc_id)

            except Exception as e:
                print(f"[Warning] Failed to load {path}: {e}")

        # DBに一括でアップサート（更新・追加）
        if docs:
            self.collection.upsert(
                documents=docs,
                metadatas=metadatas,
                ids=ids
            )

    def get_all(self) -> list[dict]:
        return self._entries

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """
        ChromaDBを使ったベクトル（意味）検索。
        言葉のニュアンスが近ければヒットする。
        """
        if not query.strip():
            return []

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(top_k, len(self._entries))
            )
            
            # 結果を辞書形式に変換
            found_entries = []
            if results["documents"] and len(results["documents"][0]) > 0:
                for i in range(len(results["documents"][0])):
                    found_entries.append({
                        "path": results["metadatas"][0][i]["path"],
                        "category": results["metadatas"][0][i]["category"],
                        "content": results["documents"][0][i]
                    })
            return found_entries
        except Exception as e:
            print(f"[Vector Search Error] {e}")
            return []

    def add_entry(self, content: str, category: str = "journal") -> Path:
        """新しい知識を追加し、即座にベクトル化する"""
        cat_dir = self.data_dir / category
        cat_dir.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d")
        filepath = cat_dir / f"{date_str}.md"

        if filepath.exists():
            existing = filepath.read_text(encoding="utf-8")
            content = existing + "\n\n---\n\n" + content
        
        filepath.write_text(content, encoding="utf-8")

        # 内部キャッシュとベクトルDBを同期
        self._sync_db()
        return filepath

    @property
    def stats(self) -> dict:
        """知識ベースの統計情報"""
        categories = {}
        for entry in self._entries:
            cat = entry["category"]
            categories[cat] = categories.get(cat, 0) + 1
        return {
            "total_files": len(self._entries),
            "categories": categories,
            "total_chars": sum(len(e["content"]) for e in self._entries),
        }


AIBOU_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "カレントディレクトリに新しいファイルを作成し、内容を書き込む",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "作成するファイル名（例: test.py）"},
                    "content": {"type": "string", "description": "ファイルに書き込むテキストやコード"}
                },
                "required": ["filename", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delegate_task",
            "description": "専門のサブAI（エージェント）を召喚し、タスクを委譲して結果を取得する",
            "parameters": {
                "type": "object",
                "properties": {
                    "role": {"type": "string", "description": "サブAIの役割（例: 'リサーチャー', 'コーダー', 'レビュアー'）"},
                    "task": {"type": "string", "description": "委譲する具体的なタスク内容"}
                },
                "required": ["role", "task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "ブラウザを開いてWeb検索を行い、検索結果のタイトルとURLを取得する",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "検索キーワード"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_webpage",
            "description": "指定したURLのWebページにアクセスし、テキスト内容を読み取る",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "読み取るWebページのURL"}
                },
                "required": ["url"]
            }
        }
    }
]

def execute_create_file(filename: str, content: str) -> str:
    try:
        from pathlib import Path
        filepath = Path(filename).name 
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"ファイル '{filepath}' を正常に作成しました。"
    except Exception as e:
        return f"ファイル作成エラー: {e}"

import re

def execute_web_search(query: str) -> str:
    print(f"\n[Browser] 🌐 Web検索を実行しています: {query}")
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8")
        
        # 簡易的なスクレイピング (DuckDuckGo HTML版)
        results = []
        for match in re.finditer(r'<a class="result__url" href="([^"]+)".*?>(.*?)</a>', html):
            url = match.group(1)
            title = re.sub(r'<[^>]+>', '', match.group(2)).strip()
            results.append(f"- {title}\n  URL: {url}")
            if len(results) >= 5:
                break
        
        if not results:
            return "検索結果が見つかりませんでした。"
        return "検索結果:\n" + "\n".join(results)
    except Exception as e:
        return f"Web検索エラー: {e}"

def execute_read_webpage(url: str) -> str:
    print(f"\n[Browser] 📄 Webページを読み込んでいます: {url}")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8", errors="ignore")
        
        # 不要なタグを削除してテキストを抽出
        text = re.sub(r'<script.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # LLMのコンテキスト長を考慮して先頭から3000文字程度に制限
        return text[:3000] + "...\n(続きは省略されました)"
    except Exception as e:
        return f"ページ読み込みエラー: {e}"

def execute_delegate_task(role: str, task: str, ollama_url: str, model: str) -> str:
    print(f"\n[Swarm Orchestration] 👥 役割 '{role}' のサブAIを召喚し、タスクを委譲しています...")
    system_prompt = f"あなたはAIBOUのサブエージェントであり、優秀な【{role}】です。マスターからのタスクを完遂し、結果を報告してください。"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task}
    ]
    data = {
        "model": model,
        "messages": messages,
        "stream": False
    }
    req = urllib.request.Request(
        ollama_url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            answer = result.get("message", {}).get("content", "")
            print(f"[Swarm Orchestration] ✅ サブAI '{role}' のタスクが完了しました。")
            return f"【{role}】からの報告:\n{answer}"
    except Exception as e:
        return f"【{role}】の実行中にエラーが発生しました: {e}"


class Aibou:
    """相棒AI — もう一人のあなた (Ollama + ChromaDB 対応版)"""

    def __init__(self, model: str = DEFAULT_MODEL, ollama_url: str = "http://localhost:11434/api/chat",
                 use_kb: bool = True, provider: str | None = None):
        self.model = model
        self.ollama_url = ollama_url
        self.conversation_history = []
        # "ollama"（既定・ローカル、後方互換） または "qwen"（Qwen Cloud、ハッカソン提出用）
        self.provider = provider or os.environ.get("AIBOU_PROVIDER", "ollama")
        
        if use_kb:
            try:
                self.kb = KnowledgeBase()
            except Exception as e:
                print(f"[Warning] 知識ベースの初期化に失敗しました (メモリ不足の可能性): {e}")
                self.kb = None
        else:
            self.kb = None
        
        system_prompt_path = PROMPTS_DIR / "system.md"
        if system_prompt_path.exists():
            self._system_prompt = system_prompt_path.read_text(encoding="utf-8")
        else:
            self._system_prompt = (
                "あなたは最強のAIエンジニア育成メンターであり、自律型エージェントです。"
                "必要に応じてTools（ツール）を呼び出し、ユーザーの代わりにファイルの作成などの作業を行ってください。"
            )

    def _call_qwen_raw(self, messages: list, override_model: str = None) -> dict:
        """Qwen Cloud (DashScope OpenAI互換モード) を呼び出し、Ollamaと同じ形のdict({"message": {"content": ...}})に正規化して返す。

        注意: tools（Function Calling）は受け取らない。OpenAI互換APIのtool結果メッセージは
        tool_call_id必須だが、_run_agent_loopはOllama形式（nameキーのみ）で積んでおり非互換のため、
        Qwenモードではエージェントのツール呼び出し機能はスコープ外とする（知識ベース検索＋通常応答のみ）。
        """
        try:
            from openai import OpenAI  # 遅延import（Ollama専用ユーザーに依存関係を強制しない）
        except ImportError:
            return {"error": "openaiパッケージが未インストールです（pip install openai）"}

        api_key = os.environ.get("DASHSCOPE_API_KEY", "")
        if not api_key:
            return {"error": "DASHSCOPE_API_KEY が設定されていません"}

        client = OpenAI(api_key=api_key, base_url=DEFAULT_QWEN_BASE_URL)
        model_to_use = override_model or DEFAULT_QWEN_MODEL
        try:
            resp = client.chat.completions.create(model=model_to_use, messages=messages)
            return {"message": {"content": resp.choices[0].message.content or ""}}
        except Exception as e:
            return {"error": f"Qwen Cloud通信エラー: {e}"}

    def _call_ollama_raw(self, messages: list, override_model: str = None, tools: list = None) -> dict:
        """Ollama APIを呼び出し、生のレスポンス(dict)を返す（provider="qwen"の場合はQwen Cloudに委譲）"""
        if self.provider == "qwen":
            return self._call_qwen_raw(messages, override_model=override_model)

        model_to_use = override_model if override_model else self.model
        data = {
            "model": model_to_use,
            "messages": messages,
            "stream": False
        }
        if tools:
            data["tools"] = tools

        req = urllib.request.Request(
            self.ollama_url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            return {"error": f"Ollamaとの通信エラー: {e}"}

    def _call_ollama(self, messages: list, override_model: str = None) -> str:
        """互換性維持のためのメソッド"""
        res = self._call_ollama_raw(messages, override_model)
        if "error" in res:
            return res["error"]
        return res.get("message", {}).get("content", "")

    def _run_agent_loop(self, messages: list, override_model: str = None) -> str:
        """Function Callingを含むエージェント実行ループ"""
        max_iterations = 5
        for _ in range(max_iterations):
            # ツールを渡してAPI呼び出し
            res = self._call_ollama_raw(messages, override_model=override_model, tools=AIBOU_TOOLS)
            if "error" in res:
                return res["error"]
                
            message = res.get("message", {})
            messages.append(message)  # アシスタントの返答（またはツール呼び出し）を履歴に追加
            
            tool_calls = message.get("tool_calls")
            if not tool_calls:
                # ツール呼び出しがなければ、通常のテキスト回答として終了
                return message.get("content", "")
            
            # ツールが呼び出された場合、実行する
            for tool in tool_calls:
                func_name = tool.get("function", {}).get("name")
                args = tool.get("function", {}).get("arguments", {})
                
                print(f"[AIBOU Agent] ツールを実行します: {func_name}({args})")
                
                if func_name == "create_file":
                    tool_result = execute_create_file(args.get("filename", ""), args.get("content", ""))
                elif func_name == "delegate_task":
                    # Swarm オーケストレーションの実行
                    tool_result = execute_delegate_task(args.get("role", ""), args.get("task", ""), self.ollama_url, self.model)
                elif func_name == "web_search":
                    # ブラウザによるWeb検索
                    tool_result = execute_web_search(args.get("query", ""))
                elif func_name == "read_webpage":
                    # ブラウザによるページ読み込み
                    tool_result = execute_read_webpage(args.get("url", ""))
                else:
                    tool_result = f"エラー: 未知のツール '{func_name}' です。"
                
                # ツールの実行結果をメッセージリストに追加
                messages.append({
                    "role": "tool",
                    "content": tool_result,
                    "name": func_name
                })
        
        return "エージェントループの上限に達しました。"

    def ask(self, question: str, remember: bool = True) -> str:
        """相棒に質問する（エージェント対応）。

        remember=False にすると会話履歴に残さない。自動監視・ページ文脈チェック等の
        「機械が投げる質問」に使い、ユーザーとの対話の記憶を汚染しないため
        """
        relevant = self.kb.search(question, top_k=3) if self.kb else []
        context = self._build_context(relevant)

        messages = []
        messages.append({
            "role": "system",
            "content": self._system_prompt + "\n\n" + context
        })

        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": question})

        # Agentic Loop を実行
        answer = self._run_agent_loop(messages)

        if remember:
            self.conversation_history.append({"role": "user", "content": question})
            self.conversation_history.append({"role": "assistant", "content": answer})
            # 上限超過分は古いものから切り捨てる（コンテキスト肥大の防止）
            if len(self.conversation_history) > MAX_HISTORY_MESSAGES:
                self.conversation_history = self.conversation_history[-MAX_HISTORY_MESSAGES:]

        return answer

    def ask_with_vision(self, question: str, base64_image: str, vision_model: str = "llama3.2-vision") -> str:
        """画像を添付してVision対応モデルに質問する"""
        messages = [
            {
                "role": "system",
                "content": "あなたは最強のAIエンジニア育成メンターです。提供されたユーザーの作業画面（画像）を見て、メタ認知や上流の視点からコーチングを行ってください。"
            },
            {
                "role": "user",
                "content": question,
                "images": [base64_image]
            }
        ]
        
        # Vision対応モデルを強制指定して呼び出す
        return self._call_ollama(messages, override_model=vision_model)

    def learn(self, content: str, category: str = "journal") -> Path:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        formatted = f"## {timestamp} の学び\n\n{content}\n"
        return self.kb.add_entry(formatted, category=category)

    def review_today(self) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        today_entries = [e for e in self.kb.get_all() if today in e.get("filename", "")]

        if not today_entries:
            return "今日はまだ記録がないよ。何か学んだことがあったら `learn` で記録しよう！"

        contents = "\n\n".join(e["content"] for e in today_entries)

        messages = [
            {"role": "system", "content": "ユーザーの今日の学習ログを振り返り、フランクな口調で要約してください。「今日の最大の学び」「パターン化できること」「明日試したいこと」を整理してください。"},
            {"role": "user", "content": f"今日の記録:\n\n{contents}"}
        ]
        return self._call_ollama(messages)

    def _build_context(self, relevant: list[dict]) -> str:
        if not relevant:
            return "## 関連する過去の知識\n\nまだ関連する記録はありません。"

        lines = ["## 関連する過去の知識\n"]
        lines.append("以下は、ユーザーが過去に記録した関連知識です。")
        lines.append("回答する際はこれらを参考にし、具体的に引用してください。\n")

        for entry in relevant:
            lines.append(f"### [Dir] {entry['path']}")
            lines.append(entry["content"])
            lines.append("")

        return "\n".join(lines)

    def get_stats(self) -> dict:
        return self.kb.stats

    def reset_conversation(self):
        self.conversation_history = []

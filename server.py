"""
server.py — AIBOU ローカルサーバー (FastAPI)

拡張機能からのリクエストを受け取り、
AIBOUのロジック（知識ベース検索＋LLM）を使ってアドバイスを返す。
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from aibou import Aibou

app = FastAPI(title="AIBOU Local Server")

# 拡張機能からのアクセスを許可
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発用。本番なら chrome-extension://... に絞る
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AIBOU の初期化（V3からOllamaローカル実行のためAPIキー不要。
# モデルはaibou.DEFAULT_MODEL＝環境変数AIBOU_MODELで上書き可能）
aibou_instance = Aibou()


class ContextRequest(BaseModel):
    url: str
    title: str
    text: str = ""

class AskRequest(BaseModel):
    question: str


@app.post("/context")
async def analyze_context(req: ContextRequest):
    """
    拡張機能から URL とページ内容を受け取り、
    何かアドバイスできることがあれば返す。
    """
    # ページ内容からプロンプトを生成
    prompt = (
        f"ユーザーが今、以下のページを見ています。\n"
        f"URL: {req.url}\n"
        f"タイトル: {req.title}\n"
        f"テキストの一部: {req.text[:500]}\n\n"
        f"この状況から、過去の知識を踏まえて、短く（1〜2文で）"
        f"「これに気をつけて！」「こうするといいよ」という気づきがあれば教えて。"
        f"特になければ「特になし」と答えてください。"
    )
    
    # AIBOU に考えさせる（ページ文脈の自動チェックなので会話履歴には残さない。
    # 残すとブラウジングのたびに履歴が肥大し、/askの対話品質が劣化する）
    answer = aibou_instance.ask(prompt, remember=False)
    
    # 関連性のない応答や「特になし」をフィルタリング
    if "特になし" in answer or "アドバイスできることはありません" in answer:
        return {"advice": None}
        
    return {"advice": answer}


@app.post("/ask")
async def ask_aibou(req: AskRequest):
    """通常の質問"""
    answer = aibou_instance.ask(req.question)
    return {"answer": answer}


@app.get("/stats")
async def get_stats():
    """知識ベースの統計"""
    return aibou_instance.get_stats()


if __name__ == "__main__":
    host = os.environ.get("AIBOU_HOST", "127.0.0.1")
    port = int(os.environ.get("AIBOU_PORT", "8000"))
    print(f"AIBOU Server is starting... (http://{host}:{port})")
    uvicorn.run(app, host=host, port=port)

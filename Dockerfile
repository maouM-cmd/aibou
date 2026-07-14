# AIBOU MemoryAgent — Alibaba Cloud (Qwen Cloud Hackathon) デプロイ用イメージ
#
# 起動するのは server.py（FastAPI）のみ。デスクトップ常駐(app.py)専用パッケージは
# requirements-server.txt で意図的に除外している。
FROM python:3.11-slim

WORKDIR /app

# ChromaDBが初回起動時にダウンロードする埋め込みモデルのキャッシュ先を
# 書き込み可能なディレクトリに固定する
ENV HF_HOME=/app/.cache/huggingface
ENV AIBOU_HOST=0.0.0.0
ENV AIBOU_PORT=8000
ENV AIBOU_PROVIDER=qwen

COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

COPY aibou.py server.py ./
COPY prompts/ ./prompts/
COPY knowledge/ ./knowledge/

# .chroma_db と .cache は初回起動時にコンテナ内で生成される（コンテナ再作成で消える点に注意。
# 永続化したい場合は `docker run -v` でボリュームマウントすること）
RUN mkdir -p .chroma_db .cache/huggingface

EXPOSE 8000

CMD ["python", "server.py"]

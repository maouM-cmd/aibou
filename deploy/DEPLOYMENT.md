# Alibaba Cloudへのデプロイ手順

> **審査員の方へ（現状のステータス）**: 本プロジェクトは、Alibaba CloudのAPI（DashScope／Qwen Cloud互換エンドポイント `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`）は[`aibou.py`](../aibou.py)の`_call_qwen_raw()`で実際に利用していますが、バックエンド(`server.py`)自体のAlibaba Cloud ECS等へのホスティングは、今回の提出では**未実施**です（新規クラウドアカウント作成が間に合わなかったため）。
>
> 以下は「実施すればすぐデプロイできる」状態まで準備した手順書です。今後対応する場合はこの手順で進められます。

## 前提
- Alibaba Cloudアカウント（未作成の場合は https://www.alibabacloud.com/ で作成）
- Qwen Cloud APIキー（https://home.qwencloud.com/ で取得、`DASHSCOPE_API_KEY`）
- Dockerが使えること（ローカルとECS両方）

## 手順

### 1. ECS（またはSimple Application Server / 軽量応用服务器）インスタンスを作成
1. Alibaba Cloudコンソールにログイン
2. ECS（Elastic Compute Service）または、より手早く済ませたい場合はSimple Application Server（軽量応用服务器）を選択
3. イメージはUbuntu 22.04などの標準Linuxイメージでよい（Dockerは後からインストール）
4. **セキュリティグループでポート8000（TCP・インバウンド）を開放**しておく（AIBOU_PORTを変える場合はそのポート）

### 2. インスタンスにDockerをインストール
```bash
curl -fsSL https://get.docker.com | sh
sudo systemctl enable --now docker
```

### 3. リポジトリをclone
```bash
git clone https://github.com/maouM-cmd/aibou.git
cd aibou
```

### 4. .envを用意
```bash
cp .env.example .env
# .env を編集し、DASHSCOPE_API_KEY に実際のQwen Cloud APIキーを設定
```

### 5. ビルド＆起動
```bash
docker build -t aibou-memoryagent .
docker run -d --name aibou \
  --env-file .env \
  -p 8000:8000 \
  aibou-memoryagent
```

### 6. 動作確認
```bash
curl -X POST http://<ECSのパブリックIP>:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "こんにちは、あなたは誰ですか？"}'
```
`{"answer": "..."}` が返ってくればAlibaba Cloud上でQwen Cloud経由のAIBOUが動作しています。

### 7. デプロイ後の記録（提出前に必ず埋める）
- パブリックIP / ドメイン: `___________`
- インスタンスID: `___________`
- デプロイ日時: `___________`

この情報を本ファイル冒頭と `SUBMISSION.md` の両方に転記してから提出してください。

## トラブルシューティング
- `DASHSCOPE_API_KEY が設定されていません` エラー → `.env`が`docker run --env-file .env`で正しく読み込まれているか確認
- 起動直後にChromaDBの埋め込みモデルダウンロードで数十秒〜数分かかることがある（`docker logs aibou`で進捗確認）
- ポートに接続できない → セキュリティグループの設定を再確認

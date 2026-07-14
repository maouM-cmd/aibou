"""aibou.py のテスト（KnowledgeBaseの複数ソース読み込み・会話履歴の管理）。

ChromaDBは実物を一時ディレクトリで使う（埋め込みモデルはローカルキャッシュ済み前提）。
Ollama呼び出しは必ずモックする（LLMは起動していなくてもテストが通る）。
"""
from pathlib import Path
from unittest.mock import patch

import pytest

import aibou as aibou_module
from aibou import Aibou, KnowledgeBase, MAX_HISTORY_MESSAGES


@pytest.fixture
def kb_dirs(tmp_path):
    """自前knowledge/と外部ソースの一時ディレクトリを作る"""
    own = tmp_path / "knowledge"
    (own / "tips").mkdir(parents=True)
    (own / "tips" / "own_tip.md").write_text("# 自前のTip\nPlan→Actの順で使う", encoding="utf-8")

    ext = tmp_path / "aigakusyu_digests"
    ext.mkdir()
    (ext / "2026-07-08.md").write_text("# digest\n最新のAIニュース", encoding="utf-8")

    return {
        "own": own,
        "external": {"aigakusyu": [ext, tmp_path / "not_exists"]},
        "db": tmp_path / "chroma",
    }


class TestKnowledgeBaseMultiSource:
    def test_loads_own_and_external_sources(self, kb_dirs):
        kb = KnowledgeBase(data_dir=kb_dirs["own"],
                           external_sources=kb_dirs["external"], db_dir=kb_dirs["db"])
        paths = [e["path"] for e in kb.get_all()]
        assert any("own_tip.md" in p for p in paths)
        assert any(p.startswith("ext:aigakusyu/") for p in paths)

    def test_missing_external_dir_is_skipped(self, kb_dirs):
        """存在しない外部ディレクトリがあっても止まらない（not_existsを含めて初期化済み）"""
        kb = KnowledgeBase(data_dir=kb_dirs["own"],
                           external_sources=kb_dirs["external"], db_dir=kb_dirs["db"])
        assert kb.stats["total_files"] == 2  # own_tip + digest

    def test_add_entry_writes_only_to_own_dir(self, kb_dirs):
        kb = KnowledgeBase(data_dir=kb_dirs["own"],
                           external_sources=kb_dirs["external"], db_dir=kb_dirs["db"])
        saved = kb.add_entry("新しい学び", category="journal")
        assert Path(saved).is_relative_to(kb_dirs["own"])
        # 外部ソースディレクトリには何も書き込まれていない
        ext_dir = kb_dirs["external"]["aigakusyu"][0]
        assert len(list(ext_dir.glob("*.md"))) == 1

    def test_external_category_prefix(self, kb_dirs):
        kb = KnowledgeBase(data_dir=kb_dirs["own"],
                           external_sources=kb_dirs["external"], db_dir=kb_dirs["db"])
        cats = kb.stats["categories"]
        assert "ext:aigakusyu" in cats


class TestConversationHistory:
    @pytest.fixture
    def aibou_no_kb(self):
        return Aibou(use_kb=False)

    def _mock_response(self, text="回答"):
        return {"message": {"content": text}}

    def test_remember_true_appends_history(self, aibou_no_kb):
        with patch.object(aibou_no_kb, "_call_ollama_raw", return_value=self._mock_response()):
            aibou_no_kb.ask("質問1")
        assert len(aibou_no_kb.conversation_history) == 2

    def test_remember_false_keeps_history_clean(self, aibou_no_kb):
        with patch.object(aibou_no_kb, "_call_ollama_raw", return_value=self._mock_response()):
            aibou_no_kb.ask("ページ文脈チェック", remember=False)
        assert aibou_no_kb.conversation_history == []

    def test_history_capped_at_max(self, aibou_no_kb):
        with patch.object(aibou_no_kb, "_call_ollama_raw", return_value=self._mock_response()):
            for i in range(MAX_HISTORY_MESSAGES):  # 上限の2倍のメッセージ数になる回数
                aibou_no_kb.ask(f"質問{i}")
        assert len(aibou_no_kb.conversation_history) == MAX_HISTORY_MESSAGES
        # 最新の質問が残り、最古が消えている
        contents = [m["content"] for m in aibou_no_kb.conversation_history]
        assert f"質問{MAX_HISTORY_MESSAGES - 1}" in contents
        assert "質問0" not in contents

    def test_default_model_used(self):
        a = Aibou(use_kb=False)
        assert a.model == aibou_module.DEFAULT_MODEL

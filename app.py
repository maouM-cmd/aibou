import sys
import io
import os
import time
import threading
import tkinter as tk
from tkinter import simpledialog
import pygetwindow as gw
import mss
from PIL import Image
import base64
import speech_recognition as sr
import pyttsx3
import keyboard

from aibou import Aibou, DEFAULT_MODEL

# Windows の日本語コンソール対応
_utf8_out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 反応させるウィンドウタイトルのキーワード（AI開発ツールを中心に）
TARGET_KEYWORDS = [
    "Cursor", "Antigravity", "Cloud Code", "ChatGPT", "Claude", "Gemini", "AI",
    "Visual Studio Code", "Code", "Terminal", "PowerShell", "コマンドプロンプト"
]

class AibouApp:
    def __init__(self, root, aibou: Aibou):
        self.root = root
        self.aibou = aibou
        self.current_window_title = ""
        self.asking = False  # テキスト質問の多重起動防止
        
        # --- アクティビティログ & キャッシュ ---
        self.activity_log = {}
        self.window_start_time = time.time()
        self.advice_cache = {}  # { "title_or_text": timestamp }
        self.CACHE_TTL = 60 * 15  # 同じ質問は15分間ブロック
        
        # ウィンドウ設定
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.transparent_color = 'black'
        self.root.configure(bg=self.transparent_color)
        self.root.attributes("-transparentcolor", self.transparent_color)

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.ui_width = 350
        self.ui_height = 200
        x = screen_width - self.ui_width - 20
        y = screen_height - self.ui_height - 60
        self.root.geometry(f"{self.ui_width}x{self.ui_height}+{x}+{y}")

        # --- UI の構築 ---
        self.bubble_frame = tk.Frame(self.root, bg="#333333", padx=10, pady=10)
        self.bubble_label = tk.Label(
            self.bubble_frame,
            text="",
            bg="#333333",
            fg="white",
            font=("Meiryo", 10),
            wraplength=280,
            justify="left"
        )
        self.bubble_label.pack()
        
        self.icon_label = tk.Label(
            self.root,
            text="🎓",  # アイコンをメンターっぽく変更
            font=("Segoe UI Emoji", 40),
            bg=self.transparent_color,
            fg="white"
        )
        self.icon_label.place(relx=1.0, rely=1.0, anchor="se")
        
        self.icon_label.bind("<Button-1>", self.start_move)
        self.icon_label.bind("<B1-Motion>", self.do_move)
        self.icon_label.bind("<Double-Button-1>", self.on_text_question)  # ダブルクリックでテキスト質問
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 音声対話ショートカットキーの登録 (Ctrl + Shift + Space)
        try:
            keyboard.add_hotkey('ctrl+shift+space', self.on_voice_shortcut)
        except Exception as e:
            print(f"Hotkey registration failed (Admin rights may be needed): {e}", file=_utf8_out)
        
        # 監視スレッド
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()


    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")


    def show_advice(self, text, duration=10000):
        if not text or text.strip() == "" or "特になし" in text:
            return
            
        self.bubble_label.config(text=text)
        self.bubble_frame.place(relx=1.0, rely=1.0, x=-60, y=-60, anchor="se")
        self.root.after(duration, lambda: self.bubble_frame.place_forget())

    def is_cached(self, key: str) -> bool:
        """キャッシュされている（直近で同じことを聞いた）か"""
        if key in self.advice_cache:
            if time.time() - self.advice_cache[key] < self.CACHE_TTL:
                return True
        return False

    def is_target_window(self, title: str) -> bool:
        """AIツールや開発に関連するウィンドウか判定"""
        for kw in TARGET_KEYWORDS:
            if kw.lower() in title.lower():
                return True
        return False

    def on_text_question(self, event=None):
        """アイコンのダブルクリックでテキスト質問（音声が使えない環境向け）"""
        if self.asking:
            return
        question = simpledialog.askstring("AIBOU", "相棒に質問:", parent=self.root)
        if not question or not question.strip():
            return

        self.asking = True
        self.show_advice(f"🤔 「{question.strip()}」\n\n考え中...", 60000)

        def _ask():
            try:
                # ユーザーとの対話なので履歴に残す（remember=True既定）
                answer = self.aibou.ask(question.strip())
                self.root.after(0, self.show_advice, "🎓 " + answer, 30000)
            except Exception as e:
                self.root.after(0, self.show_advice, f"⚠️ エラー: {e}", 5000)
            finally:
                self.asking = False

        threading.Thread(target=_ask, daemon=True).start()

    def monitor_loop(self):
        """監視ループ（軽量・非同期）"""
        while True:
            try:
                # 1. ウィンドウ監視
                active_window = gw.getActiveWindow()
                if active_window and active_window.title:
                    title = active_window.title
                    
                    if title != self.current_window_title and title.strip() != "":
                        elapsed = time.time() - self.window_start_time
                        if self.current_window_title:
                            self.activity_log[self.current_window_title] = self.activity_log.get(self.current_window_title, 0) + elapsed
                        
                        self.current_window_title = title
                        self.window_start_time = time.time()
                        
                        if self.is_target_window(title) and not self.is_cached(title):
                            self.advice_cache[title] = time.time()
                            # 画面監視（Vision）はモデルが重く404エラーになるため一時無効化
                            # threading.Thread(target=self.analyze_window_context, args=(active_window.title,), daemon=True).start()

            except Exception as e:
                print(f"Monitor error: {e}", file=_utf8_out)
                
            time.sleep(3)

    def analyze_window_context(self, window_title):
        if "AIBOU" in window_title or "Task Switching" in window_title:
            return
            
        # 1. 画面のスクリーンショットを取得して圧縮
        base64_image = ""
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]  # プライマリモニタ
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                img.thumbnail((800, 800))
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG", quality=60)
                base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"Vision Capture Error: {e}", file=_utf8_out)

        prompt = (
            f"ユーザーは今、以下のAI開発ツール・ウィンドウを開いています。\n"
            f"ウィンドウタイトル: {window_title}\n\n"
            f"添付された「現在のユーザーの作業画面」のスクリーンショットを見てください。\n"
            f"もし画面上に明らかなエラーや、GUIの崩れ、またはAI（CursorやAntigravity等）の"
            f"非効率な使い方があれば、メンターとして1〜2文で鋭く指摘してください。\n"
            f"特に言うことがなければ、絶対に「特になし」と答えてください。"
        )
        
        try:
            if base64_image:
                answer = self.aibou.ask_with_vision(prompt, base64_image)
            else:
                # 自動監視の質問なので会話履歴には残さない
                answer = self.aibou.ask(prompt, remember=False)

            self.root.after(0, self.show_advice, "👁️ " + answer, 12000)
        except Exception as e:
            print(f"LLM Vision error: {e}", file=_utf8_out)

    # --- Voice UI (音声対話) ---
    def speak(self, text):
        """テキストを音声で読み上げる（非同期）"""
        def _run_tts():
            try:
                # pyttsx3の初期化はスレッド内で行うのが安全
                engine = pyttsx3.init()
                # 読み上げ速度を少し速める
                rate = engine.getProperty('rate')
                engine.setProperty('rate', rate + 20)
                engine.say(text)
                engine.runAndWait()
            except Exception as e:
                print(f"TTS Error: {e}", file=_utf8_out)
        
        threading.Thread(target=_run_tts, daemon=True).start()

    def listen_and_answer(self):
        """マイクから音声を拾い、画面を見ながら回答する"""
        recognizer = sr.Recognizer()
        
        # UI更新（メインスレッド）
        self.root.after(0, self.show_advice, "🎙️ 聞いています... (話してください)", 5000)
        
        try:
            with sr.Microphone() as source:
                # 録音
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            # テキスト化
            self.root.after(0, self.show_advice, "🤔 音声を解析中...", 5000)
            text = recognizer.recognize_google(audio, language="ja-JP")
            print(f"ユーザーの音声: {text}", file=_utf8_out)
            
            # 画面スクショ取得
            base64_image = ""
            try:
                with mss.mss() as sct:
                    monitor = sct.monitors[1]
                    sct_img = sct.grab(monitor)
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                    img.thumbnail((800, 800))
                    buffered = io.BytesIO()
                    img.save(buffered, format="JPEG", quality=60)
                    base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
            except Exception as e:
                pass
                
            prompt = (
                f"ユーザーから音声で以下の質問・相談がありました:\n"
                f"「{text}」\n\n"
                f"あなたは音声で返答する熟練メンターです。\n"
                f"もし添付された画面スクリーンショットがあれば、それも考慮してアドバイスしてください。\n"
                f"口語体で、親しみやすく、短く（2〜3文で）簡潔に答えてください。"
            )
            
            self.root.after(0, self.show_advice, f"🗣️ 「{text}」\n\n考え中...", 10000)
            
            # メモリ不足と404エラー回避のため、画像は送らず常に通常のモデルで回答
            answer = self.aibou.ask(prompt)
                
            # 回答をテキスト表示＆音声合成
            self.root.after(0, self.show_advice, "🎓 " + answer, 15000)
            self.speak(answer)

        except sr.UnknownValueError:
            self.root.after(0, self.show_advice, "👂 音声が聞き取れませんでした。", 3000)
        except sr.WaitTimeoutError:
            self.root.after(0, self.show_advice, "💤 タイムアウトしました。", 3000)
        except Exception as e:
            self.root.after(0, self.show_advice, f"⚠️ 音声エラー: {e}", 5000)
            print(f"Voice Error: {e}", file=_utf8_out)

    def on_voice_shortcut(self):
        """ショートカットが押されたら非同期で音声認識開始"""
        threading.Thread(target=self.listen_and_answer, daemon=True).start()

    def on_closing(self):
        self.show_advice("今日の活動を振り返って学習中...\n(しばらくお待ちください)", 10000)
        
        if self.current_window_title:
            elapsed = time.time() - self.window_start_time
            self.activity_log[self.current_window_title] = self.activity_log.get(self.current_window_title, 0) + elapsed

        sorted_log = sorted(self.activity_log.items(), key=lambda x: x[1], reverse=True)[:10]
        log_text = "\n".join([f"- {title} : {int(seconds/60)}分" for title, seconds in sorted_log if seconds > 60])
        
        if not log_text:
            self.root.destroy()
            return

        def save_learning():
            prompt = (
                "ユーザーの今日のPCアクティビティ履歴（使用したアプリと時間）を元に、1日の振り返り日報を生成してください。\n"
                f"{log_text}\n\n"
                "Markdown形式で「今日何をしたか」「どんな発見があったか」をフランクにまとめてください。"
            )
            try:
                # 終了時の自動日報生成なので会話履歴には残さない
                summary = self.aibou.ask(prompt, remember=False)
                saved_path = self.aibou.learn(f"【自動生成ログ】\n\n{summary}", category="journal")
                print(f"自動学習ログを保存しました: {saved_path}", file=_utf8_out)
            except Exception:
                pass
            finally:
                self.root.after(0, self.root.destroy)

        threading.Thread(target=save_learning, daemon=True).start()


import auto_learner

def main():
    print(f"Ollamaモデル '{DEFAULT_MODEL}' で起動します...", file=_utf8_out)

    # 知識ベース（RAG）有効。初期化失敗時はAibou内でNoneフォールバックするため
    # メモリ不足でも起動自体は継続する。重い場合は AIBOU_MODEL=llama3.2:1b で逃がす
    aibou = Aibou(use_kb=True)
    if aibou.kb:
        stats = aibou.get_stats()
        print(f"知識ベース: {stats['total_files']}ファイルを読み込みました", file=_utf8_out)

    # 起動時の自動学習（Webクロール）は AIBOU_AUTOLEARN=1 のときだけ実行
    if os.environ.get("AIBOU_AUTOLEARN") == "1":
        threading.Thread(target=auto_learner.run_auto_learning, args=(aibou,), daemon=True).start()

    root = tk.Tk()
    app = AibouApp(root, aibou)
    app.show_advice("常駐を開始したよ！\nアイコンをダブルクリックで質問できるよ")
    root.mainloop()

if __name__ == "__main__":
    main()

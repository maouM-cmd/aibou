import os
import sys
import io
import time
import subprocess

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def main():
    print("Testing app.py to catch the communication error...")
    
    # app.py をサブプロセスとして起動
    python_exe = r"C:\Users\admin\AppData\Local\Programs\Python\Python311\python.exe"
    process = subprocess.Popen([python_exe, "app.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    
    # 15秒間待機（AIBOUが起動し、Visionやクリップボードチェックを走らせるのを待つ）
    print("Waiting 15 seconds for AIBOU to generate errors...")
    time.sleep(15)
    
    # プロセスを終了
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        
    stdout_out, stderr_out = process.communicate()
    
    print("\n--- STDOUT ---")
    print(stdout_out)
    print("\n--- STDERR ---")
    print(stderr_out)

if __name__ == "__main__":
    main()

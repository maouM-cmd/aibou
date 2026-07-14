import sys
import io
import urllib.error

# Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from aibou import Aibou

def main():
    print("Testing Ollama API connection...")
    aibou = Aibou(model="hermes3", use_kb=False)
    try:
        res = aibou.ask("テスト通信です。返事をしてください。")
        print(f"Result:\n{res}")
    except Exception as e:
        print(f"Test failed with exception: {e}")

if __name__ == "__main__":
    main()

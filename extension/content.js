// content.js - 表示しているWebページ内で動くスクリプト

// 1. AIBOU アイコンと吹き出しのUIを注入
function createAibouUI() {
  const container = document.createElement('div');
  container.id = 'aibou-container';

  const speechBubble = document.createElement('div');
  speechBubble.id = 'aibou-speech-bubble';
  speechBubble.className = 'hidden';

  const icon = document.createElement('div');
  icon.id = 'aibou-icon';
  icon.innerText = '🤖';

  container.appendChild(speechBubble);
  container.appendChild(icon);
  document.body.appendChild(container);
  
  return { speechBubble, icon };
}

const { speechBubble, icon } = createAibouUI();

// 2. メッセージ受信処理 (background.js からの指示)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // バックグラウンドからページ情報を求められた時
  if (request.action === "getPageContext") {
    sendResponse({
      title: document.title,
      url: window.location.href,
      text: document.body.innerText.substring(0, 2000) // 最初の2000文字を抽出
    });
    return true;
  }
  
  // バックグラウンドからアドバイスが届いた時
  if (request.action === "showAdvice") {
    showAdvice(request.advice);
  }
});

// 3. アドバイス表示のアニメーション
function showAdvice(text) {
  speechBubble.innerText = text;
  speechBubble.classList.remove('hidden');
  speechBubble.classList.add('visible');
  icon.classList.add('bounce');
  
  // 10秒後に消す
  setTimeout(() => {
    speechBubble.classList.remove('visible');
    speechBubble.classList.add('hidden');
    icon.classList.remove('bounce');
  }, 10000);
}

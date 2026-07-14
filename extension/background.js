// background.js - 拡張機能の裏側で動くワーカー

console.log("AIBOU Background Worker Started.");

// タブが更新された時（ページ遷移時）に発火
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.url && !tab.url.startsWith("chrome://")) {
    
    // content.js に「ページのテキストを取得して」とメッセージを送る
    chrome.tabs.sendMessage(tabId, { action: "getPageContext" }, (response) => {
      if (chrome.runtime.lastError || !response) {
        return;
      }
      
      const { title, text, url } = response;
      
      // ローカルサーバーにコンテキストを送信
      fetch("http://127.0.0.1:8000/context", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, title, text })
      })
      .then(res => res.json())
      .then(data => {
        // アドバイスがあれば content.js に送って表示させる
        if (data.advice) {
          chrome.tabs.sendMessage(tabId, { action: "showAdvice", advice: data.advice });
        }
      })
      .catch(err => console.error("AIBOU Server Error:", err));
    });
  }
});

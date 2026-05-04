// listens to content-script messages
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'lens') {
      fetch('http://localhost:8000/search', {  // <-- change to your domain
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({imgUrl: msg.imgUrl})
      })
      .then(r => r.json())
      .then(arr => sendResponse(arr))
      .catch(() => sendResponse([]));
      return true; // keep channel open for async
    }
  });
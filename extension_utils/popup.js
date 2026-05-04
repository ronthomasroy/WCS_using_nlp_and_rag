const list = document.getElementById('list');

(async () => {
    try {
      const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
      // ask content-script for main image
      const {imgUrl} = await chrome.tabs.sendMessage(tab.id, {type: 'getImg'});
      list.innerHTML = `<li>Found image: ${imgUrl || '(none)'}</li>`;
      // ask background to call our server
      const resp = await chrome.runtime.sendMessage({type: 'lens', imgUrl});
      list.innerHTML = '';

      // support old response (array) and new response shape { ai_summary, matches }
      let aiSummary = '';
      let matches = [];
      if (Array.isArray(resp)) {
        matches = resp;
      } else if (resp && typeof resp === 'object') {
        aiSummary = resp.ai_summary || '';
        matches = resp.matches || [];
      }

      if (aiSummary) {
        const li = document.createElement('li');
        li.textContent = aiSummary;
        list.appendChild(li);
      }

      if (!matches.length) {
        if (!aiSummary) list.innerHTML = '<li>No other occurrences found</li>';
        return;
      }

      matches.forEach(m => {
        const li = document.createElement('li');
        const heading = m.heading || m.title || m.url || '';
        li.innerHTML = `<img src="${m.thumb || ''}"> <a href="${m.url}" target="_blank">${heading}</a>`;
        list.appendChild(li);
      });
    } catch (err) {
      list.innerHTML = `<li>Could not reach content script. Make sure the page is not a Chrome internal page and reload after reloading the extension.</li>`;
    }
  })();
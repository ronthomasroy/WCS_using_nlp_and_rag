// pick the most representative image
function mainImage() {
    const meta = document.querySelector('meta[property="og:image"]')?.content ||
                 document.querySelector('meta[name="twitter:image"]')?.content;
    if (meta) return meta;
    const big = [...document.images].sort((a, b) =>
      (b.naturalWidth * b.naturalHeight) - (a.naturalWidth * a.naturalHeight))[0];
    return big ? big.src : '';
  }
  
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'getImg') sendResponse({imgUrl: mainImage()});
  });
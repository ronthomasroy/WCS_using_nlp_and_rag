(async function(){
  // Auto-scan all images on the page and extract nearest paragraph text.
  function abs(u){ try{ return new URL(u, location.href).href }catch(e){ return u } }
  const imgs = Array.from(document.images);

  const txt = s=>s && s.replace(/\s+/g,' ').trim();

  function getCandidatesForImage(img){
    const candidates = [];
    if(img.alt) candidates.push({score:100, text: txt(img.alt)});
    const fig = img.closest('figure');
    if(fig){ const fc = fig.querySelector('figcaption'); if(fc) candidates.push({score:90, text: txt(fc.textContent)}); }
    ['previousElementSibling','nextElementSibling'].forEach(dir=>{
      let e = img[dir];
      for(let i=0;i<6 && e;i++, e = e[dir]){
        if(/^(P|DIV|SPAN|FIGCAPTION|ARTICLE|SECTION|FIGURE|H[1-6])$/.test(e.tagName)){
          candidates.push({score:80 - i, text: txt(e.textContent)});
        }
      }
    });
    const parent = img.parentElement;
    if(parent){
      const kids = Array.from(parent.children);
      const idx = kids.indexOf(img);
      for(let offset=1; offset<=4; offset++){
        const b = kids[idx-offset]; if(b) candidates.push({score:60-offset, text: txt(b.textContent)});
        const a = kids[idx+offset]; if(a) candidates.push({score:55-offset, text: txt(a.textContent)});
      }
      candidates.push({score:10, text: txt(parent.textContent)});
    }
    return candidates;
  }

  function pickBestText(candidates){
    const uniq = new Map();
    for(const c of candidates){
      if(c.text){
        const t = c.text.trim();
        if(t){
          uniq.set(t, Math.max(uniq.get(t)||0, c.score));
        }
      }
    }
    if(!uniq.size) return null;
    const best = Array.from(uniq.entries()).sort((a,b)=>b[1]-a[1])[0][0];
    const sentences = best.match(/[^.!?]+[.!?]*/g) || [best];
    return sentences.slice(0,3).join(' ').trim();
  }

  // Process all images and return JSON mapping src -> best nearby paragraph
  const results = imgs.map(i=>{
    const src = abs(i.currentSrc || i.src || '');
    const best = pickBestText(getCandidatesForImage(i));
    return {src, text: best};
  }).filter(r=>r.text);

  if(!results.length){ console.log('No nearby text found for any image'); alert('No nearby text found for any image'); return; }

  // print JSON to console for easy copy/paste and show brief alert
  console.log(JSON.stringify(results, null, 2));
  alert('Found captions for ' + results.length + ' images (see console).');
})();
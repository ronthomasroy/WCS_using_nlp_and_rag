#!/usr/bin/env python3
# pip install fastapi uvicorn requests
import re, json, requests, asyncio, os, logging
from dotenv import load_dotenv
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
logger = logging.getLogger("uvicorn.error")

# load environment variables from .env if present
load_dotenv()

def _clean_google_redirect(url: str) -> str:
    # Google often wraps outbound links as "/url?q=<real>&sa=..."
    m = re.search(r"[?&]q=([^&]+)", url)
    if not m:
        return url
    try:
        from urllib.parse import unquote

        return unquote(m.group(1))
    except Exception:
        return m.group(1)



async def heading(url: str):
    try:
        html = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"}).text[:50_000]
        h = re.search(r'<h1[^>]*>(.*?)</h1>', html, flags=re.I | re.S)
        if h:
            return h.group(1).strip()
        t = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
        return t.group(1).strip() if t else url
    except Exception:
        return url


def extract_short_summary(text: str, max_sentences: int = 3) -> str:
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text).strip()
    sentences = re.split(r'(?<=[\.\?\!])\s+', text)
    return ' '.join(sentences[:max_sentences]).strip()


def _extract_ai_summary(ai_overview: dict) -> str:
    if not ai_overview:
        return ""
    blocks = ai_overview.get("text_blocks") or []
    para_texts = []
    for b in blocks:
        if b.get("type") == "paragraph" and b.get("snippet"):
            para_texts.append(b["snippet"].strip())
    if not para_texts:
        # fallback: join any snippet-like fields
        for b in blocks:
            s = b.get("snippet") or b.get("title")
            if s:
                para_texts.append(s.strip())
    joined = " ".join(para_texts)
    return extract_short_summary(joined, max_sentences=3)


async def serpapi_search_and_summary(image_url: str, query: Optional[str], api_key: str):
    base = "https://serpapi.com/search.json"
    params = {"engine": "google_lens", "url": image_url, "api_key": api_key}
    if query:
        params["q"] = query
    try:
        r = requests.get(base, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning("serpapi google_lens request failed: %s", e)
        return {"ai_summary": "", "matches": []}

    # Extract visual matches (keep ONLY the top match)
    visual = data.get("visual_matches") or []
    matches = []
    if visual:
        v = visual[0]
        matches.append({
            "url": _clean_google_redirect(v.get("link") or ""),
            "thumb": v.get("thumbnail") or v.get("image") or "",
            "title": v.get("title") or v.get("source") or v.get("link") or "",
        })

    # If AI overview present, fetch full ai_overview via google_ai_overview engine
    ai_overview = data.get("ai_overview")
    ai_summary = ""
    if ai_overview and ai_overview.get("page_token"):
        page_token = ai_overview.get("page_token")
        try:
            r2 = requests.get(base, params={"engine": "google_ai_overview", "page_token": page_token, "api_key": api_key}, timeout=30)
            r2.raise_for_status()
            data2 = r2.json()
            ai_summary = _extract_ai_summary(data2.get("ai_overview", {}))
        except Exception as e:
            logger.warning("serpapi google_ai_overview request failed: %s", e)
            ai_summary = _extract_ai_summary(ai_overview)
    else:
        ai_summary = _extract_ai_summary(ai_overview)

    return {"ai_summary": ai_summary, "matches": matches}



# uvicorn server:app --host 0.0.0.0 --port 8000

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)


class ImgIn(BaseModel):
    imgUrl: str
    query: Optional[str] = None


@app.post("/search")
async def search(body: ImgIn):
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        logger.warning("SERPAPI_API_KEY not set; returning empty results")
        return {"ai_summary": "", "matches": []}

    logger.info("received imgUrl for SerpAPI: %s", body.imgUrl)
    result = await serpapi_search_and_summary(body.imgUrl, body.query or "what is this image, its origin and date of event", api_key)

    # enrich matches with headings in parallel
    jobs = [heading(m["url"]) for m in result["matches"] if m.get("url")]
    if jobs:
        headings = await asyncio.gather(*jobs)
        for m, h in zip(result["matches"], headings):
            m["heading"] = h

    return result
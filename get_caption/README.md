Nearest paragraph scraper + proper-noun extractor
(sub component used in the https://github.com/ronthomasroy/WCS_using_nlp_and_rag )

**Purpose**
- Extract the paragraph of text closest to images on a web page (automatically).
- Feed that paragraph into the Python proper-noun extractor to get person/place/object names.

**Files**
- [nearest_paragragh_scrape.js](nearest_paragragh_scrape.js): Browser script that scans all images on the current page and logs a JSON array of `{src, text}` where `text` is the nearest paragraph(s) found.
- [propernoun_extract.py](propernoun_extract.py): Python script that extracts proper nouns from a paragraph (returns a JSON list).

**How the scraper works**
- For each `<img>` on the page it gathers nearby candidate text in this order of preference: `alt`, `figcaption`, nearby sibling paragraphs/headings, nearby sibling elements in the same parent, and finally the parent element's text.
- It scores candidates by closeness and returns the highest-scoring paragraph (up to the first 3 sentences) per image as `text`.
- The script prints a compact JSON array to the console so you can copy the text out easily for further processing.

Quick usage (in your browser)
1. Open the target page in your browser.
2. Open Developer Tools → Console.
3. Paste the contents of `nearest_paragragh_scrape.js` into the console and press Enter.
4. The console will print a JSON array of results. Copy the `text` field for the image you want.

Example console output (abbreviated):
```
[
  {
    "src": "https://example.com/img1.jpg",
    "text": "Trivandrum's coastal stretch — including the famous Kovalam beach, offers sandy shores..."
  },
  ...
]
```

Feeding the scraped paragraph to the Python extractor
- Option A: pass inline text
  - Copy the paragraph text from the console and run:
    `python propernoun_extract.py -t "Trivandrum's coastal stretch ..."`
- Option B: save to a file and pass the file
  - Save the paragraph into `input.txt` and run:
    `python propernoun_extract.py -f input.txt`

I developed this to be later added to the larger workflow , but it can also be used as a single tool, though I haven't set it up as a single pipeline.

Dependencies and environment
- The Python extractor uses NLTK. Install dependencies in a virtual environment:
```
python -m pip install -U pip
python -m pip install nltk
```
- `propernoun_extract.py` will download required NLTK data into the project-local `nltk_data` folder on first run (so you usually do not need to manually run `nltk.download`).
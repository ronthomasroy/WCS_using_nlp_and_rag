import os
import nltk
import argparse
import json
import re
from nltk import word_tokenize, pos_tag, ne_chunk
from nltk.tree import Tree

# use a project-local nltk_data so the script is portable across machines
LOCAL_NLTK_DATA = os.path.join(os.path.dirname(__file__), "nltk_data")
os.makedirs(LOCAL_NLTK_DATA, exist_ok=True)
nltk.data.path.insert(0, LOCAL_NLTK_DATA)

# ensure required resources are present (downloads only if missing)
for r in ("punkt", "punkt_tab", "averaged_perceptron_tagger", "maxent_ne_chunker", "maxent_ne_chunker_tab", "words"):
    try:
        nltk.data.find(r)
    except LookupError:
        nltk.download(r, download_dir=LOCAL_NLTK_DATA, quiet=True)


def extract_proper_nouns(text):
    """
    Extract proper nouns (prefer multiword phrases) from text using NLTK.

    Returns a list of phrases (strings) discovered in document order.
    """
    if not text or not text.strip():
        return []

    tokens = word_tokenize(text)
    pos_tags = pos_tag(tokens)
    ne_tree = ne_chunk(pos_tags)

    candidates = []  # list of (phrase, first_token_index)

    # Collect named entities (multi-token preferred)
    for subtree in ne_tree:
        if isinstance(subtree, Tree):
            ent = " ".join(word for word, tag in subtree.leaves())
            first_word = subtree.leaves()[0][0]
            try:
                first_idx = tokens.index(first_word)
            except ValueError:
                first_idx = 0
            candidates.append((ent, first_idx))

    # Capture contiguous NNP sequences and optional following noun (e.g., 'Kovalam beach')
    for i, (word, tag) in enumerate(pos_tags):
        if tag in ("NNP", "NNPS"):
            j = i
            seq = [word]
            j += 1
            while j < len(pos_tags) and pos_tags[j][1] in ("NNP", "NNPS"):
                seq.append(pos_tags[j][0])
                j += 1
            if j < len(pos_tags) and pos_tags[j][1] in ("NN", "NNS"):
                seq.append(pos_tags[j][0])
            phrase = " ".join(seq)
            candidates.append((phrase, i))

    if not candidates:
        return []

    # Normalize and pick best form per normalized key
    def norm(s):
        return re.sub(r"[^\w\s]", "", s).lower().strip()

    forms = {}
    first_pos = {}
    for phrase, pos in candidates:
        key = norm(phrase)
        if not key:
            continue
        cur = forms.get(key)
        if cur is None:
            forms[key] = phrase
            first_pos[key] = pos
        else:
            if len(phrase.split()) > len(cur.split()) or (len(phrase.split()) == len(cur.split()) and len(phrase) > len(cur)):
                forms[key] = phrase
                first_pos[key] = pos

    # Remove keys that are substrings of longer keys (keep longer)
    keys = sorted(forms.keys(), key=lambda k: (-len(k.split()), -len(k)))
    kept = []
    for k in keys:
        if any(k in other for other in kept):
            continue
        kept.append(k)

    # Order by first appearance
    kept.sort(key=lambda k: first_pos.get(k, 0))
    results = [forms[k] for k in kept]

    # Clean results: strip stray punctuation, split off sentence-attached fragments,
    # and filter common stopwords and adverb-like tokens.
    try:
        from nltk.corpus import stopwords
        STOPWORDS = set(stopwords.words('english'))
    except Exception:
        STOPWORDS = {
            'and','the','of','a','an','in','on','at','for','with','to','from','by',
            'is','are','was','were','it','its','that','this','these','those','be',
            'as','if','or','but','not','then','so','than','too','very','also'
        }

    cleaned = []
    seen = set()
    for ph in results:
        # split on sentence punctuation to remove attachments like 'beach.The'
        ph = re.split(r'[\.!?\n]', ph)[0].strip()
        # strip leading/trailing non-word characters
        ph = re.sub(r"^[^\w']+|[^\w']+$", "", ph)
        if not ph:
            continue
        nk = re.sub(r"[^\w\s]", "", ph).lower().strip()
        if not nk:
            continue
        # filter stopwords
        if nk in STOPWORDS:
            continue
        # filter short tokens and obvious adverbs
        if len(nk) <= 1:
            continue
        if nk.endswith('ly'):
            continue
        if nk in seen:
            continue
        seen.add(nk)
        cleaned.append(ph)

    return cleaned


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Extract proper nouns from text")
    p.add_argument("-t", "--text", help="Text input (quoted)")
    p.add_argument("-f", "--file", help="Path to a text file to read")
    args = p.parse_args()

    txt = args.text
    if not txt and args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            txt = fh.read()
    if not txt:
        import sys
        txt = sys.stdin.read().strip()

    if not txt:
        print("")
    else:
        result = extract_proper_nouns(txt)
        print(json.dumps(result))

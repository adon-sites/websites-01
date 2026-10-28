"""Editorial audit for candidate articles before merging into posts.json.

This report flags lexical similarity for a human content review. It cannot
certify clinical accuracy or that differently worded articles have distinct
meaning; those require reading the candidate text and its source.
"""
import collections
import itertools
import json
import pathlib
import re
import sys

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = pathlib.Path(__file__).resolve().parents[1]
published_mode = sys.argv[1:] == ["--published"]
existing = [] if published_mode else json.loads((ROOT / "content/posts.json").read_text())
paths = [] if published_mode else [pathlib.Path(p) for p in sys.argv[1:]]
candidates = json.loads((ROOT / "content/posts.json").read_text()) if published_mode else list(itertools.chain.from_iterable(json.loads(p.read_text()) for p in paths))
items = existing + candidates
refs = {p.name for p in (ROOT / "content/reference").glob("*.txt")}

def source_names(sources):
    names = []
    for source in sources:
        if isinstance(source, str) and not re.match(r"https?://", source):
            names.append(pathlib.Path(source).name)
        elif isinstance(source, dict) and source.get("path"):
            names.append(pathlib.Path(source["path"]).name)
    return names

def normalize(value):
    return re.sub(r"[^가-힣a-z0-9]", "", value.lower())

def body(post):
    return " ".join(section[1] for section in post["sections"])

errors = []
slugs = [p["slug"] for p in items]
titles = [normalize(p["title"]) for p in items]
for field, values in (("slug", slugs), ("title", titles)):
    repeated = [v for v, count in collections.Counter(values).items() if count > 1]
    if repeated:
        errors.append({"type": "repeated_" + field, "values": repeated})
for post in candidates:
    text = body(post)
    if len("".join(s[1] for s in post["sections"])) < 1300:
        errors.append({"type": "short_visible_body", "slug": post["slug"], "length": len("".join(s[1] for s in post["sections"]))})
    if len(normalize(text)) < 650:
        errors.append({"type": "short_body", "slug": post["slug"], "length": len(normalize(text))})
    if len(post["sections"]) < 7 or any(len(s) != 2 or len(s[1]) <= 60 for s in post["sections"]):
        errors.append({"type": "short_section", "slug": post["slug"]})
    names = source_names(post.get("sources", []))
    if not (post.get("sources") or post.get("sourceScope")) or not set(names).issubset(refs):
        errors.append({"type": "source_missing", "slug": post["slug"], "sources": post.get("sources")})
    if len({normalize(s[0]) for s in post["sections"]}) < len(post["sections"]):
        errors.append({"type": "repeated_heading", "slug": post["slug"]})
    if re.search(r"100%|완치|부작용 없음|반영구적|최저가|기적의", text):
        errors.append({"type": "claim_needs_review", "slug": post["slug"]})

vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(3, 5), min_df=2)
matrix = vectorizer.fit_transform([body(p) for p in items])
similarity = cosine_similarity(matrix)
flagged = []
closest = []
for i in range(len(items)):
    for j in range(max(len(existing), i + 1), len(items)):
        if i == j:
            continue
        score = float(similarity[i, j])
        closest.append({"score": round(score, 3), "a": items[i]["slug"], "b": items[j]["slug"]})
        if score >= 0.50:
            flagged.append({"score": round(score, 3), "a": items[i]["slug"], "b": items[j]["slug"]})
flagged.sort(key=lambda x: x["score"], reverse=True)
closest.sort(key=lambda x: x["score"], reverse=True)

report = {
    "existing": len(existing), "candidates": len(candidates),
    "categories": dict(collections.Counter(p["category"] for p in candidates)),
    "errors": errors, "lexically_similar_pairs_for_manual_review": flagged,
    "closest_pairs": closest[:30],
    "note": "Low lexical similarity does not establish distinct meaning or medical accuracy.",
}
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)

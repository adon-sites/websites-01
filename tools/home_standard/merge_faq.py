#!/usr/bin/env python3
"""merge_faq.py — 이미 홈 기준을 적용한 홈에서 기존 FAQ 묶음을 새 FAQ(#home-faq-own) 뒤에 합쳐 한 군데로 만들고 FAQPage 를 화면과 같게 다시 쓴다. 멱등.
usage: merge_faq.py <도메인> [빼는 기존 질문의 일부 …]"""
import html, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
d = sys.argv[1]; drop = sys.argv[2:]
f = ROOT / 'sites' / d / 'public/index.html'; s = f.read_text(encoding='utf-8')
i = s.find('id="home-faq-own"'); assert i > 0, '새 FAQ 없음'
own = re.compile(r'(<div class="faq">)(.*?)(</div>)', re.S).search(s, i)
olds = [m for m in re.finditer(r'\s*<div class="faq[^"]*">(.*?)</div>', s, re.S) if not (own.start() <= m.start() + len(m.group(0)) - len(m.group(0).lstrip()) <= own.end())]
moved = 0
for m in reversed(olds):
    items = re.findall(r'<details[^>]*>\s*<summary>.*?</summary>\s*<p>.*?</p>\s*</details>', m.group(1), re.S)
    keep = [x for x in items if not any(k in x for k in drop)]
    s = s[:m.start()] + s[m.end():]
    if m.start() < own.start(): own = re.compile(r'(<div class="faq">)(.*?)(</div>)', re.S).search(s, s.find('id="home-faq-own"'))
    s = s[:own.end(2)] + ''.join(keep) + '\n    ' + s[own.end(2):]; moved += len(keep)
    own = re.compile(r'(<div class="faq">)(.*?)(</div>)', re.S).search(s, s.find('id="home-faq-own"'))
T = lambda x: html.unescape(re.sub(r'<[^>]+>', '', x)).strip()
qa = [(T(q), T(a)) for q, a in re.findall(r'<details[^>]*>\s*<summary>(.*?)</summary>\s*<p>(.*?)</p>\s*</details>', own.group(2), re.S)]
ld = {'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in qa]}
s, n = re.subn(r'<script type="application/ld\+json" id="home-faq-schema">.*?</script>', lambda _: '<script type="application/ld+json" id="home-faq-schema">' + json.dumps(ld, ensure_ascii=False).replace('<', '\\u003c') + '</script>', s, flags=re.S)
assert n == 1
f.write_text(s, encoding='utf-8'); print(f'[{d}] 기존 FAQ {moved}문항 합침 → FAQ {len(qa)}개')

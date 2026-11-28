#!/usr/bin/env python3
"""backlink_hook.py — 지정한 기존 글에만 "관련 사이트 안내" 목록 끝에 링크 1개를 더한다 (빌드 출력에만 적용, 멱등).
usage: backlink_hook.py <sites/도메인>
설정: tools/deploy/extra_backlinks.json  {"links":[{"keyword","url","posts":{"<도메인>":["<slug>",…]}}]}
  - 목록에 있는 글(dist/blog/<slug>/index.html)의 <section class="hospital-links publication-backlinks link-bundle">("관련 사이트 안내") 안 </ul> 앞에
    <li><a href="url">keyword</a></li> 를 넣는다. 그 목록이 없는 예전 형식 글은 <section class="hospital-links">("병원 홈페이지 안내") 끝에 넣는다.
    이미 그 url 이 있으면 그대로 둔다.
  - 목록에 없는 글·새로 발행되는 글·목록 밖 사이트는 손대지 않는다. 글 수정일(dateModified)은 올리지 않는다.
  - 실패해도 배포는 계속한다(build_site.py 가 반환값을 보지 않는다).
"""
import json, re, sys, html
from pathlib import Path

site = Path(sys.argv[1]).resolve()
sj = json.loads((site / 'site.json').read_text(encoding='utf-8'))
dom = sj['domain']; out = site / sj['dist']
cfgp = Path(__file__).resolve().parent / 'extra_backlinks.json'
if not cfgp.exists(): sys.exit(0)
cfg = json.loads(cfgp.read_text(encoding='utf-8'))
SEC = re.compile(r'(<section class="hospital-links publication-backlinks link-bundle"[^>]*>.*?)(</ul>\s*</section>)', re.S)
# 예전 형식 글(관련 사이트 안내 목록이 없는 글): '병원 홈페이지 안내' 목록(class="hospital-links" 단독) 끝에 넣는다
SEC_OLD = re.compile(r'(<section class="hospital-links"[^>]*>.*?)(</ul>\s*</section>)', re.S)
added = kept = missing = nosec = 0
for link in cfg.get('links', []):
    kw, url = link['keyword'], link['url']
    li = f'<li><a href="{html.escape(url, quote=True)}">{html.escape(kw)}</a></li>'
    for slug in link.get('posts', {}).get(dom, []):
        p = out / 'blog' / slug / 'index.html'
        if not p.is_file(): missing += 1; continue
        t = p.read_text(encoding='utf-8')
        m = SEC.search(t) or SEC_OLD.search(t)
        if not m: nosec += 1; continue
        if f'href="{url}"' in m.group(1) or f'href="{url.rstrip("/")}"' in m.group(1): kept += 1; continue
        p.write_text(t[:m.end(1)] + li + t[m.end(1):], encoding='utf-8'); added += 1
if added or kept or missing or nosec:
    print(f'[{dom}] 추가 백링크: 넣음 {added} · 이미 있음 {kept} · 글 없음 {missing} · 목록 없음 {nosec}')

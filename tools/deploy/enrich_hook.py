#!/usr/bin/env python3
"""enrich_hook.py — 생성기형(python-generator)·WP형(wpstatic) 사이트의 빌드 출력에서 글 페이지에 형식 보강 v3
(섹션별 비교표·본문 링크·FAQ·해시태그·안내 문단)을 멱등 적용한다. build_site.py 가 빌드 직후 호출.
usage: enrich_hook.py <sites/<도메인> 경로>
설정: tools/deploy/enrich_sites.json (원본 site-ops/tools/enrich/sites.json; post_glob 은 dist 기준 글 페이지 glob).
본문 문장·URL 은 바꾸지 않는다. 이미 보강된 페이지(<!-- enrich:v3 -->)는 건너뛴다."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import enrich_post as E

site = Path(sys.argv[1]).resolve()
sj = json.loads((site / 'site.json').read_text(encoding='utf-8'))
domain = sj['domain']
cfg = json.loads((Path(__file__).resolve().parent / 'enrich_sites.json').read_text(encoding='utf-8'))
me = cfg.get(domain)
if not me or me.get('type') not in ('gen', 'wp', 'mkt') or not me.get('spec') or not me.get('post_glob'):
    print(f'[{domain}] enrich: 대상 아님'); sys.exit(0)
out = site / sj['dist']
done = skipped = 0
for p in sorted(out.glob(me['post_glob'])):
    s = p.read_text(encoding='utf-8')
    slug = p.parent.name if p.name == 'index.html' else p.stem
    new, ch = E.enrich_any(s, cfg, domain, slug, me["spec"])
    if ch: p.write_text(new, encoding='utf-8'); done += 1
    else: skipped += 1
print(f'[{domain}] enrich v3: 보강 {done} · 건너뜀(이미 보강/글 아님) {skipped}')

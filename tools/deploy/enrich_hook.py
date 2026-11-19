#!/usr/bin/env python3
"""enrich_hook.py — 빌드 출력의 글 페이지에 형식 보강 v4 를 멱등 적용하고 글별 이미지 2장을 만든다. build_site.py 가 빌드 직후 호출.
usage: enrich_hook.py <sites/<도메인> 경로>
- 생성기(gen)·WP(wp)·마케팅(mkt): HTML 보강(v3 흔적은 걷어내고 v4) + 이미지
- 정적(sitegen): HTML 은 발행 도구(publish_post)가 이미 보강해 커밋하므로 이미지만 생성(images/enrich/, 커밋하지 않음)
설정: tools/deploy/enrich_sites.json (원본 site-ops/tools/enrich/sites.json). 본문 문장·URL 은 바꾸지 않는다."""
import json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import enrich_post as E

site = Path(sys.argv[1]).resolve()
sj = json.loads((site / 'site.json').read_text(encoding='utf-8'))
domain = sj['domain']
cfg = json.loads((HERE / 'enrich_sites.json').read_text(encoding='utf-8'))
me = cfg.get(domain)
if not me:
    print(f'[{domain}] enrich: 설정 없음 → 건너뜀'); sys.exit(0)
out = site / sj['dist']
glob_pat = me.get('post_glob') or 'journal/*/index.html'
files = sorted(out.glob(glob_pat))
done = skipped = 0
if me.get('type') in ('gen', 'wp', 'mkt'):
    for p in files:
        s = p.read_text(encoding='utf-8')
        new, ch = E.enrich_fit(s, cfg, domain, p.parent.name if p.name == "index.html" else p.stem, me["spec"])
        if ch: p.write_text(new, encoding='utf-8'); done += 1
        else: skipped += 1
    print(f'[{domain}] enrich v4: 보강 {done} · 건너뜀(이미 보강/글 아님) {skipped}')
r = subprocess.run([sys.executable, str(HERE / 'make_images.py'), str(HERE / 'enrich_sites.json'), domain, str(out)] + [str(p) for p in files], capture_output=True, text=True)
print(r.stdout.strip() or r.stderr.strip()[-500:])
sys.exit(r.returncode)

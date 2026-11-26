#!/usr/bin/env python3
"""title_hook.py — 빌드 출력에서 글 제목에 키워드를 넣는다(규칙: title_rules.py). build_site.py 가 빌드 직후, enrich_hook 앞에서 호출.
usage: title_hook.py <sites/<도메인> 경로>
- 병원·업체 사이트: 제목에 사이트 키워드가 없으면 넣는다(구미치아교정 … → 구미치과 치아교정 …).
- 마케팅 사이트: 글마다 주제 키워드를 정하고(content/posts/<slug>.md 의 title·short_title) 제목 첫머리에 둔다. 글별 키워드는 <사이트>/.post_kw.json 에 적어 enrich_hook 이 본문 키워드로 쓴다.
옛 제목이 나오는 모든 곳(글·목록·홈·RSS·JSON-LD)을 한 번에 바꾼다. 커밋본·URL 은 그대로(빌드 출력에만 적용, 멱등).
실패해도 배포는 막지 않는다(제목은 원래대로 올라감)."""
import html, json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import title_rules as T

def variants(x):
    v = [x, html.escape(x, quote=False), html.escape(x, quote=True), html.escape(x, quote=True).replace('&#x27;', '&#39;'), json.dumps(x, ensure_ascii=False)[1:-1], json.dumps(x)[1:-1]]
    out = []
    for a in v:
        if a not in out: out.append(a)
    return out

def main():
    site = Path(sys.argv[1]).resolve()
    sj = json.loads((site / 'site.json').read_text(encoding='utf-8')); domain = sj['domain']
    cfg = json.loads((HERE / 'enrich_sites.json').read_text(encoding='utf-8')); me = cfg.get(domain)
    kwf = site / '.post_kw.json'
    if kwf.exists(): kwf.unlink()
    if not me: print(f'[{domain}] title: 설정 없음'); return
    out = site / sj['dist']; kw = [k.strip() for k in me['keyword'].split('·') if k.strip()][0]
    mkt = me.get('type') == 'mkt' or me.get('group') == 'marketing'
    kw_new = (me.get('keyword_new') or '').strip(); kw_from = me.get('keyword_new_from') or '9999'
    files = sorted(out.glob(me.get('post_glob') or 'journal/*/index.html'))
    pairs = {}; post_kw = {}; tiers = {}
    for p in files:
        slug = p.parent.name if p.name == 'index.html' else p.stem
        s = p.read_text(encoding='utf-8')
        m = re.search(r'<h1\b[^>]*>(.*?)</h1>', s, re.S)
        if not m: continue
        old = html.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip()
        if not old: continue
        if mkt:
            md = site / 'content' / 'posts' / f'{slug}.md'
            fm = md.read_text(encoding='utf-8')[:3000] if md.is_file() else ''
            st = re.search(r'^short_title:\s*(.*)$', fm, re.M); st = st.group(1).strip().strip('"\'') if st else ''
            dm = re.search(r'^date:\s*["\']?([0-9T:+\-]+)', fm, re.M)
            if kw_new and dm and dm.group(1) >= kw_from:
                # 키워드를 바꾼 사이트: 바꾼 시각 이후 글만 새 키워드를 제목 앞에(기존 글 제목은 그대로, 2026-11-26)
                new, k, tier = (old if kw_new in old else f'{kw_new}, {old}'), kw_new, 'new_kw'
            else:
                new, k, tier = T.mkt_title(old, st, kw)
            post_kw[slug] = k; tiers[tier] = tiers.get(tier, 0) + 1
        else:
            new = T.hosp_title(old, kw)
        if new != old: pairs[old] = new
    if mkt: kwf.write_text(json.dumps(post_kw, ensure_ascii=False), encoding='utf-8')
    vmap = {}
    for o, n in pairs.items():
        for a, b in zip(variants(o), variants(n)): vmap.setdefault(a, b)
    keys = sorted(vmap, key=len, reverse=True)
    nfile = nrep = 0
    for p in (out.rglob('*') if pairs else []):
        if not p.is_file() or p.suffix.lower() not in ('.html', '.xml', '.json', '.txt'): continue
        try: s = p.read_text(encoding='utf-8')
        except Exception: continue
        hit = [k for k in keys if k in s]
        if not hit: continue
        rx = re.compile('|'.join(re.escape(k) for k in hit))
        s2, n = rx.subn(lambda m: vmap[m.group(0)], s)
        if n: p.write_text(s2, encoding='utf-8'); nfile += 1; nrep += n
    # <title>·og:title·twitter:title 이 본문 제목과 다른 문구(짧은 메타 제목)라 키워드가 빠져 있으면 새 제목으로 맞춘다
    nmeta = 0
    for p in files:
        s = p.read_text(encoding='utf-8')
        m = re.search(r'<h1\b[^>]*>(.*?)</h1>', s, re.S)
        if not m: continue
        t = html.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip()
        slug = p.parent.name if p.name == 'index.html' else p.stem
        k = post_kw.get(slug, kw) if mkt else kw
        if not t or k not in t: continue
        s2 = s
        mt = re.search(r'<title>(.*?)</title>', s2, re.S)
        if mt and k not in html.unescape(mt.group(1)):
            suf = re.search(r'(\s[|·-]\s[^|·-]+)$', mt.group(1)); s2 = s2[:mt.start(1)] + html.escape(t, quote=False) + (suf.group(1) if suf else '') + s2[mt.end(1):]
        for attr, name in (('property', 'og:title'), ('name', 'twitter:title')):
            mm = re.search(r'(<meta\b[^>]*\b' + attr + '="' + name + r'"[^>]*\bcontent=")([^"]*)(")', s2) or re.search(r'(<meta\b[^>]*\bcontent=")([^"]*)("[^>]*\b' + attr + '="' + name + '")', s2)
            if mm and k not in html.unescape(mm.group(2)): s2 = s2[:mm.start(2)] + html.escape(t, quote=True) + s2[mm.end(2):]
        if s2 != s: p.write_text(s2, encoding='utf-8'); nmeta += 1
    print(f'[{domain}] title: 제목 {len(pairs)}/{len(files)}편 변경 · 메타 제목 {nmeta} · 파일 {nfile} · 치환 {nrep}' + (f' · 단계 {tiers}' if mkt else ''))

if __name__ == '__main__':
    try: main()
    except Exception as e:
        import traceback; traceback.print_exc(); print(f'::warning::title_hook 실패: {e}')

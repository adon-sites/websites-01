#!/usr/bin/env python3
"""mkt_home_hook.py — 애드온 마케팅 사이트 홈 기준 적용(mkt_home.json 에 등록된 도메인만). 빌드 출력에만 적용, 멱등.
usage: mkt_home_hook.py <sites/<도메인> 경로>
  - 홈: title·og:title = '<키워드> | <구절> | 애드온', description·og:description, H1 = '<키워드>, <구절>'
  - 사이트 이름: 모든 페이지 og:site_name = 키워드만, 홈 WebSite name = 키워드만(alternateName 삭제, 병원 사이트 desc_hook 과 같게), WebPage name·description
  - 카드 6장: 카드 제목(h3) = alt = ItemList name. cards[i] 가 null 이면 지금 카드 제목 그대로.
    카드 페이지 6쪽의 대표 이미지 alt(og:image:alt·caption·img alt)도 같은 문구로 맞춘다.
  - title_hook 뒤, cards_hook 앞에서 실행한다(title_hook 이 글 제목 문자열을 전 파일에서 치환하므로 그 뒤에 카드 제목을 확정).
  - 글 제목·본문·주소·이미지 파일은 바꾸지 않는다.
"""
import html, json, re, sys
from pathlib import Path

E = lambda x: html.escape(x, quote=True)


def set_meta(s, attr, key, value):
    tag = f'<meta {attr}="{key}" content="{E(value)}">'
    pat = r'<meta\b(?=[^>]*\b' + attr + r'=["\']' + re.escape(key) + r'["\'])[^>]*>'
    if re.search(pat, s, re.I): return re.sub(pat, lambda _: tag, s, flags=re.I)
    return s.replace('</head>', tag + '</head>', 1)


def main():
    site = Path(sys.argv[1]).resolve()
    sj = json.loads((site / 'site.json').read_text(encoding='utf-8')); domain = sj['domain']
    cfg = json.loads((Path(__file__).resolve().parent / 'mkt_home.json').read_text(encoding='utf-8'))['sites'].get(domain)
    if not cfg or sj.get('group') != 'marketing': print(f'[{domain}] mkt_home: 대상 아님'); return
    out = site / sj['dist']; hf = out / 'index.html'
    kw, phrase, desc = cfg['keyword'], cfg['phrase'], cfg['description']
    title = f'{kw} | {phrase} | 애드온'; h1 = f'{kw}, {phrase}'
    s = hf.read_text(encoding='utf-8')
    s = re.sub(r'<title>.*?</title>', lambda _: '<title>' + E(title) + '</title>', s, count=1, flags=re.S)
    for a, k, v in (('name', 'description', desc), ('property', 'og:title', title), ('property', 'og:description', desc)): s = set_meta(s, a, k, v)
    s, n = re.subn(r'(<h1\b[^>]*>).*?</h1>', lambda m: m[1] + E(h1) + '</h1>', s, count=1, flags=re.S)
    assert n == 1, 'H1 없음'
    # 카드 6장
    grid = re.search(r'<section class="feature-grid[^"]*".*?</section>', s, re.S); assert grid, '카드 영역 없음'
    cards = list(re.finditer(r'<a class="feature" href="([^"]+)">(.*?)</a>', grid[0], re.S)); assert len(cards) == 6, f'카드 {len(cards)}장'
    names = []; pages = []; g = grid[0]
    for i, m in reversed(list(enumerate(cards))):
        block = m[0]
        cur = html.unescape(re.search(r'<h3>(.*?)</h3>', block, re.S)[1])
        new = cfg['cards'][i] or cur
        old_alt = re.search(r'<img\b[^>]*\balt="([^"]*)"', block)[1]
        block = re.sub(r'(<h3>).*?(</h3>)', lambda x: x[1] + E(new) + x[2], block, count=1, flags=re.S)
        block = re.sub(r'(<img\b[^>]*\balt=")[^"]*', lambda x: x[1] + E(new), block, count=1)
        g = g[:m.start()] + block + g[m.end():]
        names.insert(0, new); pages.insert(0, (m[1], old_alt, new))
    s = s[:grid.start()] + g + s[grid.end():]
    def ld(m):
        try: obj = json.loads(m[2])
        except Exception: return m[0]
        t = obj.get('@type') if isinstance(obj, dict) else None
        if t == 'ItemList':
            for it, nm in zip(obj['itemListElement'], names): it['name'] = nm
        elif t == 'WebSite': obj['name'] = kw; obj.pop('alternateName', None)
        elif t == 'WebPage':
            obj['name'] = title; obj['description'] = desc
            for k in ('image', 'primaryImageOfPage'):
                if isinstance(obj.get(k), dict) and 'caption' in obj[k]: obj[k]['caption'] = names[0]
        else: return m[0]
        return m[1] + json.dumps(obj, ensure_ascii=False).replace('<', '\\u003c') + '</script>'
    s = re.sub(r'(<script type="application/ld\+json"[^>]*>)(.*?)</script>', ld, s, flags=re.S)
    s = set_meta(s, 'property', 'og:image:alt', names[0])
    hf.write_text(s, encoding='utf-8')
    # 카드 페이지: 대표 이미지 alt 를 카드 제목과 같게
    fixed = 0
    for href, old_alt, new in pages:
        p = out / href.strip('/') / 'index.html'
        if not p.is_file() or old_alt == E(new): continue
        t = p.read_text(encoding='utf-8'); u = t
        raw = html.unescape(old_alt)
        for o, nn in ((old_alt, E(new)), (json.dumps(raw, ensure_ascii=False)[1:-1], json.dumps(new, ensure_ascii=False)[1:-1])):
            if o: u = u.replace(o, nn)
        if u != t: p.write_text(u, encoding='utf-8'); fixed += 1
    # 사이트 이름: 전 페이지 og:site_name = 키워드만
    sn = 0
    for p in out.rglob('*.html'):
        if p.name == '404.html': continue
        t = p.read_text(encoding='utf-8')
        u = re.sub(r'<meta property="og:site_name" content="[^"]*">', lambda _: f'<meta property="og:site_name" content="{E(kw)}">', t)
        if u != t: p.write_text(u, encoding='utf-8'); sn += 1
    print(f'[{domain}] mkt_home: title {len(title)}자 · description {len(desc)}자 · 카드 제목 6 · 카드 페이지 alt {fixed} · og:site_name {sn}쪽')


if __name__ == '__main__':
    main()

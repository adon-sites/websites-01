#!/usr/bin/env python3
"""seo_hook.py — 빌드 출력(글 페이지)의 태그만 고친다. 본문 문장·제목·키워드 수·홈은 건드리지 않는다. (2026-11-24)
usage: seo_hook.py <sites/<도메인> 경로>
 ① H1 한 번만: 본문 첫머리 제목 반복 <h1 class="enrich-title"> → <p class="enrich-title">(글자 그대로, 굵기 유지)
 ② 수정일: content_rollouts.json 의 롤아웃보다 먼저 게시된 글은 article:modified_time · JSON-LD dateModified ·
    sitemap.xml lastmod 를 실제 수정일로. 게시일(article:published_time·datePublished·<time>)은 그대로.
커밋본은 그대로 두고 빌드 출력에만 적용(멱등). 되돌리려면 build_site.py 의 호출 한 줄만 뺀다.
"""
import json, re, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import unquote

KST = timezone(timedelta(hours=9))
HERE = Path(__file__).resolve().parent
CSS = '<style id="seo-fix-css">p.enrich-title{font-weight:700}</style>'

def norm(u):
    u = unquote(u.strip())
    u = re.sub(r'^https?://[^/]+', '', u)
    u = re.sub(r'(/index)?\.html$', '', u)
    return u.rstrip('/') or '/'

def fmt(dt, like):
    """dt 를 기존 값(like)과 같은 꼴로."""
    like = (like or '').strip()
    if len(like) <= 10: return dt.astimezone(KST).strftime('%Y-%m-%d')
    if like.endswith('Z'): return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    return dt.astimezone(KST).isoformat(timespec='seconds')

def day(v):
    m = re.match(r'\d{4}-\d{2}-\d{2}', (v or '').strip())
    return m.group(0) if m else ''

def published(s):
    for pat in (r'<meta property="article:published_time" content="([^"]*)"', r'"datePublished":\s*"([^"]*)"', r'<time[^>]*datetime="([^"]*)"'):
        m = re.search(pat, s)
        if m and day(m.group(1)): return m.group(1)
    return ''

def main():
    site = Path(sys.argv[1]).resolve()
    sj = json.loads((site / 'site.json').read_text(encoding='utf-8'))
    out = site / sj['dist']; domain = sj['domain']
    cfg = json.loads((HERE / 'content_rollouts.json').read_text(encoding='utf-8'))
    no_dates = domain in cfg.get('exclude_domains', [])   # 이 사이트는 날짜·사이트맵을 그대로 둔다(H1 정리만)
    rolls = [] if no_dates else [(r['published_before'], datetime.fromisoformat(r['modified'])) for r in cfg['rollouts']]
    sm_path = out / 'sitemap.xml'
    sm = sm_path.read_text(encoding='utf-8') if sm_path.exists() else ''
    sm_last = {norm(l): d for l, d in re.findall(r'<loc>\s*([^<\s]+)\s*</loc>\s*<lastmod>\s*([^<\s]+)\s*</lastmod>', sm)}
    md_date = {}
    for mdp in (site / 'content' / 'posts').glob('*.md') if (site / 'content' / 'posts').is_dir() else []:
        try: m = re.search(r'^date:\s*["\']?([0-9T:+\-Z.]+)', mdp.read_text(encoding='utf-8')[:1500], re.M)
        except Exception: m = None
        if m: md_date[mdp.stem] = m.group(1)
    n_h1 = n_mod = 0; newmod = {}; pubday = {}
    for p in out.rglob('*.html'):
        try: s = p.read_text(encoding='utf-8')
        except Exception: continue
        if 'class="enrich-title"' not in s: continue
        o = s
        # ① H1 한 번만
        s, k = re.subn(r'<h1 class="enrich-title">(.*?)</h1>', r'<p class="enrich-title">\1</p>', s, flags=re.S)
        if k:
            n_h1 += 1
            if 'id="seo-fix-css"' not in s and '</head>' in s: s = s.replace('</head>', CSS + '</head>', 1)
        # ② 수정일
        url = norm('/' + p.relative_to(out).as_posix())
        pub = published(s) or md_date.get(url.rsplit('/', 1)[-1], '') or sm_last.get(url, '')
        if day(pub): pubday[url] = day(pub)
        mod = None
        for before, dt in rolls:
            # 게시일을 알 수 없는 글 = 날짜 표기가 없던 초기 이관 글 → 롤아웃 이전 글로 본다
            if (not day(pub) or day(pub) < before) and (mod is None or dt > mod): mod = dt
        if mod:
            md = mod.astimezone(KST).strftime('%Y-%m-%d')
            def up(m):
                return m.group(1) + (fmt(mod, m.group(2)) if day(m.group(2)) < md else m.group(2)) + m.group(3)
            s = re.sub(r'(<meta property="article:modified_time" content=")([^"]*)(")', up, s)
            s = re.sub(r'("dateModified":\s*")([^"]*)(")', up, s)
            if 'article:modified_time' not in s and '</head>' in s:
                tag = f'<meta property="article:modified_time" content="{fmt(mod, pub if "article:published_time" in s else "T")}">'
                a = re.search(r'<meta property="article:published_time"[^>]*>', s)
                s = s[:a.end()] + '\n' + tag + s[a.end():] if a else s.replace('</head>', tag + '</head>', 1)
            if '"datePublished"' in s and '"dateModified"' not in s:
                s = re.sub(r'("datePublished":(\s*)"([^"]*)")', lambda m: m.group(1) + ',' + m.group(2) + '"dateModified":' + m.group(2) + '"' + fmt(mod, m.group(3)) + '"', s, count=1)
            newmod[url] = mod; n_mod += 1
        if s != o: p.write_text(s, encoding='utf-8')
    n_sm = n_add = 0
    if sm and not no_dates and (newmod or pubday):
        def sub(m):
            nonlocal n_sm, n_add
            blk = m.group(0)
            loc = re.search(r'<loc>\s*([^<\s]+)\s*</loc>', blk)
            if not loc: return blk
            u = norm(loc.group(1).replace('&amp;', '&')); mod = newmod.get(u)
            want = mod.astimezone(KST).strftime('%Y-%m-%d') if mod else pubday.get(u, '')
            if not want: return blk
            lm = re.search(r'(<lastmod>\s*)([^<\s]+)(\s*</lastmod>)', blk)
            if lm:
                if not mod or day(lm.group(2)) >= want: return blk
                n_sm += 1
                return blk[:lm.start()] + lm.group(1) + fmt(mod, lm.group(2)) + lm.group(3) + blk[lm.end():]
            n_add += 1
            return blk[:loc.end()] + f'<lastmod>{want}</lastmod>' + blk[loc.end():]
        sm2 = re.sub(r'<url>.*?</url>', sub, sm, flags=re.S)
        if sm2 != sm: sm_path.write_text(sm2, encoding='utf-8')
    if no_dates: print(f'[{domain}] seo: 수정일 반영 제외 사이트(날짜·사이트맵 그대로)')
    print(f'[{domain}] seo: H1 정리 {n_h1}편 · 수정일 반영 {n_mod}편 · sitemap lastmod 수정 {n_sm}건·추가 {n_add}건')

if __name__ == '__main__':
    main()

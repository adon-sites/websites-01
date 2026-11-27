#!/usr/bin/env python3
"""live_probe.py — 실제 주소 점검(읽기 전용). usage: live_probe.py <도메인,도메인,…|all>
사이트마다: /favicon.ico 응답(상태·종류·크기·앞 4바이트), 없는 파일 요청의 응답, 홈의 <link rel=icon>, sitemap 에서 고른 글 8편의 H1 개수. 결과는 한 줄 JSON."""
import json, re, sys, glob, os, urllib.request, urllib.parse
UA = {'User-Agent': 'Mozilla/5.0 (compatible; adon-livecheck/1.0)', 'Cache-Control': 'no-cache'}
XR = {}
def get(url):
    url0 = url
    try:
        u = urllib.parse.urlsplit(url); url = urllib.parse.urlunsplit((u.scheme, u.netloc, urllib.parse.quote(urllib.parse.unquote(u.path)), u.query, ''))
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            XR[url0] = r.headers.get('x-robots-tag', '') or ''; return r.status, r.read(), r.headers.get('content-type', '')
    except urllib.error.HTTPError as e: return e.code, (e.read() or b''), e.headers.get('content-type', '')
    except Exception as e: return 0, str(e).encode(), ''
MODE = sys.argv[2] if len(sys.argv) > 2 else ''
def main():
    arg = sys.argv[1]
    doms = sorted(os.path.basename(os.path.dirname(f)) for f in glob.glob('sites/*/site.json')) if arg == 'all' else [d.strip() for d in arg.split(',') if d.strip()]
    for d in doms:
        o = {'d': d}
        st, b, ct = get(f'https://{d}/favicon.ico'); o['fav'] = [st, ct.split(';')[0], len(b), b[:4].hex(), b'<html' in b[:600].lower() or b'<!doctype' in b[:200].lower()]
        st, b, ct = get(f'https://{d}/zz-not-exist-9x.png'); o['missing'] = [st, ct.split(';')[0], len(b)]
        st, b, ct = get(f'https://{d}/'); home = b.decode('utf-8', 'replace')
        o['icon_link'] = [(re.search(r'href="([^"]+)"', x) or [0, ''])[1] for x in re.findall(r'<link[^>]+rel="[^"]*icon[^"]*"[^>]*>', home, re.I)][:3]
        st, b, ct = get(f'https://{d}/sitemap.xml'); locs = re.findall(r'<loc>([^<]+)</loc>', b.decode('utf-8', 'replace'))
        posts = [u for u in locs if re.search(r'/(journal|blog)/[^/]+/?$', u)] or [u for u in locs if urllib.parse.urlsplit(u).path.strip('/').count('/') == 0 and urllib.parse.urlsplit(u).path.strip('/')]
        step = max(1, len(posts) // 8); pick = posts[::step][:8]; h1 = []
        for u in pick:
            st, b, ct = get(u); h1.append(len(re.findall(rb'<h1[\s>]', b, re.I)) if st == 200 else -st)
        o['posts'] = len(posts); o['h1'] = h1
        if MODE == 'robots':   # 홈·카드 6쪽(홈 ItemList)·글 표본의 meta robots 와 X-Robots-Tag 에 noindex 가 있는지
            cards = []
            for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', home, re.S):
                try: j = json.loads(m.group(1))
                except Exception: continue
                st_ = [j]
                while st_:
                    x = st_.pop()
                    if isinstance(x, list): st_ += x
                    elif isinstance(x, dict):
                        if x.get('@type') == 'ListItem' and (x.get('url') or (isinstance(x.get('item'), dict) and x['item'].get('url')) or isinstance(x.get('item'), str)):
                            cards.append(x.get('url') or (x['item'] if isinstance(x['item'], str) else x['item'].get('url')))
                        st_ += list(x.values())
            cards = [c for c in dict.fromkeys(cards) if c.startswith('http') and d in c][:6]
            step = max(1, len(posts) // 40); sample = posts[::step][:40] + posts[-3:]
            def chk(u):
                st, b, ct = get(u); t = b[:30000].decode('utf-8', 'replace'); m = re.search(r'<meta[^>]+name=["\']robots["\'][^>]*>', t, re.I)
                meta = (re.search(r'content=["\']([^"\']*)', m.group(0)) or [0, ''])[1] if m else ''
                return st, meta, XR.get(u, '')
            bad = []; seen = {'home': chk(f'https://{d}/')}
            for kind, us in (('card', cards), ('post', sample)):
                for u in us:
                    r = chk(u)
                    if r[0] != 200 or 'noindex' in (r[1] + r[2]).lower(): bad.append([kind, u, r])
            if 'noindex' in (seen['home'][1] + seen['home'][2]).lower() or seen['home'][0] != 200: bad.append(['home', f'https://{d}/', seen['home']])
            o['robots'] = {'home': seen['home'], 'cards': len(cards), 'posts_checked': len(dict.fromkeys(sample)), 'bad': bad[:10], 'bad_n': len(bad)}
        print('PROBE ' + json.dumps(o, ensure_ascii=False))
if __name__ == '__main__': main()

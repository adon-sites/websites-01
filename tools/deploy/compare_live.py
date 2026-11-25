#!/usr/bin/env python3
"""compare_live.py — 저장소에서 빌드한 출력과 실제 사이트 응답을 대조만 한다(업로드·수정 없음, 항상 exit 0).
usage: compare_live.py --host <도메인> --out <출력 폴더> [--posts 20]
  대조: 홈(/) + sitemap.xml 에서 lastmod 가 가장 최근인 글 N편(journal|blog|articles, 없으면 맨 뒤 N개).
  결과 한 줄(JSON)을 COMPARE= 로 출력하고 Actions 에서는 ::notice 로 남긴다.
"""
import argparse, hashlib, json, os, re, urllib.parse
import requests


def lp(out, p):
    p = urllib.parse.unquote(p)
    if p.endswith('/'): p += 'index.html'
    f = os.path.join(out, p.lstrip('/'))
    return f if os.path.isfile(f) else (f + '.html' if os.path.isfile(f + '.html') else None)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--host', required=True); ap.add_argument('--out', required=True); ap.add_argument('--posts', type=int, default=20)
    a = ap.parse_args(); base = 'https://' + a.host.lower(); out = a.out
    posts = []
    sm = os.path.join(out, 'sitemap.xml')
    if os.path.isfile(sm):
        x = open(sm, encoding='utf-8').read()
        ent = re.findall(r'<url>\s*<loc>(.*?)</loc>(?:\s*<lastmod>(.*?)</lastmod>)?', x, re.S)
        ps = [(lm or '', i, urllib.parse.urlparse(l).path) for i, (l, lm) in enumerate(ent) if re.search(r'/(journal|blog|articles)/[^/]+/?$', l) or re.search(r'/\d{4}/\d{2}/\d{2}/[^/]+/?$', l)]
        if not ps: ps = [(lm or '', i, urllib.parse.urlparse(l).path) for i, (l, lm) in enumerate(ent) if urllib.parse.urlparse(l).path.count('/') >= 2 and urllib.parse.urlparse(l).path != '/']
        posts = [p for _, _, p in sorted(ps, reverse=True)[:a.posts]]
    s = requests.Session(); s.headers['User-Agent'] = 'adon-verify/1'
    def cmp(u):
        f = lp(out, u)
        if not f: return 'nolocal', ''
        try: r = s.get(base + urllib.parse.quote(u, safe='/%'), timeout=30, allow_redirects=False, headers={'Cache-Control': 'no-cache'})
        except Exception as e: return 'error', str(e)[:60]
        if r.status_code != 200: return str(r.status_code), ''
        return ('same', '') if hashlib.sha256(r.content).hexdigest() == hashlib.sha256(open(f, 'rb').read()).hexdigest() else ('diff', f'live {len(r.content)}B / repo {os.path.getsize(f)}B')
    home = cmp('/'); res = [(u,) + cmp(u) for u in posts]
    bad = [f'{u} {st} {d}'.strip() for u, st, d in res if st != 'same']
    summary = {'host': a.host, 'home': home[0], 'home_detail': home[1], 'posts': len(res), 'posts_same': sum(1 for r in res if r[1] == 'same'), 'bad': bad[:20]}
    line = json.dumps(summary, ensure_ascii=False)
    print('COMPARE=' + line)
    if os.environ.get('GITHUB_ACTIONS'): print('::notice::COMPARE ' + line)


if __name__ == '__main__':
    main()

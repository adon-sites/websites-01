#!/usr/bin/env python3
"""verify_live.py — 업로드한 출력 폴더와 실제 응답(https)을 대조한다. Actions 에서 실행하면 결과를 ::notice/::error 로도 남긴다.
usage: verify_live.py --host <도메인> --out <출력 폴더> [--base <URL 기준>]
  --base 생략: https://<host>  (DNS 전환 후)
  --base https://static-host-01.<sub>.workers.dev/<host>  (라우트 전 preview; 서브도메인은 CLOUDFLARE 토큰으로 /accounts/{id}/workers/subdomain 조회 가능)
검사 URL: 홈 / robots.txt / sitemap.xml / rss.xml / 404 / 홈 ItemList 의 url 전부(허브 6) / 홈 og:image / 글 1편(sitemap 의 마지막 journal|blog URL) / 그 글의 og:image
각 URL: status 200 + 본문 sha256 == 로컬 파일 sha256 (리다이렉트 301 은 따라가지 않고 Location 만 기록). 하나라도 틀리면 exit 1.
"""
import argparse, hashlib, json, os, re, sys, urllib.parse
import requests

def note(level, msg):
    print(msg);
    if os.environ.get('GITHUB_ACTIONS'): print(f'::{level}::{msg}')

def local_path(out, url_path):
    p = urllib.parse.unquote(url_path)
    if p.endswith('/'): p += 'index.html'
    f = os.path.join(out, p.lstrip('/'))
    if os.path.isfile(f): return f
    if not os.path.splitext(p)[1] and os.path.isfile(f + '.html'): return f + '.html'
    return None

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--host', required=True); ap.add_argument('--out', required=True); ap.add_argument('--base', default=''); ap.add_argument('--list', action='store_true')
    a = ap.parse_args(); host = a.host.lower(); out = a.out; base = (a.base or f'https://{host}').rstrip('/')
    home = open(os.path.join(out, 'index.html'), encoding='utf-8', errors='replace').read()
    urls = ['/', '/robots.txt', '/sitemap.xml', '/rss.xml']
    # ItemList urls + og:image from home
    for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', home, re.S):
        try: data = json.loads(m.group(1))
        except Exception: continue
        nodes = data if isinstance(data, list) else [data]
        for n in nodes:
            for g in ([n] + n.get('@graph', [])) if isinstance(n, dict) else []:
                if isinstance(g, dict) and g.get('@type') == 'ItemList':
                    for it in g.get('itemListElement', []):
                        u = it.get('url') or (it.get('item') or {}).get('url') if isinstance(it, dict) else None
                        if u: urls.append(urllib.parse.urlparse(u).path)
    og = re.search(r'<meta property="og:image" content="([^"]+)"', home)
    if og: urls.append(urllib.parse.urlparse(og.group(1)).path)
    sm = os.path.join(out, 'sitemap.xml')
    if os.path.isfile(sm):
        locs = re.findall(r'<loc>(.*?)</loc>', open(sm, encoding='utf-8').read())
        posts = [l for l in locs if re.search(r'/(journal|blog|articles)/[^/]+/?$', l)]
        if posts:
            pp = urllib.parse.urlparse(posts[-1]).path; urls.append(pp)
            pf = local_path(out, pp)
            if pf:
                pog = re.search(r'<meta property="og:image" content="([^"]+)"', open(pf, encoding='utf-8', errors='replace').read())
                if pog: urls.append(urllib.parse.urlparse(pog.group(1)).path)
    seen = []; [seen.append(u) for u in urls if u not in seen]
    if a.list: print('\n'.join(seen)); return
    bad = 0; s = requests.Session(); s.headers['User-Agent'] = 'adon-verify/1'
    for u in seen:
        lf = local_path(out, u)
        r = None
        for attempt in range(3):  # 일시적 연결 끊김은 재시도
            try:
                r = s.get(base + urllib.parse.quote(u, safe='/%'), timeout=30, allow_redirects=False, headers={'Cache-Control': 'no-cache'}); break
            except Exception as e:
                err = e; import time as _t; _t.sleep(2 * (attempt + 1))
        if r is None: note('error', f'[{host}] {u} → 요청 실패(3회) {err}'); bad += 1; continue
        if r.status_code in (301, 302): note('warning', f'[{host}] {u} → {r.status_code} {r.headers.get("location")}'); continue
        if r.status_code == 404 and lf is None: note('warning', f'[{host}] {u} → 404 (출력 폴더에도 없는 파일 — 기존 사이트와 같은 깨진 참조)'); continue
        if r.status_code != 200: note('error', f'[{host}] {u} → {r.status_code}'); bad += 1; continue
        if lf is None: note('warning', f'[{host}] {u} → 200 (로컬 파일 없어 해시 비교 생략)'); continue
        same = hashlib.sha256(r.content).hexdigest() == hashlib.sha256(open(lf, 'rb').read()).hexdigest()
        ct = r.headers.get('content-type', ''); cc = r.headers.get('cache-control', '')
        if same: print(f'ok   {u} 200 {ct} [{cc}]')
        else: note('error', f'[{host}] {u} → 200 이지만 본문 해시 불일치 ({len(r.content)}B vs 로컬 {os.path.getsize(lf)}B)'); bad += 1
    try:
        r404 = s.get(base + '/__no_such_page__/', timeout=30, allow_redirects=False)
        if r404.status_code == 404: print(f'ok   /__no_such_page__/ 404 ({len(r404.content)}B)')
        else: note('error', f'[{host}] 404 확인 실패: {r404.status_code}'); bad += 1
    except Exception as e: note('error', f'[{host}] 404 확인 요청 실패 {e}'); bad += 1
    note('error' if bad else 'notice', f'[{host}] live 확인 {base}: {len(seen) + 1} URL 중 불일치 {bad}')
    sys.exit(1 if bad else 0)

if __name__ == '__main__': main()

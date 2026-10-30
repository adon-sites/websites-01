#!/usr/bin/env python3
"""add_zone.py — 도메인 1곳을 Worker 호스팅으로 붙이는 Cloudflare API 절차 (SCALE_DESIGN §4). GitHub Actions 등 API 가 닿는 곳에서 실행.
usage: add_zone.py <도메인> [--worker static-host-01] [--create-zone] [--dns] [--route] [--all]
env:   CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID
  --create-zone : 이 계정에 존 추가(full) → 배정된 네임서버 출력(등록기관에서 바꾸는 건 사람)
  --dns         : A @ 192.0.2.1 proxied (더미) + CNAME www → @ proxied (이미 있으면 유지)
  --route       : Workers 라우트 `<도메인>/*` 와 `www.<도메인>/*` → <worker>
  --all         : 위 셋 순서대로.  존이 아직 active 가 아니면 --route 는 실패할 수 있다(네임서버 반영 후 재실행).
주의: Worker 라우트는 존과 같은 계정에만 붙는다. 다른 Cloudflare 계정(naver/gmail)에 있는 존은 이 계정에 다시 추가(이전)해야 한다.
(2026-10-28 작성, 세션에서 API 호출 불가 → 미실행·미검증)
"""
import argparse, os, sys, requests

API = 'https://api.cloudflare.com/client/v4'
tok = os.environ.get('CLOUDFLARE_API_TOKEN'); acct = os.environ.get('CLOUDFLARE_ACCOUNT_ID')
S = requests.Session(); S.headers['Authorization'] = f'Bearer {tok}'

def call(method, path, **kw):
    r = S.request(method, API + path, **kw); j = r.json()
    if not j.get('success'): raise SystemExit(f'{method} {path} → {j.get("errors")}')
    return j['result']

def zone(domain):
    res = call('GET', '/zones', params={'name': domain})
    return res[0] if res else None

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('domain'); ap.add_argument('--worker', default='static-host-01')
    for f in ('create-zone', 'dns', 'route', 'all'): ap.add_argument('--' + f, action='store_true')
    a = ap.parse_args(); d = a.domain.lower()
    if not (tok and acct): sys.exit('CLOUDFLARE_API_TOKEN / CLOUDFLARE_ACCOUNT_ID 필요')
    z = zone(d)
    if a.create_zone or a.all:
        if z: print(f'존 이미 있음: {d} status={z["status"]} ns={z.get("name_servers")}')
        else:
            z = call('POST', '/zones', json={'name': d, 'account': {'id': acct}, 'type': 'full'})
            print(f'존 추가됨: {d} → 등록기관 네임서버를 이렇게 바꾸세요: {z.get("name_servers")}')
    if not z: sys.exit(f'존 없음: {d} (--create-zone 먼저)')
    zid = z['id']
    if a.dns or a.all:
        recs = call('GET', f'/zones/{zid}/dns_records', params={'per_page': 200})
        have = {(r['type'], r['name']) for r in recs}
        if ('A', d) not in have and ('AAAA', d) not in have and ('CNAME', d) not in have:
            call('POST', f'/zones/{zid}/dns_records', json={'type': 'A', 'name': '@', 'content': '192.0.2.1', 'proxied': True, 'ttl': 1}); print('DNS A @ 192.0.2.1 proxied 추가')
        else: print('DNS @ 레코드 이미 있음 — 유지 (전환 때 Pages CNAME 을 지우고 A 192.0.2.1 proxied 로 바꿀 것)')
        if ('CNAME', 'www.' + d) not in have and ('A', 'www.' + d) not in have:
            call('POST', f'/zones/{zid}/dns_records', json={'type': 'CNAME', 'name': 'www', 'content': d, 'proxied': True, 'ttl': 1}); print('DNS CNAME www 추가')
    if a.route or a.all:
        routes = call('GET', f'/zones/{zid}/workers/routes')
        have = {r['pattern']: r for r in routes}
        for pat in (f'{d}/*', f'www.{d}/*'):
            if pat in have:
                if have[pat].get('script') != a.worker:
                    call('PUT', f'/zones/{zid}/workers/routes/{have[pat]["id"]}', json={'pattern': pat, 'script': a.worker}); print(f'라우트 갱신 {pat} → {a.worker}')
                else: print(f'라우트 이미 있음 {pat}')
            else:
                call('POST', f'/zones/{zid}/workers/routes', json={'pattern': pat, 'script': a.worker}); print(f'라우트 추가 {pat} → {a.worker}')
    print(f'완료: {d} status={z["status"]}')

if __name__ == '__main__': main()

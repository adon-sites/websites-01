#!/usr/bin/env python3
"""r2_sync.py — 빌드 출력 폴더를 R2 `sites/<host>/` 로 동기화 (GitHub Actions 에서 실행; SCALE_DESIGN §5)

usage: r2_sync.py --host <도메인> --out <출력 폴더> [--bucket sites] [--dry-run] [--no-purge] [--check-live]
env:   CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID  (Actions Secrets)

순서: ① 출력 폴더 검사(0바이트·빈 HTML·index.html 유무 → 하나라도 걸리면 업로드 없이 exit 2)
      ② 로컬 manifest(sha256) 계산 → R2 의 sites/<host>/manifest.json 과 비교
      ③ 바뀐/새 파일만 PUT, 사라진 파일 DELETE (병렬 16)
      ④ manifest.json 업로드
      ⑤ 바뀐 html/xml/txt URL 만 Cloudflare 캐시 purge (존이 이 계정에 있을 때만; 없으면 건너뛰고 알림)
      ⑥ --check-live: 바뀐 HTML URL 을 https 로 받아 업로드한 해시와 같은지 확인(전환 전엔 Pages 가 응답하므로 경고만)
멱등: 같은 출력이면 ③④ 는 0건.  --dry-run: API 호출 없이 계획만 출력.
R2 객체 REST API: PUT/GET/DELETE /accounts/{account}/r2/buckets/{bucket}/objects/{key}
"""
import argparse, hashlib, json, mimetypes, os, sys, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests

API = 'https://api.cloudflare.com/client/v4'
TYPES = {'.html': 'text/html; charset=utf-8', '.xml': 'application/xml; charset=utf-8', '.txt': 'text/plain; charset=utf-8',
         '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8',
         '.svg': 'image/svg+xml', '.webp': 'image/webp', '.avif': 'image/avif', '.ico': 'image/x-icon', '.woff2': 'font/woff2', '.woff': 'font/woff',
         '.webmanifest': 'application/manifest+json'}
PURGE_EXT = {'.html', '.xml', '.txt', '.json'}
SKIP_NAMES = {'.DS_Store', 'Thumbs.db', '.nojekyll'}  # .nojekyll 은 GitHub Pages 전용 0바이트 표식 → 업로드 대상 아님


def note(level, msg):
    print(msg)
    if os.environ.get('GITHUB_ACTIONS'): print(f'::{level}::{msg}')


def ctype(p: Path):
    return TYPES.get(p.suffix.lower()) or mimetypes.guess_type(str(p))[0] or 'application/octet-stream'


def local_manifest(out: Path):
    m = {}
    for p in sorted(out.rglob('*')):
        if not p.is_file() or p.name in SKIP_NAMES or '__pycache__' in p.parts: continue
        rel = p.relative_to(out).as_posix()
        m[rel] = {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'size': p.stat().st_size}
    return m


def sanity(out: Path, m: dict):
    """0바이트, <html 없는 .html, index.html 부재 → 오류 목록"""
    errs = []
    if 'index.html' not in m: errs.append('index.html 없음')
    for rel, v in m.items():
        if v['size'] == 0: errs.append(f'0바이트: {rel}')
        elif rel.endswith('.html'):
            head = (out / rel).read_bytes()[:4096].lower()
            if b'<html' not in head: errs.append(f'빈 HTML(<html 없음): {rel}')
    return errs


class R2:
    def __init__(self, account, bucket, token):
        self.base = f'{API}/accounts/{account}/r2/buckets/{bucket}/objects/'
        self.s = requests.Session(); self.s.headers['Authorization'] = f'Bearer {token}'
        self.account = account; self.token = token

    def url(self, key): return self.base + urllib.parse.quote(key, safe='/')

    def _retry(self, fn, tries=4):
        for i in range(tries):
            r = fn()
            if r.status_code < 500 and r.status_code != 429: return r
            time.sleep(1.5 * (i + 1))
        return r

    def get(self, key):
        r = self._retry(lambda: self.s.get(self.url(key)))
        return r.content if r.status_code == 200 else None

    def put(self, key, data: bytes, content_type):
        r = self._retry(lambda: self.s.put(self.url(key), data=data, headers={'Content-Type': content_type}))
        if r.status_code not in (200, 201): raise RuntimeError(f'PUT {key} → {r.status_code} {r.text[:200]}')

    def delete(self, key):
        r = self._retry(lambda: self.s.delete(self.url(key)))
        if r.status_code not in (200, 204, 404): raise RuntimeError(f'DELETE {key} → {r.status_code} {r.text[:200]}')

    def zone_id(self, host):
        r = self.s.get(f'{API}/zones', params={'name': host, 'status': 'active'})
        res = r.json().get('result') or []
        return res[0]['id'] if res else None

    def purge(self, zone, urls):
        for i in range(0, len(urls), 30):  # 요청당 30 URL (Free 플랜 한도)
            r = self._retry(lambda: self.s.post(f'{API}/zones/{zone}/purge_cache', json={'files': urls[i:i + 30]}))
            if r.status_code != 200: raise RuntimeError(f'purge → {r.status_code} {r.text[:200]}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', required=True); ap.add_argument('--out', required=True); ap.add_argument('--bucket', default='sites')
    ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--no-purge', action='store_true'); ap.add_argument('--check-live', action='store_true')
    ap.add_argument('--workers', type=int, default=16)
    a = ap.parse_args()
    out = Path(a.out).resolve(); host = a.host.lower(); prefix = f'sites/{host}/'
    if not out.is_dir(): print(f'출력 폴더 없음: {out}'); sys.exit(2)

    m = local_manifest(out)
    errs = sanity(out, m)
    if errs:
        note('error', f'[{host}] 출력 검사 실패 {len(errs)}건 — 업로드 중단: ' + '; '.join(errs[:5])); [print('  -', e) for e in errs[:30]]; sys.exit(2)
    print(f'[{host}] 로컬 파일 {len(m)}개, 검사 통과')

    token = os.environ.get('CLOUDFLARE_API_TOKEN'); account = os.environ.get('CLOUDFLARE_ACCOUNT_ID')
    if not a.dry_run and not (token and account):
        print('CLOUDFLARE_API_TOKEN / CLOUDFLARE_ACCOUNT_ID 가 없습니다 (Actions Secrets)'); sys.exit(2)
    r2 = None if a.dry_run else R2(account, a.bucket, token)

    old = {}
    if r2:
        raw = r2.get(prefix + 'manifest.json')
        if raw:
            try: old = json.loads(raw).get('files', {})
            except Exception: old = {}
    changed = [k for k, v in m.items() if old.get(k, {}).get('sha256') != v['sha256']]
    removed = [k for k in old if k not in m]
    print(f'[{host}] 변경/신규 {len(changed)}개, 삭제 {len(removed)}개, 유지 {len(m) - len(changed)}개' + (' (dry-run: R2 manifest 미조회)' if a.dry_run else ''))
    if a.dry_run:
        for k in changed[:20]: print('  +', k)
        for k in removed[:20]: print('  -', k)
        return

    failures = []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(r2.put, prefix + k, (out / k).read_bytes(), ctype(out / k)): ('put', k) for k in changed}
        futs.update({ex.submit(r2.delete, prefix + k): ('del', k) for k in removed})
        done = 0
        for f in as_completed(futs):
            op, k = futs[f]
            try: f.result(); done += 1
            except Exception as e: failures.append(f'{op} {k}: {e}')
            if done % 200 == 0: print(f'  … {done}/{len(futs)}')
    if failures:
        note('error', f'[{host}] 업로드 실패 {len(failures)}건 — manifest 갱신 안 함: ' + '; '.join(failures[:3])); [print('  -', x) for x in failures[:20]]; sys.exit(1)

    manifest = {'host': host, 'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'commit': os.environ.get('GITHUB_SHA', ''), 'files': m}
    r2.put(prefix + 'manifest.json', json.dumps(manifest, ensure_ascii=False).encode(), 'application/json; charset=utf-8')
    note('notice', f'[{host}] 파일 {len(m)}개 검사 통과 · 업로드 {len(changed)} · 삭제 {len(removed)} · 유지 {len(m) - len(changed)} · manifest 갱신 ({os.environ.get("GITHUB_SHA", "")[:7]})')

    purge_keys = [k for k in changed + removed if Path(k).suffix.lower() in PURGE_EXT]
    urls = []
    for k in purge_keys:
        p = '/' + k
        if p.endswith('/index.html'): p = p[:-len('index.html')]
        elif p == '/index.html': p = '/'
        urls.append(f'https://{host}' + urllib.parse.quote(p, safe='/'))
    if urls and not a.no_purge:
        zone = r2.zone_id(host)
        if zone: r2.purge(zone, urls); note('notice', f'[{host}] purge {len(urls)} URL')
        else: note('notice', f'[{host}] 존이 이 계정에 없어 purge 생략 ({len(urls)} URL)')

    if a.check_live and changed:
        bad = 0
        for k in [k for k in changed if k.endswith('.html')][:50]:
            p = '/' + k; p = p[:-len('index.html')] if p.endswith('/index.html') else p
            try:
                r = requests.get(f'https://{host}' + urllib.parse.quote(p, safe='/'), timeout=20, headers={'Cache-Control': 'no-cache'})
                ok = r.status_code == 200 and hashlib.sha256(r.content).hexdigest() == m[k]['sha256']
            except Exception as e: ok = False; r = None
            if not ok: bad += 1; print(f'  live 불일치: {p} ({r.status_code if r is not None else "err"})')
        print(f'[{host}] live 확인: 불일치 {bad}건 (전환 전이면 Pages 응답이라 정상)')


if __name__ == '__main__':
    main()

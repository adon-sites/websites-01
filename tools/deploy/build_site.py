#!/usr/bin/env python3
"""build_site.py — websites-NN/sites/<도메인>/ 을 site.json 의 builder 대로 빌드하고 출력 폴더 경로를 출력한다.
usage: build_site.py <sites/<도메인> 경로>   → stdout 마지막 줄: OUT=<출력 폴더 절대경로>
  python-generator : dist/ 비움 → static/ 복사 → site.json build 실행 → dist/
  static           : 빌드 없음 → public/ (site.json dist)
  wpstatic         : site.json build 를 제자리에서 실행(멱등 후처리) → site.json dist (public|docs)
  모든 builder: 빌드 뒤 enrich_hook.py — 생성기·WP·마케팅은 글 형식 보강 v4(멱등) + 글별 이미지 2장, 정적은 이미지만(images/enrich/)
빌드가 0 이 아니면 그대로 exit (워크플로 실패).
"""
import json, shutil, subprocess, sys
from pathlib import Path

site = Path(sys.argv[1]).resolve()
sj = json.loads((site / 'site.json').read_text(encoding='utf-8'))
builder = sj.get('builder'); out = site / sj['dist']
if builder == 'python-generator':
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    st = site / sj.get('static_dir', 'static')
    n = 0
    if st.exists():
        for p in st.rglob('*'):
            if p.is_file():
                d = out / p.relative_to(st); d.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, d); n += 1
    print(f'[{sj["domain"]}] static {n}개 복사 → {sj["dist"]}/; build: {sj["build"]}')
    r = subprocess.run(sj['build'], shell=True, cwd=site)
    if r.returncode: print(f'[{sj["domain"]}] 빌드 실패 exit {r.returncode}'); sys.exit(r.returncode)
elif builder == 'static':
    print(f'[{sj["domain"]}] 정적 사이트, 빌드 없음 → {sj["dist"]}/')
elif builder == 'wpstatic':
    print(f'[{sj["domain"]}] wpstatic 후처리: {sj["build"]} (제자리, {sj["dist"]}/)')
    r = subprocess.run(sj['build'], shell=True, cwd=site)
    if r.returncode: print(f'[{sj["domain"]}] 후처리 실패 exit {r.returncode}'); sys.exit(r.returncode)
else:
    print(f'알 수 없는 builder: {builder}'); sys.exit(2)
if builder in ('python-generator', 'wpstatic', 'static'):
    # 글 제목에 키워드(병원: 사이트 키워드 / 마케팅: 글 주제 키워드) — 빌드 출력에만 적용, 실패해도 배포는 계속
    subprocess.run([sys.executable, str(Path(__file__).resolve().parent / 'title_hook.py'), str(site)])
    r = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / 'enrich_hook.py'), str(site)])
    if r.returncode: print(f'[{sj["domain"]}] 글 형식 보강 실패 exit {r.returncode}'); sys.exit(r.returncode)
    # 첫 페이지 보강(병원·업체 사이트만; 제목 키워드·h2 키워드·목차·최근 글 6·FAQ) — 커밋본은 그대로 두고 빌드 출력에만 적용
    r = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / 'home_hook.py'), str(site)])
    if r.returncode: print(f'[{sj["domain"]}] 첫 페이지 보강 실패 exit {r.returncode}'); sys.exit(r.returncode)
(site / '.post_kw.json').unlink(missing_ok=True)
for p in site.rglob('__pycache__'): shutil.rmtree(p, ignore_errors=True)
print(f'OUT={out}')

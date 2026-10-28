#!/usr/bin/env python3
"""build_site.py — websites-NN/sites/<도메인>/ 을 site.json 의 builder 대로 빌드하고 출력 폴더 경로를 출력한다.
usage: build_site.py <sites/<도메인> 경로>   → stdout 마지막 줄: OUT=<출력 폴더 절대경로>
  python-generator : dist/ 비움 → static/ 복사 → site.json build 실행 → dist/
  static           : 빌드 없음 → public/ (site.json dist)
  wpstatic         : site.json build 를 제자리에서 실행(멱등 후처리) → site.json dist (public|docs)
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
for p in site.rglob('__pycache__'): shutil.rmtree(p, ignore_errors=True)
print(f'OUT={out}')

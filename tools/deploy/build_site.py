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
    # 새 글 구조 v5(frontmatter `layout: v5` 인 md 글만; 대표 이미지·도입·질문형 소제목 5·표 2·FAQ 6·해시태그 9) — 그 표기가 없는 글은 손대지 않는다. 변환 실패는 배포 중단
    if builder == 'python-generator' and (site / 'content' / 'posts').is_dir():
        r = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / 'layout_v5.py'), str(site)])
        if r.returncode: print(f'[{sj["domain"]}] 새 글 구조(v5) 변환 실패 exit {r.returncode}'); sys.exit(r.returncode)
    # 글 제목에 키워드(병원: 사이트 키워드 / 마케팅: 글 주제 키워드) — 빌드 출력에만 적용, 실패해도 배포는 계속
    subprocess.run([sys.executable, str(Path(__file__).resolve().parent / 'title_hook.py'), str(site)])
    r = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / 'enrich_hook.py'), str(site)])
    if r.returncode: print(f'[{sj["domain"]}] 글 형식 보강 실패 exit {r.returncode}'); sys.exit(r.returncode)
    # 첫 페이지 보강(병원·업체 사이트만; 제목 키워드·h2 키워드·목차·최근 글 6·FAQ) — 커밋본은 그대로 두고 빌드 출력에만 적용
    r = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / 'home_hook.py'), str(site)])
    if r.returncode: print(f'[{sj["domain"]}] 첫 페이지 보강 실패 exit {r.returncode}'); sys.exit(r.returncode)
    # 홈 검색 설명 문구(home_descriptions.json) — 빌드 출력에만 적용, 멱등. 실패해도 배포는 계속
    subprocess.run([sys.executable, str(Path(__file__).resolve().parent / 'desc_hook.py'), str(site)])
    # 홈 '오시는 길' 아래 구글 지도(병원·정보 사이트만) — 빌드 출력에만 적용, 멱등. 실패해도 배포는 계속
    subprocess.run([sys.executable, str(Path(__file__).resolve().parent / 'map_hook.py'), str(site)])
    # 홈 오른쪽 퀵메뉴: 대표 카드 6장 아래까지 스크롤하면 표시(병원·정보 사이트만) — 빌드 출력에만 적용, 멱등. 실패해도 배포는 계속
    subprocess.run([sys.executable, str(Path(__file__).resolve().parent / 'quick_hook.py'), str(site)])
    # 카드 페이지(홈 ItemList 6쪽) 본문 아래에 홈과 같은 카드 6장 목록(병원·정보 사이트만, mediwoman 제외) — 빌드 출력에만 적용, 멱등. 실패해도 배포는 계속
    # 애드온 마케팅 홈 기준(mkt_home.json 등록 도메인만): 홈 title·description·H1·사이트 이름·카드 제목 — 빌드 출력에만 적용, 멱등. 실패해도 배포는 계속
    subprocess.run([sys.executable, str(Path(__file__).resolve().parent / 'mkt_home_hook.py'), str(site)])
    subprocess.run([sys.executable, str(Path(__file__).resolve().parent / 'cards_hook.py'), str(site)])
    # 글 페이지 태그 정리(H1 한 번만 · 수정일/sitemap lastmod) — 빌드 출력에만 적용, 본문·홈은 그대로. 실패해도 배포는 계속
    subprocess.run([sys.executable, str(Path(__file__).resolve().parent / 'seo_hook.py'), str(site)])
(site / '.post_kw.json').unlink(missing_ok=True)
for p in site.rglob('__pycache__'): shutil.rmtree(p, ignore_errors=True)
print(f'OUT={out}')

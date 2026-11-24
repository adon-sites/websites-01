#!/usr/bin/env python3
"""plan.py — 이번 푸시에서 배포할 사이트 목록과 Worker 배포 여부를 계산 (GitHub Actions `plan` job)
usage: plan.py [--before <sha>] [--sha <sha>] [--domain <도메인>]   → stdout JSON {"sites":[...], "worker":bool, "reason":"..."}
  --domain 이 있으면 그 사이트 하나.  아니면 `git diff --name-only before..sha` 로 sites/<도메인>/ 변경 감지.
  before 는 deploy.yml 이 넘기는 "마지막 success push run 의 sha"(없으면 event.before). 없거나 diff 불가능하면 sites/*/site.json 전부.
  hosting/ 변경 → worker=true.  .github/ · tools/ 만 바뀐 푸시는 사이트 0곳(수동 실행으로 돌림).
"""
import argparse, json, subprocess, sys
from pathlib import Path

ap = argparse.ArgumentParser(); ap.add_argument('--before', default=''); ap.add_argument('--sha', default='HEAD'); ap.add_argument('--domain', default=''); ap.add_argument('--all', action='store_true'); ap.add_argument('--allow-frozen', action='store_true'); ap.add_argument('--push-before', default='')
a = ap.parse_args()
all_sites = sorted(p.parent.name for p in Path('sites').glob('*/site.json'))
# 배포 동결 사이트(frozen.json): 전체 배포에서 항상 빼고, 직접 지정해도 --allow-frozen 없이는 뺀다. push(새 글 발행)는 push_ok 면 통과
_fz = Path(__file__).resolve().parent / 'frozen.json'
_fzj = json.loads(_fz.read_text(encoding='utf-8')) if _fz.exists() else {}
FROZEN = set(_fzj.get('frozen', [])); PUSH_OK = bool(_fzj.get('push_ok'))
def thaw(sites, why):
    if a.allow_frozen: return sites, why
    cut = [d for d in sites if d in FROZEN]
    return [d for d in sites if d not in FROZEN], why + (f' (동결 제외: {", ".join(cut)})' if cut else '')
if a.domain:
    want = [d.strip() for d in a.domain.split(',') if d.strip()]
    bad = [d for d in want if d not in all_sites]
    if bad: print(json.dumps({'sites': [], 'worker': False, 'reason': f'unknown domain {bad}'})); sys.exit(1)
    want, why = thaw(want, 'workflow_dispatch')
    print(json.dumps({'sites': want, 'worker': False, 'reason': why}, ensure_ascii=False)); sys.exit(0)
if a.all:
    a.allow_frozen = False   # 전체 배포는 동결 사이트를 절대 포함하지 않는다
    sites, why = thaw(all_sites, 'workflow_dispatch all')
    print(json.dumps({'sites': sites, 'worker': False, 'reason': why}, ensure_ascii=False)); sys.exit(0)
files = None
if a.before and not set(a.before) <= {'0'}:
    # -z: 한글 경로를 따옴표·이스케이프 없이 받는다(따옴표가 붙으면 'sites/' 로 시작하지 않아 365raeon·beomeorosee 가 빠졌다, 2026-11-19)
    r = subprocess.run(['git', 'diff', '--name-only', '-z', a.before, a.sha], capture_output=True, text=True)
    if r.returncode == 0: files = [f for f in r.stdout.split('\0') if f]
if files is None:
    sites, why = thaw(all_sites, 'no diff base → full deploy')
    print(json.dumps({'sites': sites, 'worker': True, 'reason': why}, ensure_ascii=False)); sys.exit(0)
sites = sorted({f.split('/')[1] for f in files if f.startswith('sites/') and f.count('/') >= 2 and f.split('/')[1] in all_sites})
worker = any(f.startswith('hosting/') for f in files)
why = f'{len(files)} changed files since {a.before[:7]}'
# 동결 사이트는 "이번 push 자체"(event.before..sha)가 그 사이트 파일을 건드렸을 때만(=새 글 발행) 통과한다.
# diff base(마지막 성공 run)가 오래돼 전 사이트가 잡히는 push 는 사실상 전체 배포이므로 동결 사이트를 뺀다.
touched = set()
if PUSH_OK and a.push_before and not set(a.push_before) <= {'0'}:
    r2 = subprocess.run(['git', 'diff', '--name-only', '-z', a.push_before, a.sha], capture_output=True, text=True)
    if r2.returncode == 0: touched = {f.split('/')[1] for f in r2.stdout.split('\0') if f.startswith('sites/') and f.count('/') >= 2}
cut = [d for d in sites if d in FROZEN and d not in touched]
if cut: sites = [d for d in sites if d not in cut]; why += f' (동결 제외: {", ".join(cut)})'
print(json.dumps({'sites': sites, 'worker': worker, 'reason': why}, ensure_ascii=False))

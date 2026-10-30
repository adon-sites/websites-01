#!/usr/bin/env python3
"""plan.py — 이번 푸시에서 배포할 사이트 목록과 Worker 배포 여부를 계산 (GitHub Actions `plan` job)
usage: plan.py [--before <sha>] [--sha <sha>] [--domain <도메인>]   → stdout JSON {"sites":[...], "worker":bool, "reason":"..."}
  --domain 이 있으면 그 사이트 하나.  아니면 `git diff --name-only before..sha` 로 sites/<도메인>/ 변경 감지.
  before 는 deploy.yml 이 넘기는 "마지막 success push run 의 sha"(없으면 event.before). 없거나 diff 불가능하면 sites/*/site.json 전부.
  hosting/ 변경 → worker=true.  .github/ · tools/ 만 바뀐 푸시는 사이트 0곳(수동 실행으로 돌림).
"""
import argparse, json, subprocess, sys
from pathlib import Path

ap = argparse.ArgumentParser(); ap.add_argument('--before', default=''); ap.add_argument('--sha', default='HEAD'); ap.add_argument('--domain', default=''); ap.add_argument('--all', action='store_true')
a = ap.parse_args()
all_sites = sorted(p.parent.name for p in Path('sites').glob('*/site.json'))
if a.domain:
    want = [d.strip() for d in a.domain.split(',') if d.strip()]
    bad = [d for d in want if d not in all_sites]
    if bad: print(json.dumps({'sites': [], 'worker': False, 'reason': f'unknown domain {bad}'})); sys.exit(1)
    print(json.dumps({'sites': want, 'worker': False, 'reason': 'workflow_dispatch'})); sys.exit(0)
if a.all:
    print(json.dumps({'sites': all_sites, 'worker': False, 'reason': 'workflow_dispatch all'})); sys.exit(0)
files = None
if a.before and not set(a.before) <= {'0'}:
    r = subprocess.run(['git', 'diff', '--name-only', a.before, a.sha], capture_output=True, text=True)
    if r.returncode == 0: files = r.stdout.split()
if files is None:
    print(json.dumps({'sites': all_sites, 'worker': True, 'reason': 'no diff base → full deploy'})); sys.exit(0)
sites = sorted({f.split('/')[1] for f in files if f.startswith('sites/') and f.count('/') >= 2 and f.split('/')[1] in all_sites})
worker = any(f.startswith('hosting/') for f in files)
print(json.dumps({'sites': sites, 'worker': worker, 'reason': f'{len(files)} changed files since {a.before[:7]}'}))

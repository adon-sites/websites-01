#!/usr/bin/env python3
"""mkt_guard.py — 마케팅 발행 실행 전 멈춤 조건 검사. usage: python3 -I tools/publish/mkt_guard.py <site-ops 경로>
출력 첫 줄이 GO 면 발행, STOP <사유> 면 이번 실행은 글을 쓰지 않는다. STOP-NEW 는 방금 조건에 걸린 것(→ 등록 파일 skip_date 기록·사용자 알림 필요).
조건(사용자 2026-11-26): ① registry/mkt_publish.json 의 enabled 가 false ② skip_date 가 오늘(KST)
 ③ 오늘(KST, count_from 이후) 끝난 deploy 실행 중 실패+취소가 10% 초과(끝난 실행 10건 이상일 때) ④ 줄 서 있는(queued·pending) deploy 실행이 30분 넘게 대기"""
import json, subprocess, sys, datetime
from pathlib import Path
KST = datetime.timezone(datetime.timedelta(hours=9)); now = datetime.datetime.now(KST); today = now.strftime('%Y-%m-%d')
ctl = json.loads((Path(sys.argv[1]) / 'registry' / 'mkt_publish.json').read_text(encoding='utf-8'))
if not ctl.get('enabled'): print('STOP enabled=false (등록 파일에서 꺼져 있음)'); sys.exit(0)
if ctl.get('skip_date') == today: print(f'STOP skip_date={today} (오늘 남은 발행 건너뜀: {ctl.get("skip_reason", "")})'); sys.exit(0)
start = now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
start = max(start, ctl.get('count_from') or '')   # 발행을 켠 시각(UTC) 이전의 배포 기록은 세지 않는다
try:
    out = subprocess.run(['gh', 'api', '--paginate', f'repos/adon-sites/websites-01/actions/workflows/deploy.yml/runs?per_page=100&created=>={start}',
                          '-q', '.workflow_runs[]|[.status,(.conclusion//""),.created_at,.event]|@tsv'], capture_output=True, text=True, timeout=120).stdout
except Exception as e:
    print(f'GO (배포 기록 조회 실패 — 조건 ③④ 확인 못 함: {e})'); sys.exit(0)
rows = [l.split('\t') for l in out.splitlines() if l.strip()]
done = [r for r in rows if r[0] == 'completed']; bad = [r for r in done if r[1] in ('failure', 'cancelled', 'timed_out')]
waiting = [r for r in rows if r[0] in ('queued', 'pending', 'waiting', 'requested')]
old = [r for r in waiting if (now - datetime.datetime.strptime(r[2], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)).total_seconds() > 1800]
stat = f'오늘 끝난 배포 {len(done)}건 중 실패·취소 {len(bad)}건, 대기 {len(waiting)}건'
if len(done) >= 10 and len(bad) / len(done) > 0.10: print(f'STOP-NEW 배포 실패·취소 {len(bad)}/{len(done)} = {len(bad)*100//len(done)}% (10% 초과)'); sys.exit(0)
if old: print(f'STOP-NEW 배포 대기 30분 초과 {len(old)}건 (가장 오래된 것 {min(r[2] for r in old)} 생성)'); sys.exit(0)
print(f'GO ({stat})')

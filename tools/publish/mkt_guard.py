#!/usr/bin/env python3
"""mkt_guard.py — 마케팅 발행 실행 전 멈춤 조건 검사. usage: python3 -I tools/publish/mkt_guard.py <site-ops 경로> [--detail]
출력 첫 줄이 GO 면 발행, STOP <사유> 면 이번 실행은 글을 쓰지 않는다. STOP-NEW 는 방금 조건에 걸린 것(→ 등록 파일 skip_date 기록·사용자 알림 필요).
조건(사용자 2026-11-26 19:07 개정): ① registry/mkt_publish.json 의 enabled 가 false ② skip_date 가 오늘(KST)
 ③ 오늘(KST, count_from 이후) 끝난 자동(push) 배포 중 "세는 실패"가 10% 초과(끝난 실행 10건 이상일 때)
 ④ 줄 서 있는(queued·pending) 배포가 30분 넘게 대기
세는 실패 = 실제 실패(failure·timed_out) + 확인 안 된 취소.
세지 않는 것 = 수동(workflow_dispatch) 배포 전부 / 뒤에 온 배포로 자동 교체되어 취소됐고, 그 배포에 들어 있던 사이트가 뒤 배포에서 실제로 올라간 것(성공 job)이 확인된 취소.
 뒤 배포가 아직 돌고 있거나 대기 중이라 확인을 못 한 취소는 '확인 대기'로 두고 이번에는 세지 않는다. 취소된 지 30분이 지나도 확인이 안 되면 실패로 센다."""
import json, subprocess, sys, datetime
from pathlib import Path
REPO = 'adon-sites/websites-01'
KST = datetime.timezone(datetime.timedelta(hours=9)); now = datetime.datetime.now(KST); today = now.strftime('%Y-%m-%d')
def gh(path, q):
    r = subprocess.run(['gh', 'api', '--paginate', path, '-q', q], capture_output=True, text=True, timeout=120)
    if r.returncode: raise RuntimeError(r.stderr.strip()[:200])
    return [l.split('\t') for l in r.stdout.splitlines() if l.strip()]
def analyse(start):
    rows = gh(f'repos/{REPO}/actions/workflows/deploy.yml/runs?per_page=100&created=>={start}', '.workflow_runs[]|[(.id|tostring),.status,(.conclusion//""),.created_at,.event,.head_sha]|@tsv')
    rows.sort(key=lambda r: r[3]); push = [r for r in rows if r[4] == 'push']; jobs = {}
    def run_jobs(rid):
        if rid not in jobs: jobs[rid] = {n[8:-1]: c for n, c in gh(f'repos/{REPO}/actions/runs/{rid}/jobs?per_page=100', '.jobs[]|[.name,(.conclusion//.status)]|@tsv') if n.startswith('deploy (')}
        return jobs[rid]
    done = [r for r in push if r[1] == 'completed']; fails = [r for r in done if r[2] in ('failure', 'timed_out')]
    replaced, unconfirmed, waiting_confirm = [], [], []
    for r in [x for x in done if x[2] == 'cancelled']:
        sites = sorted({p.split('/')[1] for (p,) in gh(f'repos/{REPO}/commits/{r[5]}', '.files[]|[.filename]|@tsv') if p.startswith('sites/')})
        own = run_jobs(r[0]); left = [s for s in sites if own.get(s) != 'success']; later = [x for x in push if x[3] > r[3]]; pending = False
        for x in later:
            if not left: break
            if x[1] != 'completed': pending = True; continue
            j = run_jobs(x[0]); left = [s for s in left if j.get(s) != 'success']
        # 확인 대기는 취소된 지 30분 안일 때만(= 다음 검사까지). 그 뒤에도 확인이 안 되면 실패로 센다(사용자 2026-11-26 19:11)
        fresh = (now - datetime.datetime.strptime(r[3], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)).total_seconds() <= 1800
        (replaced if not left else waiting_confirm if (pending and fresh) else unconfirmed).append((r[0], r[3], sites, left))
    waiting = [r for r in rows if r[1] in ('queued', 'pending', 'waiting', 'requested')]
    old = [r for r in waiting if (now - datetime.datetime.strptime(r[3], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)).total_seconds() > 1800]
    return dict(runs=len(rows), manual=len(rows) - len(push), done=len(done), fails=fails, replaced=replaced, unconfirmed=unconfirmed, waiting_confirm=waiting_confirm, waiting=waiting, old=old)
def main():
    ctl = json.loads((Path(sys.argv[1]) / 'registry' / 'mkt_publish.json').read_text(encoding='utf-8')); detail = '--detail' in sys.argv
    if not detail:
        if not ctl.get('enabled'): print('STOP enabled=false (등록 파일에서 꺼져 있음)'); return
        if ctl.get('skip_date') == today: print(f'STOP skip_date={today} (오늘 남은 발행 건너뜀: {ctl.get("skip_reason", "")})'); return
    start = now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    start = max(start, ctl.get('count_from') or '')   # 발행을 켠 시각(UTC) 이전의 배포 기록은 세지 않는다
    try: a = analyse(start)
    except Exception as e: print(f'GO (배포 기록 조회 실패 — 조건 ③④ 확인 못 함: {e})'); return
    bad = len(a['fails']) + len(a['unconfirmed']); base = a['done'] - len(a['replaced']) - len(a['waiting_confirm'])
    stat = f'자동 배포 {a["done"]}건 끝남 · 실제 실패 {len(a["fails"])} · 자동 교체 취소 {len(a["replaced"])}(뒤 배포에서 올라간 것 확인) · 확인 안 된 취소 {len(a["unconfirmed"])} · 확인 대기 {len(a["waiting_confirm"])} · 수동 배포 {a["manual"]}(세지 않음) · 대기 {len(a["waiting"])}'
    if base >= 10 and bad / base > 0.10: print(f'STOP-NEW 세는 실패 {bad}/{base} = {bad * 100 // base}% (10% 초과) — {stat}')
    elif a['old']: print(f'STOP-NEW 배포 대기 30분 초과 {len(a["old"])}건 (가장 오래된 것 {min(r[3] for r in a["old"])} 생성) — {stat}')
    else: print(f'GO ({stat})')
    if detail:
        for k, lab in (('fails', '실제 실패'), ('replaced', '자동 교체 취소(확인됨)'), ('unconfirmed', '확인 안 된 취소'), ('waiting_confirm', '확인 대기')):
            for x in a[k]: print(f'  {lab}: 실행 {x[0]} · {x[3] if k == "fails" else x[1]} · ' + ('' if k == 'fails' else f'사이트 {", ".join(x[2]) or "(사이트 변경 없음)"}' + (f' · 아직 안 올라간 곳 {", ".join(x[3])}' if x[3] else '')))
if __name__ == '__main__': main()

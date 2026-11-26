#!/usr/bin/env python3
"""mkt_guard.py — 마케팅 발행 실행 전 멈춤 조건 검사.
usage: python3 -I tools/publish/mkt_guard.py <site-ops 경로> [--detail] [--asof 2026-11-27T01:38:00+09:00]

출력 첫 줄:
  GO …          발행한다.
  STOP …        이번 실행은 글을 쓰지 않는다(꺼져 있음 / 오늘 남은 발행 멈춤 / 1시간 쉬는 중).
  PAUSE-NEW …   방금 조건에 걸렸다 → 1시간 쉰다(글을 쓰지 않는다). 사용자 알림은 필요 없다.
  STOP-NEW …    같은 날 세 번째로 걸렸다 → 그날 남은 발행을 멈춘다. 사용자에게 알린다.
마지막 줄이 SAVE 면 이 도구가 registry/mkt_publish.json 을 고친 것이므로 site-ops 를 커밋·푸시한다.

조건(사용자 2026-11-27 02:18 개정):
 ① registry/mkt_publish.json 의 enabled 가 false ② skip_date 가 오늘(KST) ②' 오늘 기록된 쉼(pauses)의 until 이 아직 안 지남
 ③ 오늘(KST, count_from 이후) 끝난 자동(push) 배포가 20건 이상이면 "세는 실패" 비율이 10% 초과일 때, 20건 미만이면 실제 실패가 3건 이상일 때
 ④ 줄 서 있는(queued·pending) 배포가 30분 넘게 대기
 ③④에 걸리면 그날 전체를 건너뛰지 않고 1시간만 쉰다. 쉬는 시간이 지나 다시 검사해 통과하면 자동으로 재개한다(GO, 재개 시각 기록).
 같은 날 세 번째로 걸리면 skip_date 를 오늘로 적어 그날 남은 발행을 멈춘다.
세는 실패 = 실제 실패(failure·timed_out) + 확인 안 된 취소.
세지 않는 것 = 수동(workflow_dispatch) 배포 전부 / 뒤에 온 배포로 자동 교체되어 취소됐고, 그 배포에 들어 있던 사이트가 뒤 배포에서 실제로 올라간 것(성공 job)이 확인된 취소.
 뒤 배포가 아직 돌고 있거나 대기 중이라 확인을 못 한 취소는 '확인 대기'로 두고 이번에는 세지 않는다. 취소된 지 30분이 지나도 확인이 안 되면 실패로 센다.
실제 실패는 실패한 사이트가 뒤 배포에서 다시 올라갔는지도 함께 확인해 적는다(올라갔어도 실패 건수에서는 빼지 않는다).
--asof 는 그 시각 기준으로 다시 계산해 보는 시험용이다(파일을 고치지 않는다. 조건 ④는 그때의 대기 상태를 알 수 없어 실행 시작 여부로만 본다)."""
import json, subprocess, sys, datetime
from pathlib import Path
REPO = 'adon-sites/websites-01'
KST = datetime.timezone(datetime.timedelta(hours=9)); UTC = datetime.timezone.utc
PAUSE_MIN = 60; MAX_PAUSES = 2          # 하루에 두 번까지는 1시간 쉬고, 세 번째에 그날 멈춤
MIN_DONE = 20; MIN_FAILS = 3; RATE = 0.10
asof = None
if '--asof' in sys.argv: asof = datetime.datetime.fromisoformat(sys.argv[sys.argv.index('--asof') + 1])
now = asof or datetime.datetime.now(KST); today = now.astimezone(KST).strftime('%Y-%m-%d')
Z = lambda s: datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=UTC)

def gh(path, q):
    r = subprocess.run(['gh', 'api', '--paginate', path, '-q', q], capture_output=True, text=True, timeout=120)
    if r.returncode: raise RuntimeError(r.stderr.strip()[:200])
    return [l.split('\t') for l in r.stdout.splitlines() if l.strip()]

def analyse(start):
    rows = gh(f'repos/{REPO}/actions/workflows/deploy.yml/runs?per_page=100&created=>={start}', '.workflow_runs[]|[(.id|tostring),.status,(.conclusion//""),.created_at,.event,.head_sha,.updated_at]|@tsv')
    if asof:   # 그 시각의 모습으로 되돌린다: 그 뒤에 생긴 실행은 빼고, 그때 아직 안 끝난 실행은 진행 중으로
        rows = [r for r in rows if Z(r[3]) <= asof]
        rows = [r if Z(r[6]) <= asof else [r[0], 'in_progress', '', r[3], r[4], r[5], r[6]] for r in rows]
    rows.sort(key=lambda r: r[3]); push = [r for r in rows if r[4] == 'push']; jobs = {}
    def run_jobs(rid):
        if rid not in jobs:
            js = gh(f'repos/{REPO}/actions/runs/{rid}/jobs?per_page=100', '.jobs[]|[.name,(.conclusion//.status),(.completed_at//"")]|@tsv')
            jobs[rid] = {n[8:-1]: (c if not asof or (t and Z(t) <= asof) else 'in_progress') for n, c, *rest in js for t in [rest[0] if rest else ''] if n.startswith('deploy (')}
        return jobs[rid]
    def later_ok(r, left):
        """left 의 사이트가 r 뒤의 push 실행에서 올라갔는지 → (아직 안 올라간 곳, 확인 못 한 뒤 실행이 남았는지)"""
        pending = False
        for x in [x for x in push if x[3] > r[3]]:
            if not left: break
            if x[1] != 'completed': pending = True; continue
            j = run_jobs(x[0]); left = [s for s in left if j.get(s) != 'success']
        return left, pending
    done = [r for r in push if r[1] == 'completed']; fails = []
    for r in [x for x in done if x[2] in ('failure', 'timed_out')]:
        bad_sites = sorted(s for s, c in run_jobs(r[0]).items() if c not in ('success', 'skipped')); left, _p = later_ok(r, list(bad_sites))
        fails.append((r[0], r[3], bad_sites, left))
    replaced, unconfirmed, waiting_confirm = [], [], []
    for r in [x for x in done if x[2] == 'cancelled']:
        sites = sorted({p.split('/')[1] for (p,) in gh(f'repos/{REPO}/commits/{r[5]}', '.files[]|[.filename]|@tsv') if p.startswith('sites/')})
        own = run_jobs(r[0]); left, pending = later_ok(r, [s for s in sites if own.get(s) != 'success'])
        fresh = (now - Z(r[3])).total_seconds() <= 1800   # 확인 대기는 취소된 지 30분 안일 때만. 그 뒤에도 확인이 안 되면 실패로 센다
        (replaced if not left else waiting_confirm if (pending and fresh) else unconfirmed).append((r[0], r[3], sites, left))
    waiting = [r for r in rows if r[1] in ('queued', 'pending', 'waiting', 'requested')]
    old = [r for r in waiting if (now - Z(r[3])).total_seconds() > 1800]
    return dict(runs=len(rows), manual=len(rows) - len(push), done=len(done), fails=fails, replaced=replaced, unconfirmed=unconfirmed, waiting_confirm=waiting_confirm, waiting=waiting, old=old)

def verdict(a):
    """→ (걸렸는지, 사유, 상태 요약)"""
    bad = len(a['fails']) + len(a['unconfirmed']); base = a['done'] - len(a['replaced']) - len(a['waiting_confirm'])
    back = sum(1 for f in a['fails'] if f[2] and not f[3])
    stat = (f'자동 배포 {a["done"]}건 끝남 · 실제 실패 {len(a["fails"])}' + (f'(그중 {back}건은 뒤 배포에서 다시 올라감)' if a['fails'] else '') +
            f' · 자동 교체 취소 {len(a["replaced"])}(뒤 배포에서 올라간 것 확인) · 확인 안 된 취소 {len(a["unconfirmed"])} · 확인 대기 {len(a["waiting_confirm"])} · 수동 배포 {a["manual"]}(세지 않음) · 대기 {len(a["waiting"])}')
    if a['done'] >= MIN_DONE and base > 0 and bad / base > RATE: return True, f'세는 실패 {bad}/{base} = {bad * 100 // base}% (10% 초과)', stat
    if a['done'] < MIN_DONE and len(a['fails']) >= MIN_FAILS: return True, f'자동 배포 {MIN_DONE}건이 끝나기 전에 실제 실패 {len(a["fails"])}건', stat
    if a['old']: return True, f'배포 대기 30분 초과 {len(a["old"])}건 (가장 오래된 것 {min(r[3] for r in a["old"])} 생성)', stat
    return False, '', stat

def main():
    path = Path(sys.argv[1]) / 'registry' / 'mkt_publish.json'; ctl = json.loads(path.read_text(encoding='utf-8')); detail = '--detail' in sys.argv
    write = not detail and not asof; hm = lambda s: datetime.datetime.fromisoformat(s).astimezone(KST).strftime('%H:%M')
    pauses = [p for p in (ctl.get('pauses') or []) if p.get('date') == today]
    # 같은 일로 여러 실행이 동시에 적은 쉼은 하나로 센다(시작이 50분 안쪽으로 붙은 것)
    distinct = []
    for p in sorted(pauses, key=lambda p: p['at']):
        if not distinct or (datetime.datetime.fromisoformat(p['at']) - datetime.datetime.fromisoformat(distinct[-1]['at'])).total_seconds() > 50 * 60: distinct.append(p)
    if not detail and not asof:
        if not ctl.get('enabled'): print('STOP enabled=false (등록 파일에서 꺼져 있음)'); return
        if ctl.get('skip_date') == today: print(f'STOP skip_date={today} (오늘 남은 발행 멈춤: {ctl.get("skip_reason", "")})'); return
        act = [p for p in pauses if datetime.datetime.fromisoformat(p['until']) > now]
        if act: print(f'STOP 쉬는 중 ({hm(act[-1]["until"])} 까지, {hm(act[-1]["at"])} 에 걸림: {act[-1].get("reason", "")})'); return
    start = now.astimezone(KST).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
    start = max(start, ctl.get('count_from') or '')   # 발행을 켠 시각(UTC) 이전의 배포 기록은 세지 않는다
    try: a = analyse(start)
    except Exception as e: print(f'GO (배포 기록 조회 실패 — 조건 ③④ 확인 못 함: {e})'); return
    hit, why, stat = verdict(a); saved = False
    if hit and detail: print(f'(지금 검사하면 걸림) {why} — {stat}')
    elif hit:
        if len(distinct) >= MAX_PAUSES:
            print(f'STOP-NEW 오늘 {len(distinct) + 1}번째로 걸림 — {why} — {stat}')
            if write: ctl['skip_date'] = today; ctl['skip_reason'] = f'오늘 {len(distinct) + 1}번째: {why} — {stat}'; saved = True
        else:
            until = now + datetime.timedelta(minutes=PAUSE_MIN)
            print(f'PAUSE-NEW {until.astimezone(KST).strftime("%H:%M")} 까지 1시간 쉼(오늘 {len(distinct) + 1}번째) — {why} — {stat}')
            if write: ctl.setdefault('pauses', []).append({'date': today, 'at': now.isoformat(timespec='seconds'), 'until': until.isoformat(timespec='seconds'), 'reason': why, 'stat': stat}); saved = True
    else:
        last = pauses[-1] if pauses else None
        if last and not last.get('resumed') and not detail:
            print(f'GO (자동 재개: {hm(last["at"])} 에 쉬기 시작 → 다시 검사해 통과 · {stat})')
            if write:
                for p in ctl['pauses']:
                    if p.get('date') == today and not p.get('resumed'): p['resumed'] = now.isoformat(timespec='seconds')
                saved = True
        else: print(f'GO ({stat})')
    if detail:
        for x in a['fails']: print(f'  실제 실패: 실행 {x[0]} · {x[1]} · 실패한 사이트 {", ".join(x[2]) or "(확인 못 함)"} · ' + ('뒤 배포에서 다시 올라감' if x[2] and not x[3] else f'아직 안 올라간 곳 {", ".join(x[3]) or "(확인 못 함)"}'))
        for k, lab in (('replaced', '자동 교체 취소(확인됨)'), ('unconfirmed', '확인 안 된 취소'), ('waiting_confirm', '확인 대기')):
            for x in a[k]: print(f'  {lab}: 실행 {x[0]} · {x[1]} · 사이트 {", ".join(x[2]) or "(사이트 변경 없음)"}' + (f' · 아직 안 올라간 곳 {", ".join(x[3])}' if x[3] else ''))
        for p in pauses: print(f'  오늘의 쉼: {hm(p["at"])} ~ {hm(p["until"])} · 재개 {hm(p["resumed"]) if p.get("resumed") else "아직"} · {p.get("reason", "")}')
    if saved: path.write_text(json.dumps(ctl, ensure_ascii=False, indent=1), encoding='utf-8'); print('SAVE')

if __name__ == '__main__': main()

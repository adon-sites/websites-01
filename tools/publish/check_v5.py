#!/usr/bin/env python3
"""check_v5.py — 새 글 구조(v5) 마크다운 1편의 발행 전 구조 검사. (배포 때 layout_v5.py 가 같은 규칙으로 변환한다)
usage: python3 -I tools/publish/check_v5.py <sites/<도메인> 경로> <slug> [--keyword 대표키워드]
FAIL 이 하나라도 있으면 exit 1 — 고쳐서 다시 돌린다. 중복·금지어 검사는 sources-01 의 check_md.py 가 따로 한다.
기준: layout: v5 · intro 120~320자 · `## ` 질문형 소제목 5개(각 2문단 이상) · 표 2개(2~4칸, 내용 3~6줄, 서로 다른 절)
      · `## 자주 묻는 질문` 아래 `### ` 질문 6개(답 1문단 이상) · tags 9개 · 소제목 5개 절의 문단 합계 1,000자 이상(전체 분량 1,500~2,500자는 check_md.py 가 본다)
      · `[표] 제목` 줄 바로 다음 줄이 표(`|`)여야 한다(빈 줄 금지)
      · date 는 지금보다 과거(KST) · 본문에 링크·HTML·이미지 없음 · 대표 키워드가 intro 와 tags 에 있음"""
import sys, re, json, datetime, importlib.util
from pathlib import Path

def load_v5():
    p = Path(__file__).resolve().parent.parent / 'deploy' / 'layout_v5.py'
    spec = importlib.util.spec_from_file_location('layout_v5', p); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def nchars(t): return len(re.sub(r'\s+', '', t))

def main():
    a = sys.argv[1:]; kw = None
    if '--keyword' in a: i = a.index('--keyword'); kw = a[i + 1]; del a[i:i + 2]
    if len(a) != 2: print(__doc__); sys.exit(2)
    site, slug = Path(a[0]).resolve(), a[1]; md = site / 'content' / 'posts' / f'{slug}.md'
    v5 = load_v5(); raw = md.read_text(encoding='utf-8'); doc = v5.parse_v5(raw); meta = doc['meta'] or {}
    F, W = [], []
    if kw is None:
        try: kw = json.loads((site / 'content' / 'company.json').read_text(encoding='utf-8'))['seo']['primary']
        except Exception: kw = ''
    if meta.get('layout') != 'v5': F.append('frontmatter 에 layout: v5 가 없음')
    for k in ('title', 'short_title', 'description', 'category', 'date', 'intro', 'tags'):
        if not meta.get(k): F.append(f'frontmatter {k} 없음')
    intro = doc['intro']; n = nchars(intro)
    if intro and not 120 <= n <= 320: F.append(f'intro {n}자(기준 120~320)')
    F += v5.problems(doc)
    body = 0
    for i, s in enumerate(doc['sections'], 1):
        ps = [b for b in s['blocks'] if b[0] == 'p']; body += sum(nchars(b[1]) for b in ps)
        if not s['heading'].rstrip().endswith('?'): F.append(f'소제목 {i} 이 질문형(?)이 아님: {s["heading"]}')
        if len(ps) < 2: F.append(f'소제목 {i} 문단 {len(ps)}개(2개 이상)')
        if sum(1 for b in s['blocks'] if b[0] == 'table') > 1: F.append(f'소제목 {i} 에 표가 2개 — 표는 서로 다른 절에')
        for b in s['blocks']:
            if b[0] == 'table':
                _, cap, head, rows = b
                if not 2 <= len(head) <= 4: F.append(f'표 칸 수 {len(head)}(2~4)')
                if not 3 <= len(rows) <= 6: F.append(f'표 내용 {len(rows)}줄(3~6)')
                if not cap: W.append('표 제목([표] …) 없음')
                if any(not c for r in rows for c in r): F.append('표에 빈 칸이 있음')
    if body < 1000: F.append(f'소제목 절 문단 합계 {body}자(1,000자 이상, 표·FAQ 제외)')
    if any(b[0] == 'p' and b[1].lstrip().startswith('[표]') for s in doc['sections'] for b in s['blocks']): F.append('`[표] 제목` 다음 줄에 빈 줄이 있어 표 제목이 문단으로 읽힘 — 빈 줄을 지우세요')
    if any(b[0] == 'p' and '|' in b[1] and b[1].count('|') >= 4 for s in doc['sections'] for b in s['blocks']): F.append('표 표기가 문단으로 읽힘 — 머리줄 다음에 | --- | 구분줄이 있는지 확인')
    for q, ans in doc['faq']:
        if not ans or nchars(' '.join(ans)) < 40: F.append(f'FAQ 답이 없거나 짧음: {q}')
        if not q.rstrip().endswith('?'): F.append(f'FAQ 질문이 ?로 끝나지 않음: {q}')
    if len({q for q, _ in doc['faq']}) != len(doc['faq']): F.append('FAQ 질문 중복')
    heads = [s['heading'] for s in doc['sections']]
    if len(set(heads)) != len(heads): F.append('소제목 중복')
    bodytxt = raw.split('\n---\n', 1)[1] if '\n---\n' in raw else ''
    if re.search(r'https?://|<[a-zA-Z/][^>]*>|!\[', bodytxt): F.append('본문에 링크·HTML·이미지 표기가 있음')
    if re.search(r'^\s*[-*]\s', bodytxt, re.M): W.append('목록(-, *) 표기는 문단으로 합쳐져 보입니다 — 문장이나 표로 쓰세요')
    if kw:
        if kw not in intro: F.append(f'intro 에 대표 키워드 "{kw}" 없음')
        if kw.replace(' ', '') not in [t for t in doc['tags']]: F.append(f'tags 에 대표 키워드 "{kw.replace(" ", "")}" 없음')
    try:
        d = datetime.datetime.fromisoformat(meta.get('date', ''))
        if d.tzinfo is None: F.append('date 에 +09:00 없음')
        elif d > datetime.datetime.now(datetime.timezone.utc): F.append('date 가 미래 시각 — 공개되지 않음')
    except ValueError: F.append('date 형식 오류(YYYY-MM-DDTHH:MM:SS+09:00)')
    for w in W: print('WARN', w)
    for f in F: print('FAIL', f)
    print(f'[{"FAIL" if F else "PASS"}] {site.name}/{slug} — v5 구조: 소제목 {len(doc["sections"])} · 표 {sum(1 for s in doc["sections"] for b in s["blocks"] if b[0]=="table")} · FAQ {len(doc["faq"])} · 태그 {len(doc["tags"])} · 본문 {body}자')
    sys.exit(1 if F else 0)

if __name__ == '__main__': main()

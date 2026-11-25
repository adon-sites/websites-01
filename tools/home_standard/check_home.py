#!/usr/bin/env python3
"""check_home.py — 병원·정보 사이트 홈 수정 기준 검사(기준 도구, 2026-11-26). FAIL 이 있으면 종료코드 1.
usage: check_home.py <도메인> [<도메인> …]     (대상: sites/<도메인>/public/index.html + tools/deploy/home_descriptions.json)
  site-ops/tools/humanize/check.py 는 문단별 전/후 대조 파일(humanize/src·out)이 있어야 돌아서, 구조를 바꾸는 홈 수정에는 쓸 수 없다. 이 도구가 대신한다.
  FAIL: description 160자 초과·대표키워드 2~3회 아님·형식(키워드 | 병원명 | …) 아님·"19:00"식 시각 / H1 이 "키워드, "로 시작하지 않음·콜론·"19:00"식 시각
        안내 블록 3줄 없음 / "저희·본원·우리 병원" / 제3자 인용 / 금지 어미 / 깨진 문장 / 같은 문장 반복 / FAQ 묶음이 한 군데가 아님·FAQPage 와 문항 수 불일치 / ItemList 6 아님
  WARN: description 130~150자 밖 / 홈 4,500~6,000자 밖 / 소제목 10~12개 밖 / FAQ 8개 안팎(6~12) 밖 / 과장·보장 표현
"""
import html, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
BAN_END = ['죠.', '죠?', '어요.', '해요.', '거든요', '잖아요', '고요.', '라서요']
THIRD = ['공식 홈페이지에 따르면', '공식 안내하고', '로 소개됩니다', '안내되어 있습니다', '공개 자료에 따르면', '공개 자료 기준', '공식 홈페이지 기준', '공식 소개에 따르면']
FIRST = ['저희', '본원', '우리 병원', '우리 의원']
BROKEN = [r'[은는이가] 이며', r'[은는] 입니다', r'\(\s*,', r'  +[.,]', r'의원 의원', r'클리닉 수면클리닉', r'병원 병원']
HYPE = ['최고', '유일', '100%', '완벽', '보장합니다', '확실한 효과', '부작용 없는', '1위']


def check(domain):
    fails, warns = [], []
    s = (ROOT / 'sites' / domain / 'public/index.html').read_text(encoding='utf-8')
    desc = json.loads((ROOT / 'tools/deploy/home_descriptions.json').read_text(encoding='utf-8'))['descriptions'].get(domain)
    main = re.search(r'<main.*?</main>', s, re.S).group(0)
    text = html.unescape(re.sub(r'<[^>]+>', ' ', re.sub(r'<(script|style).*?</\1>', '', main, flags=re.S)))
    h1 = html.unescape(re.sub(r'<[^>]+>', '', re.search(r'<h1[^>]*>(.*?)</h1>', s, re.S).group(1))).strip()
    kw = None
    if not desc: fails.append('description 없음(home_descriptions.json)')
    else:
        parts = desc.split(' | ')
        if len(parts) < 3: fails.append('description 형식(키워드 | 병원명 | …) 아님')
        kw = parts[0]; n = len(desc); c = desc.count(kw)
        if n > 160: fails.append(f'description {n}자(160자 초과)')
        elif not 130 <= n <= 150: warns.append(f'description {n}자(130~150자 밖)')
        if not 2 <= c <= 3: fails.append(f'description 대표키워드 {c}회')
        if re.search(r'\d{1,2}:\d{2}', desc): fails.append('description 에 "19:00"식 시각')
        if '☎' not in desc: fails.append('description 에 전화 표기 없음')
    if kw and not h1.startswith(kw + ', '): fails.append(f'H1 이 "{kw}, "로 시작하지 않음: {h1[:30]}')
    if re.search(r'(?<!\d)[:：]|[:：](?!\d)', h1): fails.append('H1 에 콜론')
    if re.search(r'\d{1,2}:\d{2}', h1): fails.append('H1 에 "19:00"식 시각')
    ib = re.search(r'<dl class="home-info">(.*?)</dl>', s, re.S)
    if not ib or [html.unescape(x) for x in re.findall(r'<dt>(.*?)</dt>', ib.group(1))] != ['진료시간', '위치', '전화']: fails.append('안내 블록 3줄(진료시간·위치·전화) 없음')
    for w in FIRST:
        k = text.count(w)
        if k: fails.append(f'"{w}" {k}회')
    for w in THIRD:
        if w in text: fails.append(f'제3자 인용 "{w}"')
    for w in BAN_END:
        if w in text: fails.append(f'금지 어미 "{w}"')
    for p in BROKEN:
        m = re.search(p, text)
        if m: fails.append(f'깨진 문장 "{text[max(0, m.start() - 12):m.end() + 8].strip()}"')
    for w in HYPE:
        if w in text: warns.append(f'과장·보장 표현 "{w}"')
    paras = [html.unescape(re.sub(r'<[^>]+>', '', p)).strip() for p in re.findall(r'<(?:p|li)\b[^>]*>(.*?)</(?:p|li)>', main, re.S)]
    sents = [x.strip() for p in paras for x in re.split(r'(?<=[.!?])\s+', p) if len(x.strip()) > 20]
    for d in sorted({x for x in sents if sents.count(x) > 1}): fails.append(f'같은 문장 반복: "{d[:36]}"')
    nd = len(re.findall(r'<details', main)); blocks = len(re.findall(r'<div class="faq', main))
    fq = [json.loads(m) for m in re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', s, re.S) if '"FAQPage"' in m]
    if blocks != 1: fails.append(f'FAQ 묶음 {blocks}곳')
    if len(fq) != 1: fails.append(f'FAQPage {len(fq)}개')
    elif len(fq[0]['mainEntity']) != nd: fails.append(f'FAQPage {len(fq[0]["mainEntity"])}문항 ≠ 화면 {nd}문항')
    elif [html.unescape(re.sub(r'<[^>]+>', '', q)).strip() for q in re.findall(r'<summary>(.*?)</summary>', main, re.S)] != [q['name'] for q in fq[0]['mainEntity']]: fails.append('FAQPage 질문이 화면과 다름')
    if not 6 <= nd <= 12: warns.append(f'FAQ {nd}개')
    il = [json.loads(m) for m in re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', s, re.S) if '"ItemList"' in m]
    cnt = sum(len(n.get('itemListElement', [])) for o in il for n in (o.get('@graph', [o]) if isinstance(o, dict) else o) if isinstance(n, dict) and n.get('@type') == 'ItemList')
    if cnt != 6: fails.append(f'ItemList {cnt}항목')
    chars = len(re.sub(r'\s', '', text)); h2 = len(re.findall(r'<h2', main))
    if not 4500 <= chars <= 6000: warns.append(f'홈 {chars}자(4,500~6,000자 밖)')
    if not 10 <= h2 <= 12: warns.append(f'소제목 {h2}개(10~12개 밖)')
    return dict(domain=domain, h1=h1, desc_len=len(desc or ''), chars=chars, h2=h2, faq=nd, fails=fails, warns=warns)


if __name__ == '__main__':
    bad = 0
    for d in sys.argv[1:]:
        r = check(d); bad += bool(r['fails'])
        print(f'[{d}] {"FAIL" if r["fails"] else "PASS"} · description {r["desc_len"]}자 · 홈 {r["chars"]}자 · 소제목 {r["h2"]} · FAQ {r["faq"]}')
        for x in r['fails']: print('   FAIL', x)
        for x in r['warns']: print('   WARN', x)
    sys.exit(1 if bad else 0)

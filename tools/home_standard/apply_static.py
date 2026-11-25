#!/usr/bin/env python3
"""apply_static.py — sitegen 정적 사이트(public/index.html) 홈을 '홈 수정 기준'(2026-11-26 사용자 지시)에 맞춰 고친다. 멱등.
usage: apply_static.py <도메인>      (spec: tools/home_standard/specs/<도메인>.json)
  ① H1 ② H1 아래 안내 블록(진료시간·위치·전화), 첫 문단은 기존 주제 도입 유지, '저희·본원' → 병원 이름 ③ 병원 안내: 진료시간 표 + 병원 안내 표
  ④ FAQ 8개 + FAQPage ⑤ 해외 기관 링크 삭제 ⑥ 문장 치환(제3자 서술 → 1인칭 등) ⑦ description 은 tools/deploy/home_descriptions.json
  title, 카드 6장, ItemList, 비용 표, 글은 건드리지 않는다.
"""
import html, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
E = lambda x: html.escape(str(x), quote=False)
CSS = ('<style id="home-std-style">.info-table{width:100%;border-collapse:collapse;margin:14px 0 18px;font-size:.97rem;background:var(--paper,#fff)}'
       '.info-table caption{text-align:left;font-weight:700;margin:0 0 8px;color:var(--brand-deep,#1c3557)}'
       '.info-table th,.info-table td{border:1px solid var(--line,#e2e6ea);padding:11px 13px;text-align:left;vertical-align:top}'
       '.info-table th{width:32%;background:var(--tint,#f4f7f9);font-weight:700;white-space:nowrap}'
       '@media(max-width:560px){.info-table th{width:38%;white-space:normal}}'
       '.home-info{margin:14px 0 18px;padding:14px 16px;border:1px solid var(--line,#e2e6ea);border-radius:10px;background:var(--paper,#fff);font-size:.97rem}'
       '.home-info div{display:grid;grid-template-columns:5.2em 1fr;gap:10px;padding:4px 0}.home-info dt{font-weight:700;color:var(--brand-deep,#1c3557)}.home-info dd{margin:0}</style>')

def jong(w):
    c = w.strip()[-1]
    return '가' <= c <= '힣' and (ord(c) - 0xAC00) % 28 != 0

THIRD = [(r'공개 자료에 따르면\s*', ''), (r'공개 자료 기준,?\s*', ''), (r'공식 소개에 따르면\s*', ''), (r'공식 홈페이지 기준,?\s*', ''),
         (r'해 준다고 공식 홈페이지에 안내되어 있습니다', '해 드립니다'), (r'주차 안내는 공식 자료에 없어 방문 전', '주차는 방문 전'),
         (r'주차 안내는 공식 홈페이지에 명시되어 있지 않습니다\.\s*', ''), (r'\(\s*,\s*', '(')]

def voice(t, name):
    """'저희', '본원' 을 병원 이름으로(조사는 받침에 맞춤)."""
    j = jong(name)
    t = re.sub(r'저희\s+(?=' + re.escape(name) + r')', '', t)
    t = re.sub(r'저희\s+(?=[가-힣A-Za-z0-9]{1,12}(?:의원|병원|치과)(?:[은는이가의도에과와]|\s))', '', t)
    for a, b in (('저희는', name + ('은' if j else '는')), ('저희가', name + ('이' if j else '가')), ('저희도', name + '도'), ('저희의 ', name + '의 '), ('저희 ', name + ' '),
                 ('본원은', name + ('은' if j else '는')), ('본원이', name + ('이' if j else '가')), ('본원에서는', name + '에서는'), ('본원에서', name + '에서'),
                 ('본원에는', name + '에는'), ('본원에', name + '에'), ('본원의', name + '의'), ('본원도', name + '도'), ('본원을', name + ('을' if j else '를')), ('본원 ', name + ' '), ('본원', name)):
        t = t.replace(a, b)
    return t

def table(caption, rows):
    return ('<table class="info-table"><caption>' + E(caption) + '</caption><tbody>' +
            ''.join(f'<tr><th scope="row">{E(a)}</th><td>{E(b)}</td></tr>' for a, b in rows) + '</tbody></table>')

def main():
    domain = sys.argv[1]
    spec = json.loads((ROOT / 'tools/home_standard/specs' / f'{domain}.json').read_text(encoding='utf-8'))
    f = ROOT / 'sites' / domain / 'public/index.html'; s = f.read_text(encoding='utf-8'); log = []
    def one(pat, repl, flags=re.S):
        nonlocal s
        s2, n = re.subn(pat, repl, s, count=1, flags=flags)
        assert n == 1, f'패턴 없음: {pat[:60]}'
        s = s2
    if 'data-home-std=' in s:
        print(f'[{domain}] 이미 적용됨(data-home-std) — 다시 적용하려면 git checkout 후 실행'); return
    # ① H1 + ② 안내 블록(진료시간·위치·전화). 첫 문단(주제 도입)은 기존 문단을 그대로 둔다(spec intro 가 있으면 그 문단들로 교체).
    m = re.search(r'(<section class="hero">.*?<h1>)(.*?)(</h1>\s*)((?:<p class="sub">.*?</p>\s*)?)((?:<p>.*?</p>\s*){1,3})(</div>)', s, re.S)
    assert m, 'hero 구조가 다름'
    ib = spec['info']
    info = ('<dl class="home-info">' + ''.join(f'<div><dt>{E(k)}</dt><dd>{E(v)}</dd></div>' for k, v in (('진료시간', ib['hours']), ('위치', ib['addr']), ('전화', ib['phone']))) + '</dl>\n')
    paras = ''.join(f'<p>{E(x)}</p>' for x in spec['intro']) + '\n' if spec.get('intro') else m.group(5)
    sub = '' if spec.get('drop_sub') else m.group(4)
    s = s[:m.start()] + m.group(1) + E(spec['h1']) + m.group(3) + info + sub + paras + m.group(6) + s[m.end():]
    s = s.replace('<section class="hero">', '<section class="hero" data-home-std="2026-11-26">', 1)
    log.append('H1 · 안내 블록' + (f' · 첫 문단 {len(spec["intro"])}개 교체' if spec.get('intro') else ' · 기존 문단 유지'))
    # 화법: "저희", "본원" → 병원 이름. 제3자 인용 표현 삭제. (본문 <main> 안에서만)
    a0 = s.find('<main'); b0 = s.find('</main>'); body = s[a0:b0]; n0 = len(re.findall(r'저희|본원', body))
    body = voice(body, spec['name'])
    for pat, rep in THIRD: body = re.sub(pat, rep, body)
    left = re.findall(r'저희|본원', re.sub(r'<script.*?</script>', '', body, flags=re.S))
    s = s[:a0] + body + s[b0:]
    log.append(f'화법 {n0}곳 정리' + (f'(남음 {len(left)})' if left else ''))
    # ③ 병원 안내 dl → 표 2개
    m = re.search(r'(<h2>병원 안내</h2>.*?)<p>(.*?)</p>\s*<dl class="dl">(.*?)</dl>', s, re.S)
    assert m, '병원 안내 구조가 다름'
    pairs = re.findall(r'<dt>(.*?)</dt><dd>(.*?)</dd>', m.group(3), re.S)
    keep = [(html.unescape(re.sub(r'<[^>]+>', '', a)), html.unescape(re.sub(r'<[^>]+>', '', b))) for a, b in pairs if re.sub(r'<[^>]+>', '', a).strip() in spec.get('keep_rows', [])]
    block = (m.group(1) + '<p>' + E(spec['clinic_intro']) + '</p>\n' + table(spec['name'] + ' 진료시간', spec['hours']) + '\n' +
             table('병원 안내', spec['facts'] + keep))
    s = s[:m.start()] + block + s[m.end():]
    log.append(f'진료시간 표 {len(spec["hours"])}줄 · 병원 안내 표 {len(spec["facts"]) + len(keep)}줄')
    # ⑤ 해외 링크
    n = 0
    for dom in spec.get('drop_link_domains', []):
        s, k = re.subn(r'<li>\s*<a href="https?://(?:www\.)?' + re.escape(dom) + r'[^"]*"[^>]*>.*?</a>.*?</li>', '', s, flags=re.S); n += k
    if spec.get('drop_link_domains'): log.append(f'해외 링크 {n}개 삭제'); assert n >= 1, '삭제할 링크를 못 찾음'
    # ⑥ 문장 치환
    for a, b in spec.get('replace', []):
        assert s.count(a) >= 1, f'치환 대상 없음: {a[:40]}'
        s = s.replace(a, b)
    if spec.get('replace'): log.append(f'문장 치환 {len(spec["replace"])}건')
    # ④ FAQ (비용 섹션 앞)
    # 기존 홈 FAQ(<div class="faq …">) 문항은 새 FAQ 뒤에 합쳐 한 군데로(spec drop_old_faq 에 걸리는 겹치는 문항은 뺌). 기존 FAQ 묶음은 지운다.
    old = re.search(r'\s*<div class="faq[^"]*">(.*?)</div>', s, re.S)
    if old:
        T = lambda x: html.unescape(re.sub(r'<[^>]+>', '', x)).strip()
        olds = [(T(q), T(a)) for q, a in re.findall(r'<details[^>]*>\s*<summary>(.*?)</summary>\s*<p>(.*?)</p>\s*</details>', old.group(1), re.S)]
        kept = [(q, a) for q, a in olds if not any(k in q for k in spec.get('drop_old_faq', []))]
        spec['faq'] = [tuple(x) for x in spec['faq']] + kept
        s = s[:old.start()] + s[old.end():]
        log.append(f'기존 FAQ {len(olds)}문항 중 {len(kept)}문항 합침')
    faq = ('<section class="section" id="home-faq-own">\n  <div class="wrap narrow">\n    <p class="eyebrow">FAQ</p>\n    <h2>자주 묻는 질문</h2>\n    <div class="faq">\n      ' +
           ''.join(f'<details><summary>{E(q)}</summary><p>{E(a)}</p></details>' for q, a in spec['faq']) + '\n    </div>\n  </div>\n</section>\n\n')
    m = re.search(r'<section class="section[^"]*">\s*<div class="wrap narrow">\s*<p class="eyebrow">Budget', s)
    assert m, '비용 섹션 위치를 못 찾음'
    s = s[:m.start()] + faq + s[m.start():]
    ld = {'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in spec['faq']]}
    s = s.replace('</head>', CSS + '<script type="application/ld+json" id="home-faq-schema">' + json.dumps(ld, ensure_ascii=False).replace('<', '\\u003c') + '</script>\n</head>', 1)
    log.append(f'FAQ {len(spec["faq"])}개 + FAQPage')
    f.write_text(s, encoding='utf-8')
    # ⑦ description
    hp = ROOT / 'tools/deploy/home_descriptions.json'; raw = hp.read_text(encoding='utf-8'); d = json.loads(raw)
    d['descriptions'][domain] = spec['description']
    hp.write_text(json.dumps(d, ensure_ascii=False, indent=1) + ('\n' if raw.endswith('\n') else ''), encoding='utf-8')
    print(f'[{domain}] ' + ' · '.join(log) + f' · description {len(spec["description"])}자')

if __name__ == '__main__':
    main()

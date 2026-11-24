#!/usr/bin/env python3
"""map_hook.py — 병원·정보 사이트 홈의 '오시는 길' 칸 아래(병원 안내 바로 위)에 구글 지도를 넣는다. 빌드 출력에만 적용, 멱등.
usage: map_hook.py <sites/<도메인> 경로>
  - 주소: '오시는 길' 제목 다음에 나오는 첫 문단(도로명 주소)을 그대로 쓴다. 괄호 안 부가 설명은 검색어에서만 뺀다.
  - 위치: '오시는 길' 칸의 버튼 줄(전화·네이버 플레이스·공식 홈페이지)이 끝난 바로 뒤. 버튼 줄을 못 찾으면 그 칸의 끝.
  - 이미 구글 지도 iframe 이 있는 홈, '오시는 길' 제목이 없는 홈, 마케팅 사이트는 건드리지 않는다.
  - 사용자 지시(2026-11-24): 27곳 홈 '오시는 길' 아래에 구글 지도 삽입.
"""
import html, json, re, sys
from pathlib import Path
from urllib.parse import quote

MARK = 'class="home-map"'


def main():
    site = Path(sys.argv[1]).resolve()
    sj = json.loads((site / 'site.json').read_text(encoding='utf-8'))
    domain = sj['domain']
    if sj.get('group') not in ('hospital', 'info', 'wp'):
        print(f'[{domain}] map: 대상 아님'); return
    f = site / sj['dist'] / 'index.html'
    if not f.exists():
        print(f'[{domain}] map: 홈 없음'); return
    s = f.read_text(encoding='utf-8')
    if MARK in s or re.search(r'<iframe[^>]+google\.[a-z.]+/maps', s):
        print(f'[{domain}] map: 이미 있음'); return
    h = p = addr = None
    for h in re.finditer(r'<h2[^>]*>(?:(?!</h2>).){0,80}?오시는 길\s*</h2>', s):
        p = re.compile(r'<p[^>]*>(.*?)</p>', re.S).search(s, h.end())
        if not p or p.start() - h.end() > 400: continue
        a = html.unescape(re.sub(r'<[^>]+>', '', p.group(1))).strip()
        if len(a) <= 70 and re.search(r'(시|군|구)\s.*(로|길)\s?\d', a): addr = a; break
    if not addr:
        print(f'[{domain}] map: 오시는 길 주소를 못 찾음 → 건너뜀'); return
    q = re.sub(r'\s+', ' ', re.sub(r'\([^)]*\)', ' ', addr)).strip()
    # 병원 이름을 함께 검색해 지도에 병원 장소 카드(이름·지도에서 열기)가 뜨게 한다
    hname = html.unescape(re.sub(r'<[^>]+>', '', h.group(0))).replace('오시는 길', '').strip()
    road = re.match(r'.*?(?:로|길)(?:\d+번?길)?\s\d+(?:-\d+)?', q)   # 층·호수는 검색어에서 뺀다(장소 찾기 방해)
    if road: q = road.group(0)
    if hname: q = hname + ' ' + q
    # 다음 제목(병원 안내 등) 전까지가 '오시는 길' 칸
    nxt = re.compile(r'<h2[\s>]').search(s, p.end())
    end = nxt.start() if nxt else len(s)
    block = s[p.end():end]
    pos = None
    m = None
    for m in re.finditer(r'바로가기[^<]*(?:</strong>|</span>)?\s*</a>\s*</div>', block):
        pass
    if m:
        pos = p.end() + m.end()
    else:
        c = block.rfind('</section>')
        if c < 0:
            print(f'[{domain}] map: 넣을 자리를 못 찾음 → 건너뜀'); return
        pos = p.end() + c
    name = html.escape(sj.get('name', domain), quote=True)
    src = 'https://maps.google.com/maps?q=' + quote(q) + '&z=16&hl=ko&output=embed'
    tag = (f'<div {MARK} style="margin:28px 0 0;overflow:hidden;line-height:0">'
           f'<iframe src="{html.escape(src, quote=True)}" title="{name} 위치 지도" width="100%" height="480" '
           f'style="border:0;display:block;width:100%" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe></div>')
    f.write_text(s[:pos] + tag + s[pos:], encoding='utf-8')
    print(f'[{domain}] map: 구글 지도 삽입 (주소: {q})')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""desc_hook.py — 홈의 검색 설명 문구(meta description, og:description, twitter:description)를 home_descriptions.json 값으로 바꾼다.
usage: desc_hook.py <sites/<도메인> 경로>   빌드 출력의 index.html 에만 적용, 멱등. 목록에 없거나 hold 인 사이트는 건드리지 않는다.
"""
import html, json, re, sys
from pathlib import Path


def main():
    site = Path(sys.argv[1]).resolve()
    sj = json.loads((site / 'site.json').read_text(encoding='utf-8')); domain = sj['domain']
    cfg = json.loads((Path(__file__).resolve().parent / 'home_descriptions.json').read_text(encoding='utf-8'))
    desc = cfg.get('descriptions', {}).get(domain)
    if not desc or domain in cfg.get('hold', []):
        print(f'[{domain}] desc: 대상 아님'); return
    f = site / sj['dist'] / 'index.html'
    if not f.exists(): print(f'[{domain}] desc: 홈 없음'); return
    s = f.read_text(encoding='utf-8'); v = html.escape(desc, quote=True); n = 0
    for attr, key in (('name', 'description'), ('property', 'og:description'), ('name', 'twitter:description'), ('property', 'twitter:description')):
        s, k = re.subn(r'(<meta\s+' + attr + r'="' + re.escape(key) + r'"\s+content=")[^"]*(")', lambda m: m.group(1) + v + m.group(2), s)
        n += k
    if not n: print(f'[{domain}] desc: 설명 태그를 못 찾음 → 건너뜀'); return
    f.write_text(s, encoding='utf-8'); print(f'[{domain}] desc: 설명 문구 {n}곳 교체')


if __name__ == '__main__':
    main()

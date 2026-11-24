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
    # 사이트 이름: 검색 결과 윗줄에 병원명 없이 키워드만 보이게(제목·og:site_name·WebSite 이름) — 사용자 지시 2026-11-24 22:43
    kw = desc.split(' | ')[0].strip(); kv = html.escape(kw, quote=True); t = 0
    s, k = re.subn(r'(<title[^>]*>).*?(</title>)', lambda m: m.group(1) + kv + m.group(2), s, count=1, flags=re.S); t += k
    for attr, key in (('property', 'og:title'), ('name', 'twitter:title'), ('property', 'twitter:title'), ('property', 'og:site_name'),
                      ('name', 'application-name'), ('name', 'apple-mobile-web-app-title')):
        s, k = re.subn(r'(<meta\s+' + attr + r'="' + re.escape(key) + r'"\s+content=")[^"]*(")', lambda m: m.group(1) + kv + m.group(2), s)
        t += k

    def ld(m):
        nonlocal t
        try: o = json.loads(m.group(2))
        except Exception: return m.group(0)
        nodes = o.get('@graph', [o]) if isinstance(o, dict) else (o if isinstance(o, list) else [])
        hit = False
        for nd in nodes:
            if isinstance(nd, dict) and nd.get('@type') == 'WebSite' and (nd.get('name') != kw or 'alternateName' in nd):
                nd['name'] = kw; nd.pop('alternateName', None); hit = True
        if not hit: return m.group(0)
        t += 1
        return m.group(1) + json.dumps(o, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + m.group(3)
    s = re.sub(r'(<script[^>]*application/ld\+json[^>]*>)(.*?)(</script>)', ld, s, flags=re.S)
    print(f'[{domain}] desc: 사이트 이름 {t}곳을 "{kw}" 로')
    f.write_text(s, encoding='utf-8'); print(f'[{domain}] desc: 설명 문구 {n}곳 교체')


if __name__ == '__main__':
    main()

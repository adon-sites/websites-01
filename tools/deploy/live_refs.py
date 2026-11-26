#!/usr/bin/env python3
"""live_refs.py — 실제 주소에서 홈과 카드 6쪽을 열어 카드 이미지 참조를 센다(읽기 전용).
usage: live_refs.py <도메인,도메인,…> [새 파일 정규식] [옛 파일 정규식]
사이트마다: 홈의 ItemList 에서 카드 6쪽 주소를 읽고, 7쪽 각각에서 새 이름·옛 이름 참조 수(HTML 전체 문자열 기준)와
홈 카드 img·og:image·ItemList image 가 새 이름인지 세고, 새 이름 이미지 파일을 실제 주소로 요청해 200 이 아닌 것을 센다. 결과는 annotation 한 줄(JSON)."""
import json, re, sys, urllib.request
UA = {'User-Agent': 'Mozilla/5.0 (compatible; adon-livecheck/1.0)', 'Cache-Control': 'no-cache'}
def get(url, method='GET'):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA, method=method), timeout=30) as r:
            return r.status, (r.read() if method == 'GET' else b''), r.headers.get('content-type', '')
    except urllib.error.HTTPError as e: return e.code, b'', ''
    except Exception as e: return 0, str(e).encode(), ''
def main():
    doms = [d.strip() for d in sys.argv[1].split(',') if d.strip()]
    new = re.compile(sys.argv[2] if len(sys.argv) > 2 else r'carousel-0[1-6]-860-v2\.jpg'); old = re.compile(sys.argv[3] if len(sys.argv) > 3 else r'carousel-0[1-6]-860\.jpg')
    for d in doms:
        st, body, _ = get(f'https://{d}/'); home = body.decode('utf-8', 'replace'); cards = []
        for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', home, re.S):
            try: j = json.loads(m.group(1))
            except Exception: continue
            stack = [j]
            while stack:
                x = stack.pop()
                if isinstance(x, list): stack += x
                elif isinstance(x, dict):
                    if x.get('@type') == 'ItemList' and not cards: cards = sorted(((e.get('position'), e.get('url'), e.get('image')) for e in x.get('itemListElement', [])), key=lambda t: t[0] or 0)
                    stack += list(x.values())
        pages = [f'https://{d}/'] + [c[1] for c in cards]; rep = {'site': d, 'home_status': st, 'pages': len(pages), 'new_refs': 0, 'old_refs': 0, 'page_not200': [], 'og_new': 0, 'og_other': [], 'itemlist_image_new': sum(1 for c in cards if c[2] and new.search(c[2])), 'itemlist_items': len(cards), 'home_card_img_new': len(set(new.findall(' '.join(re.findall(r'<img\b[^>]*>', home)))))}
        imgs = set()
        for u in pages:
            s_, b, _ = get(u); t = b.decode('utf-8', 'replace')
            if s_ != 200: rep['page_not200'].append([u, s_]); continue
            rep['new_refs'] += len(new.findall(t)); rep['old_refs'] += len(old.findall(t)); imgs |= set(new.findall(t))
            og = re.search(r'<meta\b[^>]*property="og:image"[^>]*content="([^"]*)"', t) or re.search(r'<meta\b[^>]*content="([^"]*)"[^>]*property="og:image"', t)
            if og and new.search(og.group(1)): rep['og_new'] += 1
            else: rep['og_other'].append([u, og.group(1) if og else None])
        bad = []
        for name in sorted(imgs):
            s_, b, ct = get(f'https://{d}/images/{name}')
            if s_ != 200 or not ct.startswith('image/') or len(b) < 1000: bad.append([name, s_, ct, len(b)])
        rep['images_checked'] = len(imgs); rep['images_not200'] = bad
        print('::notice::LIVEREFS ' + json.dumps(rep, ensure_ascii=False))
if __name__ == '__main__': main()

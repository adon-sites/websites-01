#!/usr/bin/env python3
"""캐러셀 2-B 사후 처리(애드온 마케팅용, 멱등): 홈 카드 6장이 가리키는 페이지의 대표 이미지 = 그 카드 JPG.

사용: python3 -I patch_cards.py <dist>
홈 index.html 의 feature-grid 에서 (href, src, alt) 6개를 읽어 각 페이지에
  - og:image / og:image:width / og:image:height / og:image:alt / twitter:card / twitter:image
  - JSON-LD: Article·BlogPosting 이면 image=ImageObject + mainEntityOfPage=WebPage{primaryImageOfPage}; WebPage 계열이면 image+primaryImageOfPage; 없으면 WebPage 노드 추가
  - 본문: 카드 JPG 가 없으면 첫 <h1> 뒤에 <figure class="cover guide-cover"> 삽입, 옛 carousel 이미지 태그가 있으면 교체(단일 src)
각 빌드 끝에서 실행한다(build.py 훅). 페이지가 정적으로 보존되는 사이트에서도 동작.
"""
import json, re, sys, html
from pathlib import Path

D = Path(sys.argv[1]).resolve()
home = (D / 'index.html').read_text(encoding='utf-8')
origin = re.search(r'<link rel="canonical" href="(https?://[^/"]+)', home).group(1)
grid = re.search(r'<section class="feature-grid[^"]*".*?</section>', home, re.S).group(0)
cards = []
for m in re.finditer(r'<a class="feature" href="([^"]+)">\s*(<img\b[^>]*>)', grid, re.S):
    tag = m.group(2); a = dict(re.findall(r'\b([\w-]+)="([^"]*)"', tag))
    cards.append((m.group(1), a.get('data-speed-original', a.get('src', '')), a.get('alt', '')))
assert len(cards) == 6, f'카드 6장 파싱 실패: {len(cards)}'
OLD = re.compile(r'(?:/images/optimized/|/images/first-visit/|/images/)carousel-0\d(?!-860)[^"\s]*')
changed = []
for href, src, alt in cards:
    if not src.endswith('-860.jpg'): continue
    p = D / href.strip('/') / 'index.html'
    if not p.is_file(): print('MISSING', href); continue
    s = p.read_text(encoding='utf-8'); before = s
    absu = origin + src; esc = html.escape(alt, quote=True)
    # 옛 캐러셀 이미지 경로 전부 → 새 JPG
    s = OLD.sub(src, s)
    # og / twitter
    s = re.sub(r'<meta property="og:image(?::width|:height|:alt)?" content="[^"]*">', '', s)
    s = re.sub(r'<meta name="twitter:(?:card|image)" content="[^"]*">', '', s)
    metas = (f'<meta property="og:image" content="{absu}"><meta property="og:image:width" content="860"><meta property="og:image:height" content="860">'
             f'<meta property="og:image:alt" content="{esc}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{absu}">')
    s = s.replace('</head>', metas + '</head>', 1)
    # JSON-LD
    io = {'@type': 'ImageObject', 'url': absu, 'width': 860, 'height': 860, 'caption': alt}
    if 'primaryImageOfPage' not in s:
        scripts = list(re.finditer(r'<script type="application/ld\+json">(.*?)</script>', s, re.S))
        done = False
        for m in scripts:
            try: obj = json.loads(m.group(1))
            except Exception: continue
            nodes = obj if isinstance(obj, list) else (obj.get('@graph') if isinstance(obj, dict) and '@graph' in obj else [obj])
            for n in nodes:
                t = n.get('@type'); t = t if isinstance(t, str) else (t[0] if t else '')
                if t in ('Article', 'BlogPosting', 'NewsArticle'):
                    n['image'] = io; n['mainEntityOfPage'] = {'@type': 'WebPage', '@id': origin + href, 'primaryImageOfPage': io}; done = True; break
                if t in ('WebPage', 'MedicalWebPage', 'CollectionPage', 'ItemPage'):
                    n['image'] = io; n['primaryImageOfPage'] = io; done = True; break
            if done:
                s = s[:m.start(1)] + json.dumps(obj, ensure_ascii=False) + s[m.end(1):]; break
        if not done:
            wp = {'@context': 'https://schema.org', '@type': 'WebPage', '@id': origin + href + '#webpage', 'url': origin + href, 'isPartOf': {'@id': origin + '/#website'}, 'image': io, 'primaryImageOfPage': io}
            s = s.replace('</head>', '<script type="application/ld+json">' + json.dumps(wp, ensure_ascii=False) + '</script></head>', 1)
    else:
        # 이미 있으면 url 만 맞춘다(옛 경로 치환은 위에서 처리)
        pass
    # 본문 hero
    head_end = s.find('</head>'); body = s[head_end:]
    if src not in body:
        fig = f'<figure class="cover guide-cover"><img src="{src}" alt="{esc}" width="860" height="860" loading="eager" fetchpriority="high"></figure>'
        m = re.search(r'</h1>', body)
        if m: body = body[:m.end()] + fig + body[m.end():]
        s = s[:head_end] + body
    else:
        # 본문 안의 카드 이미지 태그에서 srcset/sizes 제거, 크기 860 고정
        def fix(m):
            t = m.group(0)
            if src not in t: return t
            t = re.sub(r'\s+(?:srcset|sizes|data-speed-original)="[^"]*"', '', t)
            t = re.sub(r'\swidth="\d+"', ' width="860"', t); t = re.sub(r'\sheight="\d+"', ' height="860"', t)
            return t
        s = s[:head_end] + re.sub(r'<img\b[^>]*>', fix, s[head_end:])
    if s != before:
        p.write_text(s, encoding='utf-8'); changed.append(href)

# ---- 홈: 노출된 5곳과 같은 엔티티 구성 (조직.image/logo + WebSite + WebPage.primaryImageOfPage), 멱등 ----
hp = D / 'index.html'; h = hp.read_text(encoding='utf-8'); h0 = h
href1, src1, alt1 = cards[0]
abs1 = origin + src1
logo_png = D / 'images/brand/adon-logo.png'
logo_url = origin + '/images/brand/adon-logo.png' if logo_png.is_file() else origin + '/images/brand/adon-logo.svg'
title = html.unescape(re.search(r'<title>(.*?)</title>', h, re.S).group(1)).strip()
desc = html.unescape((re.search(r'<meta name="description" content="([^"]*)"', h) or [None, ''])[1])
mscripts = list(re.finditer(r'<script type="application/ld\+json">(.*?)</script>', h, re.S))
org_id = None
for m in mscripts:
    try: obj = json.loads(m.group(1))
    except Exception: continue
    nodes = obj if isinstance(obj, list) else (obj.get('@graph') if isinstance(obj, dict) and '@graph' in obj else [obj])
    hit = False
    for n in nodes:
        if n.get('@type') in ('Organization', 'ProfessionalService', 'LocalBusiness') and n.get('@id', '').endswith('#organization'):
            org_id = n['@id']
            if n.get('image') != abs1 or n.get('logo') != logo_url:
                n['image'] = abs1; n['logo'] = logo_url; hit = True
    if hit:
        h = h[:m.start(1)] + json.dumps(obj, ensure_ascii=False) + h[m.end(1):]
        break
if org_id and '#website' not in h:
    kw = re.search(r'<meta name="keywords" content="([^",]*)', h)
    site_name = (kw.group(1).strip() if kw else title.split('|')[0].strip())
    ws = {'@context': 'https://schema.org', '@type': 'WebSite', '@id': origin + '/#website', 'name': site_name, 'alternateName': '애드온 AD-ON', 'url': origin + '/', 'inLanguage': 'ko-KR', 'publisher': {'@id': org_id}}
    io1 = {'@type': 'ImageObject', 'url': abs1, 'width': 860, 'height': 860, 'caption': alt1}
    wp = {'@context': 'https://schema.org', '@type': 'WebPage', '@id': origin + '/#webpage', 'url': origin + '/', 'name': title, 'description': desc, 'inLanguage': 'ko-KR', 'isPartOf': {'@id': origin + '/#website'}, 'about': {'@id': org_id}, 'image': io1, 'primaryImageOfPage': io1}
    h = h.replace('</head>', '<script type="application/ld+json">' + json.dumps(ws, ensure_ascii=False) + '</script><script type="application/ld+json">' + json.dumps(wp, ensure_ascii=False) + '</script></head>', 1)
if h != h0:
    hp.write_text(h, encoding='utf-8'); changed.append('/')
print(json.dumps({'patched': changed, 'cards': len(cards)}, ensure_ascii=False))

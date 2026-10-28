#!/usr/bin/env python3
"""cjwelldentalinfo.co.kr (청주웰치과 · 청주치과 정보 사이트) 정적 생성기.

입력: site-config.json, content/posts.json(이전 시점까지 공개된 글), content/posts/*.md(이후 추가 글),
      content/treatments.json(진료 안내 6종), homepage-original.json, homepage-cost-guide.json,
      homepage-image-variants.json, templates/*.css(라이브와 동일한 컴파일 CSS), public/(이미지·아이콘·favicon).
출력: dist/ 전체 (홈, about, visit, treatments/*, blog 목록·페이지·주제, articles/*, 404, robots, sitemap, rss).
마크업은 이전 Next.js(vinext) SSR 결과와 동일하게 맞추되 클라이언트 런타임(JS 청크·RSC payload·modulepreload)은 넣지 않는다.
"""
import json, re, pathlib, datetime, shutil, os, math, urllib.parse

R = pathlib.Path(__file__).resolve().parents[1]
VERIFY = os.environ.get('WELL_VERIFY') == '1'   # 라이브(쿼리 문자열 블로그 주소)와 바이트 비교용 출력 모드
D = R / ('dist-verify' if VERIFY else 'dist')
C = json.loads((R / 'site-config.json').read_text(encoding='utf-8'))
if VERIFY:
    C['blogUrlStyle'] = 'query'
    C['legacyQueryRedirectScript'] = False
TREATMENTS = json.loads((R / 'content/treatments.json').read_text(encoding='utf-8'))
HOME = json.loads((R / 'homepage-original.json').read_text(encoding='utf-8'))
COST = json.loads((R / 'homepage-cost-guide.json').read_text(encoding='utf-8'))
VARIANTS = json.loads((R / 'homepage-image-variants.json').read_text(encoding='utf-8'))
POSTS = json.loads((R / 'content/posts.json').read_text(encoding='utf-8'))

O = C['origin'].rstrip('/')
SITE_NAME = C['siteName']            # '청주치과'
LIVE = bool(C.get('indexingEnabled'))
KST = datetime.timezone(datetime.timedelta(hours=9))
T_BY_SLUG = {t['slug']: t for t in TREATMENTS}
T_BY_NAME = {t['name']: t for t in TREATMENTS}

# lib/clinic.ts
CLINIC = {'name': '청주웰치과의원', 'phone': '043-238-9201', 'phoneHref': 'tel:0432389201',
          'address': '충청북도 청주시 흥덕구 2순환로 1120 승리빌딩 3~5층', 'representative': '빙정호', 'businessNumber': '221-18-97112',
          'homepage': 'http://cjwelldental.co.kr/', 'instagram': 'https://www.instagram.com/cjwelldental/',
          'kakao': 'https://pf.kakao.com/_xiLHTj', 'naverPlace': 'https://naver.me/GUweAjlC'}
HOURS = [('월 · 수 · 금', '09:30 — 18:30', None), ('화 · 목', '09:30 — 21:00', '야간진료'), ('토 · 일', '09:30 — 17:00', None)]
BREAKS = [('평일 점심', '12:30 — 14:00'), ('토 · 일 점심', '13:00 — 14:00'), ('화 · 목 저녁', '18:30 — 19:00')]
REP_IMAGE = {'src': '/images/cheongju-well-representative.jpg', 'alt': '청주웰치과 건물과 의료진을 담은 병원 대표 이미지', 'width': 1200, 'height': 1200}
SESSIONS = [(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'], '09:30', '12:30'), (['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'], '14:00', '18:30'),
            (['Tuesday', 'Thursday'], '19:00', '21:00'), (['Saturday', 'Sunday'], '09:30', '13:00'), (['Saturday', 'Sunday'], '14:00', '17:00')]
DOCTORS = [('빙정호', '대표원장', '구강악안면외과 전문의'), ('이의묵', '대표원장', '구강악안면외과 전문의'), ('김지권', '원장', '치과교정과 전문의'), ('박상용', '원장', '치과보철과 전문의'),
           ('길기성', '원장', '치과보철과 전문의'), ('김지현', '원장', '일반의'), ('정지혜', '원장', '치과보철과 전문의'), ('이상윤', '원장', '통합치의학과 전문의'),
           ('김기원', '원장', '치과보철과 전문의'), ('김진형', '원장', '치주과 전문의'), ('이효경', '원장', '치과보철과 · 통합치의학과 전문의')]
ABOUT_TITLE = '청주치과 웰치과 소개'

def absolute(p): return O + p

# ---------- React SSR 호환 이스케이프 ----------
def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#x27;')
E = esc

def jsonld(data):
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c') + '</script>'

def iso_ms(dt):
    dt = dt.astimezone(datetime.timezone.utc)
    return dt.strftime('%Y-%m-%dT%H:%M:%S.') + f'{dt.microsecond // 1000:03d}Z'

def parse_iso(s):
    return datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))

def kst_long(dt):   # toLocaleDateString('ko-KR',{timeZone:'Asia/Seoul',year:'numeric',month:'long',day:'numeric'})
    k = dt.astimezone(KST); return f'{k.year}년 {k.month}월 {k.day}일'

def kst_short(dt):  # toLocaleDateString('ko-KR',{timeZone:'Asia/Seoul'})
    k = dt.astimezone(KST); return f'{k.year}. {k.month}. {k.day}.'

def utc_string(dt):  # Date.prototype.toUTCString
    u = dt.astimezone(datetime.timezone.utc)
    return u.strftime('%a, %d %b %Y %H:%M:%S GMT')

# ---------- 마크다운 글 로더 (content/posts/*.md) ----------
def _load_md(path):
    raw = path.read_text(encoding='utf-8'); assert raw.startswith('---\n'), path
    fm, body = raw[4:].split('\n---\n', 1); meta = {}
    for line in fm.splitlines():
        if ':' in line: k, v = line.split(':', 1); meta[k.strip()] = v.strip().strip('"').strip("'")
    secs = []; cur = None
    for line in body.strip().splitlines():
        if line.startswith('## '): cur = [line[3:].strip(), []]; secs.append(cur)
        elif cur is not None and line.strip(): cur[1].append(line.strip())
    assert 4 <= len(secs) <= 7, ('sections', path)
    sections = [{'heading': h, 'paragraphs': lines} for h, lines in secs]   # 줄(빈 줄 구분) 하나가 문단 하나
    t = T_BY_NAME.get(meta.get('category', ''))
    assert t, ('category must be one of ' + '/'.join(T_BY_NAME), path)
    assert re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00', meta['date']), ('date must be YYYY-MM-DDTHH:MM:SS+09:00', path)
    dt = datetime.datetime.fromisoformat(meta['date'])
    sources = [s.strip() for s in meta.get('sources', '').split(',') if s.strip()]
    return {'id': 'MD-' + path.stem, 'slug': path.stem, 'treatmentSlug': t['slug'], 'title': meta['title'], 'short_title': meta.get('short_title', ''),
            'description': meta['description'], 'sections': sections, 'sourceIds': sources, 'textOnly': True,
            'publishedAt': iso_ms(dt), 'origin': 'markdown'}

_md = sorted((R / 'content/posts').glob('*.md')) if (R / 'content/posts').exists() else []
_seen = {p['slug'] for p in POSTS}
for _f in _md:
    _p = _load_md(_f); assert _p['slug'] not in _seen, ('duplicate slug', _f); _seen.add(_p['slug']); POSTS.append(_p)

_now = datetime.datetime.now(datetime.timezone.utc)
_counts = {}
for _p in POSTS:
    if _p.get('origin') != 'markdown': continue   # 이전 시점 글(posts.json)은 당시 운영 규칙으로 이미 공개된 상태
    _day = parse_iso(_p['publishedAt']).astimezone(KST).date().isoformat(); _counts[_day] = _counts.get(_day, 0) + 1
assert all(v <= 30 for v in _counts.values()), 'KST daily new-article cap (30) exceeded'
_future = [p for p in POSTS if parse_iso(p['publishedAt']) > _now]
for _p in _future:
    _stale = D / 'articles' / (_p['slug'] + '.html')
    if _stale.exists(): _stale.unlink()
POSTS = [p for p in POSTS if p not in _future]
# publicArticles(): 색인 허용 상태에서만 글이 공개되며 공개 시각 오름차순(동일 시각은 파일 순서 유지).
ITEMS = sorted(POSTS, key=lambda p: parse_iso(p['publishedAt'])) if LIVE else []
for p in ITEMS: p['_at'] = parse_iso(p['publishedAt'])

# ---------- 공통 레이아웃 (app/layout.tsx + components/clinic-shell.tsx) ----------
GLOBAL_CSS = (R / 'templates/globals.css').read_text(encoding='utf-8')
COST_CSS = (R / 'templates/home-cost-guide.css').read_text(encoding='utf-8')
STYLE = '<style id="well-site-styles">' + GLOBAL_CSS + '</style>'
COST_STYLE = '<style data-home-cost-styles="true">' + COST_CSS + '</style>'
def _icon(name):   # `?raw` import → data:image/svg+xml,encodeURIComponent(svg)
    svg = (R / 'public/icons' / name).read_text(encoding='utf-8')
    return 'data:image/svg+xml,' + urllib.parse.quote(svg, safe="-_.!~*'()")
KAKAO_ICON = _icon('kakaotalk.svg'); INSTAGRAM_ICON = _icon('instagram.svg')

CARDS = [{'name': ABOUT_TITLE, 'url': '/about', 'image': '/images/clinic.jpg', 'alt': '청주웰치과가 위치한 승리빌딩 외관', 'description': '분과별 의료진과 병원 공간, 진료 철학을 만나보세요.', 'label': 'WELL DENTAL', 'width': 1000, 'height': 1000}]
CARDS += [{'name': t['title'], 'url': '/treatments/' + t['slug'], 'image': t['image'], 'alt': t['alt'], 'description': t['description'].replace('청주웰치과 ', ''), 'label': t['english'], 'width': 1000, 'height': 1000} for t in TREATMENTS if t['slug'] != 'jaw-joint']

LD_SITE = jsonld({'@context': 'https://schema.org', '@type': 'WebSite', '@id': absolute('/#website'), 'name': SITE_NAME, 'alternateName': C['alternateNames'], 'url': absolute('/'), 'inLanguage': 'ko-KR', 'publisher': {'@id': absolute('/#clinic')}})
LD_LIST = jsonld({'@context': 'https://schema.org', '@type': 'ItemList', 'name': '청주치과 주요 진료와 청주웰치과 소개', 'numberOfItems': len(CARDS), 'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'name': c['name'], 'url': absolute(c['url']), 'image': absolute(c['image'])} for i, c in enumerate(CARDS)]})
LD_CLINIC = jsonld({'@context': 'https://schema.org', '@type': 'Dentist', '@id': absolute('/#clinic'), 'name': CLINIC['name'], 'url': absolute('/'), 'telephone': CLINIC['phone'], 'image': absolute('/images/clinic.jpg'),
                    'address': {'@type': 'PostalAddress', 'addressCountry': 'KR', 'addressRegion': '충청북도', 'addressLocality': '청주시 흥덕구', 'streetAddress': '2순환로 1120 승리빌딩 3~5층'},
                    'openingHoursSpecification': [{'@type': 'OpeningHoursSpecification', 'dayOfWeek': ['https://schema.org/' + d for d in days], 'opens': o, 'closes': c} for days, o, c in SESSIONS],
                    'sameAs': [CLINIC['homepage'], CLINIC['instagram']]})

def header(home=False):
    h = f'<header class="site-header"><div class="header-inner"><a class="site-brand" href="/" aria-label="{SITE_NAME} 홈">{SITE_NAME}</a>'
    if home: h += f'<nav class="homepage-keyword" aria-label="공식 병원 안내"><a href="{CLINIC["homepage"]}" target="_blank" rel="noopener noreferrer">{C["backlinkLabel"]}</a></nav>'
    else: h += f'<nav aria-label="주요 메뉴"><a href="/#care">진료 안내</a><a href="/about">웰치과 소개</a><a href="/blog">블로그</a><a href="/visit">오시는 길</a></nav><a class="header-call" href="{CLINIC["phoneHref"]}">043.238.9201</a>'
    return h + '</div></header>'
RAIL = (f'<aside class="contact-rail" aria-label="상담 및 소식 바로가기"><a href="{CLINIC["phoneHref"]}"><span class="rail-icon" aria-hidden="true">☎</span><span>전화 상담</span></a>'
        f'<a href="{CLINIC["kakao"]}" target="_blank" rel="noopener noreferrer"><span class="rail-icon kakao"><img src="{E(KAKAO_ICON)}" alt="" width="24" height="24"/></span><span>카카오톡</span></a>'
        f'<a href="{CLINIC["naverPlace"]}" target="_blank" rel="noopener noreferrer"><span class="rail-icon naver" aria-hidden="true">N</span><span>네이버지도</span></a>'
        f'<a href="{CLINIC["instagram"]}" target="_blank" rel="noopener noreferrer"><span class="rail-icon instagram"><img src="{E(INSTAGRAM_ICON)}" alt="" width="24" height="24"/></span><span>인스타그램</span></a>'
        f'<a href="{CLINIC["homepage"]}" target="_blank" rel="noopener noreferrer"><span class="rail-icon" aria-hidden="true">⌂</span><span>기존 홈페이지</span></a></aside>')
YEAR = datetime.datetime.now(datetime.timezone.utc).year
FOOTER = (f'<footer class="site-footer"><div class="footer-inner"><div><p class="footer-brand">청주웰치과의원</p><p>{CLINIC["address"]}</p><p>대표자 <!-- -->{CLINIC["representative"]}<!-- --> · 사업자등록번호 <!-- -->{CLINIC["businessNumber"]}</p><p>대표전화 <a href="{CLINIC["phoneHref"]}">{CLINIC["phone"]}</a></p></div>'
          f'<div class="footer-links"><a href="/about">병원 소개</a><a href="/blog">블로그</a><a href="/visit">진료시간·오시는 길</a><a href="{CLINIC["homepage"]}" target="_blank" rel="noopener noreferrer">기존 홈페이지 ↗</a></div>'
          f'<p class="medical-note">이 안내는 일반적인 치과 정보를 제공합니다. 치료의 적용 여부와 과정은 진찰 결과 및 개인 상태에 따라 달라질 수 있습니다.</p><p class="copyright">© <!-- -->{YEAR}<!-- --> <!-- -->{SITE_NAME}<!-- --> · <!-- -->{CLINIC["name"]}</p></div></footer>')
CONTACT_BOX = (f'<section class="contact-box"><div><p class="eyebrow">CONTACT WELL</p><h2>궁금한 점은 편하게 문의하세요.</h2><p>증상과 진료 일정을 확인하고 방문을 준비할 수 있습니다.</p><div class="inline-links contact-social"><a href="{CLINIC["kakao"]}" target="_blank" rel="noopener noreferrer"><img src="{E(KAKAO_ICON)}" alt="" width="22" height="22"/>카카오톡 상담 ↗</a><a href="{CLINIC["naverPlace"]}" target="_blank" rel="noopener noreferrer">네이버지도 ↗</a></div></div>'
               f'<a class="button" href="{CLINIC["phoneHref"]}">전화 상담 <span>{CLINIC["phone"]}</span></a></section>')
HOME_LINK = f'<p data-carousel-home-link="true" style="margin-top:32px;padding-top:20px;border-top:1px solid #dce4e8"><a href="{C["backlinkOrigin"]}" style="text-decoration:underline;text-underline-offset:3px;font-weight:600">{C["backlinkLabel"]}</a></p>'
def breadcrumb(label, parent=None):
    p = f'<a href="{parent[1]}">{parent[0]}</a><span>/</span>' if parent else ''
    return f'<nav class="breadcrumb" aria-label="현재 위치"><a href="/">홈</a><span>/</span>{p}<span aria-current="page">{E(label)}</span></nav>'
HOURS_HTML = '<div class="hours"><p class="holiday-note">공휴일에도 진료합니다.</p>' + ''.join(f'<div class="hours-row"><span>{d}</span><strong>{t}</strong>' + (f'<small>{n}</small>' if n else '') + '</div>' for d, t, n in HOURS) + '<dl class="break-times">' + ''.join(f'<div><dt>{d}</dt><dd>{t}</dd></div>' for d, t in BREAKS) + '</dl><p>공휴일의 상세 진료시간과 의료진별 일정, 접수 마감시간은 방문 전에 전화로 확인해 주세요.</p></div>'

ROBOTS = 'index, follow, max-image-preview:large' if LIVE else 'noindex, nofollow'
ICONS = '<link rel="icon" href="/favicon.svg?v=well-symbol-1" type="image/svg+xml" sizes="any"/><link rel="icon" href="/images/cheongju-well-favicon-32.png" type="image/png" sizes="32x32"/><link rel="icon" href="/images/cheongju-well-favicon-192.png" type="image/png" sizes="192x192"/>'
VERIFICATION_META = f'<meta name="naver-site-verification" content="{E(C["naverSiteVerification"])}"/>' if C.get('naverSiteVerification') else ''

def head_meta(title, description, path, image, alt, og_type='website', published=None, robots=None):
    url = absolute(path)
    img = absolute(image)
    parts = [f'<title>{E(title)}</title>', f'<meta name="description" content="{E(description)}"/>', f'<meta name="application-name" content="{SITE_NAME}"/>',
             f'<meta name="robots" content="{robots or ROBOTS}"/>',
             f'<meta property="og:title" content="{E(title)}"/>', f'<meta property="og:description" content="{E(description)}"/>',
             f'<meta property="og:url" content="{E(url)}"/>', f'<meta property="og:site_name" content="{SITE_NAME}"/>',
             f'<meta property="og:type" content="{og_type}"/>', '<meta property="og:locale" content="ko_KR"/>']
    if published: parts.append(f'<meta property="article:published_time" content="{published}"/>')
    parts += [f'<meta property="og:image" content="{E(img)}"/>', f'<meta property="og:image:alt" content="{E(alt)}"/>',
              '<meta name="twitter:card" content="summary_large_image"/>', f'<meta name="twitter:title" content="{E(title)}"/>',
              f'<meta name="twitter:description" content="{E(description)}"/>', f'<meta name="twitter:image" content="{E(img)}"/>', f'<meta name="twitter:image:alt" content="{E(alt)}"/>',
              ICONS, f'<link rel="canonical" href="{E(url)}"/>', VERIFICATION_META]
    return ''.join(parts)

def preload(src, fetch_priority=None, srcset=None, sizes=None):   # React 19 가 lazy 가 아닌 <img> 에 대해 넣는 preload
    if srcset: return f'<link rel="preload" as="image" imageSrcSet="{E(srcset)}" imageSizes="{E(sizes)}"' + (f' fetchPriority="{fetch_priority}"' if fetch_priority else '') + '/>'
    return f'<link rel="preload" href="{src}" as="image"' + (f' fetchPriority="{fetch_priority}"' if fetch_priority else '') + '/>'

def page(meta, body, home=False, preloads='', head_extra=''):
    head = '<!DOCTYPE html><html lang="ko"><head><meta charSet="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>' + preloads + meta + STYLE
    head += (LD_SITE + LD_LIST if home else '') + LD_CLINIC + head_extra + '</head>'
    return head + '<body><a class="skip-link" href="#main">본문으로 건너뛰기</a>' + header(home) + body + RAIL + FOOTER + '</body></html>'

def write(path, content):
    p = D / path; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(content, encoding='utf-8')

# ---------- URL ----------
QUERY_URLS = C.get('blogUrlStyle') == 'query'
def blog_path(topic=None, n=1):   # lib/blog-navigation.ts blogUrl(topic, page)
    if topic: topic = urllib.parse.quote_plus(topic, safe='*')   # URLSearchParams 와 같은 퍼센트 인코딩 (비ASCII treatmentSlug)
    if QUERY_URLS:
        q = []
        if topic: q.append('topic=' + topic)
        if n > 1: q.append('page=' + str(n))
        return '/blog' + ('?' + '&'.join(q) if q else '')
    p = '/blog'
    if topic: p += '/topic/' + topic
    if n > 1: p += '/page/' + str(n)
    return p

def blog_file(topic=None, n=1):
    return blog_path(topic, n).lstrip('/') + '.html'

# ---------- 글 페이지 (articles/[slug]/page.tsx) ----------
def sections_html(sections):
    return ''.join(f'<section><h2>{E(s["heading"])}</h2>' + ''.join(f'<p>{E(p)}</p>' for p in s['paragraphs']) + '</section>' for s in sections)

def post_page(a):
    t = T_BY_SLUG.get(a['treatmentSlug'])
    related = [p for p in ITEMS if p['id'] != a['id'] and p['treatmentSlug'] == a['treatmentSlug']][-3:][::-1]
    sources = [s for s in a['sourceIds'] if s.startswith('https://')]
    ld = {'@context': 'https://schema.org', '@type': 'BlogPosting', 'headline': a['title'], 'image': absolute(REP_IMAGE['src']), 'description': a['description'], 'datePublished': a['publishedAt'], 'inLanguage': 'ko-KR', 'mainEntityOfPage': absolute('/articles/' + a['slug']), 'author': {'@type': 'Organization', 'name': '청주웰치과'}, 'publisher': {'@type': 'Organization', 'name': '청주웰치과의원', 'url': absolute('/')}}
    body = '<main id="main" class="detail-main article-main">' + jsonld(ld) + breadcrumb('건강정보', ('블로그', '/blog'))
    body += f'<header class="detail-header"><p class="eyebrow">{E(t["name"]) if t else ""}</p><h1>{E(a["title"])}</h1><p>{E(a["description"])}</p><time dateTime="{a["publishedAt"]}">{kst_short(a["_at"])}<!-- --> · 청주웰치과</time></header>'
    body += '<article class="prose article-prose">'
    if not a.get('textOnly'): body += f'<img class="article-representative" src="{REP_IMAGE["src"]}" alt="{E(REP_IMAGE["alt"])}" width="{REP_IMAGE["width"]}" height="{REP_IMAGE["height"]}"/>'
    body += sections_html(a['sections'])
    if t: body += f'<a class="related-treatment" href="/treatments/{t["slug"]}">{E(t["name"])}<!-- --> 진료 안내 함께 보기 ↗</a>'
    if sources: body += '<div class="source-note"><strong>참고 자료</strong><ul>' + ''.join(f'<li><a href="{E(u)}" target="_blank" rel="noopener noreferrer">{E(urllib.parse.urlsplit(u).hostname)}<!-- --> · 참고 자료 <!-- -->{i + 1}<!-- --> ↗</a></li>' for i, u in enumerate(sources)) + '</ul></div>'
    if related: body += '<section class="related-posts"><h2>함께 읽는 치아 건강정보</h2><ul>' + ''.join(f'<li><a href="/articles/{p["slug"]}">{E(p["title"])}</a></li>' for p in related) + '</ul></section>'
    body += '<a class="button secondary" href="/blog">블로그 목록으로 돌아가기</a></article>' + CONTACT_BOX + HOME_LINK + '</main>'
    doc_title = a['short_title'] if a.get('short_title') else a['title'] + ' | 청주웰치과'
    meta = head_meta(doc_title, a['description'], '/articles/' + a['slug'], REP_IMAGE['src'], REP_IMAGE['alt'], 'article', a['publishedAt'])
    return page(meta, body, preloads='' if a.get('textOnly') else preload(REP_IMAGE['src']))

# ---------- 블로그 목록 (lib/blog-view.ts + app/blog/page.tsx) ----------
BLOG_TOPICS = [{'slug': 'about', 'name': '병원 소개'}] + [{'slug': t['slug'], 'name': t['name']} for t in TREATMENTS]
ABOUT_FIRST = '치아와 잇몸, 교합은 서로 연결되어 있습니다. 청주웰치과는 구강악안면외과, 치과교정과, 치과보철과, 치주과 등 각 진료 분야의 의료진과 상담할 수 있도록 진료를 안내합니다. 검사 결과를 바탕으로 필요한 치료를 이해하고 선택할 수 있도록, 치료 목적과 과정, 이후 관리에 대해 물어보세요.'
INITIAL = []
for c in CARDS:
    t = next((x for x in TREATMENTS if '/treatments/' + x['slug'] == c['url']), None)
    INITIAL.append({'id': c['url'], 'url': c['url'], 'title': c['name'], 'description': c['description'], 'firstSection': ' '.join(t['sections'][0]['paragraphs']) if t else ABOUT_FIRST,
                    'topic': t['slug'] if t else 'about', 'category': t['name'] if t else '병원 소개', 'picture': {'image': c['image'], 'alt': c['alt'], 'width': c['width'], 'height': c['height']}})

def excerpt(e):
    summary = ' '.join(x for x in [e['description'], e['firstSection']] if x)
    return re.sub(r'\s+\S*$', '', summary[:320]) + '…' if len(summary) > 320 else summary

def blog_view(topic, page_n):
    initial = [e for e in INITIAL if not topic or e['topic'] == topic['slug']]
    later = [{'id': p['id'], 'url': '/articles/' + p['slug'], 'title': p['title'], 'description': p['description'], 'firstSection': ' '.join(p['sections'][0]['paragraphs']) if p['sections'] else '',
              'topic': p['treatmentSlug'], 'category': T_BY_SLUG[p['treatmentSlug']]['name'] if p['treatmentSlug'] in T_BY_SLUG else '치아 건강정보', 'publishedAt': p['publishedAt'], '_at': p['_at']}
             for p in reversed(ITEMS) if not topic or p['treatmentSlug'] == topic['slug']]
    total = max(1, math.ceil(len(later) / 10))
    page_n = min(total, max(1, page_n))
    is_initial = bool(initial) and page_n == 1
    items = (initial if is_initial else []) + later[(page_n - 1) * 10: page_n * 10]
    return page_n, total, items, is_initial

def blog_page(topic, page_n):
    page_n, total, items, is_initial = blog_view(topic, page_n)
    tslug = topic['slug'] if topic else None
    title = ('청주치과 ' + topic['name'] + ' 블로그' if topic else '청주치과 블로그 | 청주웰치과') + (' · ' + str(page_n) + '페이지' if page_n > 1 else '')
    body = '<main id="main" class="blog-shell"><section class="blog-content">'
    body += f'<h1 class="blog-topic-heading">청주치과 {E(topic["name"])} 이야기</h1>' if topic else '<h1 class="sr-only">청주치과 블로그</h1>'
    if not items: body += '<p class="blog-empty">공개된 글이 아직 없습니다. <a href="/#care">진료 안내</a>에서 상담 전 확인할 내용을 살펴보세요.</p>'
    else:
        body += f'<div class="blog-list" data-blog-list="{"initial" if is_initial else "latest"}">'
        for e in items:
            pic = e.get('picture')
            body += f'<article data-blog-entry="{"initial" if pic else "latest"}">'
            if pic: body += f'<a class="initial-post-image" href="{e["url"]}" data-card-name="{E(e["title"])}"><img src="{pic["image"]}" alt="{E(pic["alt"])}" width="{pic["width"]}" height="{pic["height"]}" loading="lazy"/></a>'
            time_el = f'<time dateTime="{e["publishedAt"]}">{kst_long(e["_at"])}</time>' if e.get('publishedAt') else ''
            body += f'<h2><a href="{e["url"]}">{E(e["title"])}</a></h2><div class="blog-meta">{time_el}<span>작성자: 청주웰치과 진료 안내</span></div>'
            body += f'<p class="blog-excerpt">{E(excerpt(e))}<!-- --> <a class="text-link blog-read-more" href="{e["url"]}" aria-label="{E(e["title"] + " 더 읽기")}">더 읽기</a></p>'
            body += f'<p class="blog-category">카테고리 <a href="{E(blog_path(e["topic"]))}">{E(e["category"])}</a></p></article>'
        body += '</div>'
    if total > 1:
        pages = [n for n in range(1, total + 1) if n == 1 or n == total or abs(n - page_n) <= 1]
        body += '<nav class="blog-pagination" aria-label="글 목록 페이지">'
        if page_n > 1: body += f'<a href="{E(blog_path(tslug, page_n - 1))}" rel="prev">← 이전</a>'
        for i, n in enumerate(pages):
            body += '<span>' + ('<span class="page-gap" aria-hidden="true">…</span>' if i > 0 and n - pages[i - 1] > 1 else '')
            body += f'<a href="{E(blog_path(tslug, n))}" aria-label="{n}페이지"' + (' aria-current="page"' if n == page_n else '') + f'>{n}</a></span>'
        if page_n < total: body += f'<a href="{E(blog_path(tslug, page_n + 1))}" rel="next">다음 →</a>'
        body += '</nav>'
    body += '<nav class="blog-topics" aria-label="블로그 주제"><a href="/blog"' + ('' if topic else ' aria-current="page"') + '>전체</a>'
    body += ''.join(f'<a href="{E(blog_path(t["slug"]))}"' + (' aria-current="page"' if topic and topic['slug'] == t['slug'] else '') + f'>{E(t["name"])}</a>' for t in BLOG_TOPICS)
    body += '</nav></section></main>'
    extra = ''
    if C.get('legacyQueryRedirectScript') and page_n == 1 and not topic:
        extra = "<script>(function(){var q=new URLSearchParams(location.search),p=q.get('page'),t=q.get('topic');if(!p&&!t)return;var u='/blog';if(t&&/^[a-z-]+$/.test(t))u+='/topic/'+t;if(p&&/^\\d+$/.test(p)&&p!=='1')u+='/page/'+p;location.replace(u);})()</script>"
    robots = 'noindex, follow' if (topic or page_n > 1) else None
    meta = head_meta(title, '청주웰치과의 진료별 상담 준비와 치아 건강정보를 최신 글부터 살펴보세요.', blog_path(tslug, page_n), REP_IMAGE['src'], REP_IMAGE['alt'], robots=robots)
    return page(meta, body, head_extra=extra), total

# ---------- 진료 안내 (treatments/[slug]/page.tsx) ----------
def source_label(s):
    return '청주웰치과 진료 안내' if 'cjwelldental' in s else 'FDA 환자 안내' if 'fda.gov' in s else 'NIDCR 구강건강 안내' if 'nidcr' in s else 'NHS 환자 안내' if 'nhs' in s else '공식 환자 안내'

def treatment_page(t):
    related = [a for a in ITEMS if a['treatmentSlug'] == t['slug']]
    body = '<main id="main" class="detail-main">' + breadcrumb(t['name'])
    body += f'<header class="detail-header"><p class="eyebrow">{E(t["english"])}</p><h1>{E(t["title"])}</h1><p>{E(t["intro"])}</p></header><div class="detail-layout"><article class="prose">'
    body += f'<img class="detail-cover" src="{t["image"]}" width="1000" height="1000" alt="{E(t["alt"])}"/>'
    body += ''.join(f'<section id="section-{i}"><h2>{E(s["heading"])}</h2>' + ''.join(f'<p>{E(p)}</p>' for p in s['paragraphs']) + '</section>' for i, s in enumerate(t['sections']))
    body += '<section class="faq"><p class="eyebrow">QUESTIONS &amp; ANSWERS</p><h2>자주 궁금해하시는 내용</h2>' + ''.join(f'<details><summary>{E(q["q"])}<span aria-hidden="true">+</span></summary><p>{E(q["a"])}</p></details>' for q in t['questions']) + '</section>'
    body += '<p class="source-note">안내 근거: ' + ''.join(f'<a href="{E(s)}" target="_blank" rel="noopener noreferrer">' + (' · <!-- -->' if i > 0 else '') + source_label(s) + '</a>' for i, s in enumerate(t['sources'])) + '</p></article>'
    body += '<aside class="detail-aside"><p>이 안내에서 살펴볼 내용</p>' + ''.join(f'<a href="#section-{i}"><small>0<!-- -->{i + 1}</small>{E(s["heading"])}</a>' for i, s in enumerate(t['sections'])) + '<a class="aside-back" href="/#care">전체 진료 안내 ↗</a></aside></div>'
    if related: body += '<section class="related-posts"><h2>함께 읽으면 좋은 글</h2>' + ''.join(f'<a href="/articles/{a["slug"]}">{E(a["title"])}<span>↗</span></a>' for a in related) + '</section>'
    body += CONTACT_BOX + HOME_LINK + '</main>'
    meta = head_meta(t['title'] + ' | 청주웰치과', t['description'], '/treatments/' + t['slug'], t['image'], t['alt'])
    return page(meta, body, preloads=preload(t['image']))

# ---------- 홈 (page.tsx + home-original.tsx + home-cost-guide.tsx) ----------
def home_page():
    body = '<main id="main" class="editorial-home"><section class="care-section" id="care"><div class="section-heading"><div><p class="eyebrow">CHEONGJU WELL DENTAL</p><h2>청주웰치과 주요 안내</h2></div><p class="section-summary">청주웰치과 진료 안내</p></div><div class="card-grid" data-card-list="primary">'
    for i, c in enumerate(CARDS):
        v = VARIANTS.get(c['image'])
        src = v['src'] if v else c['image']
        img = f'<img src="{src}"' + (f' srcSet="{E(v["srcSet"])}" sizes="{E(v["sizes"])}"' if v else '') + f' alt="{E(c["alt"])}" width="{c["width"]}" height="{c["height"]}" loading="{"eager" if i == 0 else "lazy"}" fetchPriority="{"high" if i == 0 else "auto"}" decoding="async"/>'
        body += f'<a class="care-card" href="{c["url"]}" data-card-name="{E(c["name"])}"><div class="card-visual">{img}<span class="card-number">0<!-- -->{i + 1}</span></div><div class="card-copy"><p class="card-label">{E(c["label"])}</p><h2>{E(c["name"])}</h2><p>{E(c["description"])}</p><span class="read-more">자세히 보기 <span aria-hidden="true">↗</span></span></div></a>'
    body += '</div><p class="additional-care">턱의 움직임이 불편하신가요? <a href="/treatments/jaw-joint">청주치과 턱관절 진료 안내 ↗</a></p></section>'
    c = HOME
    P = lambda items: ''.join(f'<p>{E(x)}</p>' for x in items)
    L = lambda items: '<ul>' + ''.join(f'<li>{E(x)}</li>' for x in items) + '</ul>'
    body += f'<article class="source-homeguide" id="treatments" data-original-revision="{E(c["revision"])}">'
    body += f'<header class="original-hero"><p class="original-kicker">{E(c["eyebrow"])}</p><h1>{E(c["title"])}</h1><p class="original-subtitle">{E(c["subtitle"])}</p>{P(c["intro"])}</header>'
    body += '<section class="original-section" id="guide-checkpoints"><p class="original-kicker">CHECKPOINT 01–04</p><h2>진료 전 살펴볼 네 가지</h2><div class="original-checks">' + ''.join(f'<div class="original-check"><span class="original-count">{i + 1:02d}</span><h3>{E(v["title"])}</h3><p>{E(v["text"])}</p></div>' for i, v in enumerate(c['checkpoints'])) + '</div></section>'
    body += '<section class="original-section" id="guide-treatments"><p class="original-kicker">TREATMENT GUIDE</p><h2>진료 항목 자세히 보기</h2><div class="original-treatments">' + ''.join(f'<div class="original-treatment"><span>{i + 1:02d}</span><div><h3>{E(v["title"])}</h3><p>{E(v["text"])}</p></div></div>' for i, v in enumerate(c['treatments'])) + '</div></section>'
    body += '<section class="original-section" id="guide-stages"><p class="original-kicker">BEFORE &amp; AFTER</p><h2>치료·시술 전후 일정 안내</h2><div class="original-stages" role="list">' + ''.join(f'<div class="original-stage" role="listitem"><div><span>{E(v["when"])}</span><h3>{E(v["stage"])}</h3></div><p>{E(v["text"])}</p></div>' for v in c['stages']) + f'</div><p class="original-note">{E(c["stageNote"])}</p></section>'
    body += f'<section class="original-section" id="guide-consultation"><p class="original-kicker">CONSULTATION</p><h2>상담을 준비하는 팁과 질문</h2><div class="original-tips">{L(c["consultTips"])}</div><div class="original-questions">' + ''.join(f'<details><summary>{E(v["q"])}</summary><p>{E(v["a"])}</p></details>' for v in c['questions']) + '</div></section>'
    body += f'<section class="original-section" id="guide-patient-info"><p class="original-kicker">YOUR INFORMATION</p><h2>환자가 미리 알려주면 좋은 정보</h2>{L(c["patientInfo"])}</section>'
    phone = c['links']['phone']; tel = re.sub(r'\D', '', phone)
    body += f'<section class="original-section" id="guide-directions"><p class="original-kicker">LOCATION</p><h2>{E(c["name"])}<!-- --> 오시는 길</h2><p class="original-address">{E(c["directions"]["address"])}</p>{P(c["directions"]["items"])}<div class="original-actions"><a href="tel:{tel}"><span>전화 문의</span><strong>{E(phone)}</strong></a><a href="{E(c["links"]["naver"])}" target="_blank" rel="noopener noreferrer"><span>네이버 플레이스</span><strong>위치·예약 정보 ↗</strong></a><a href="{E(c["links"]["homepage"])}" target="_blank" rel="noopener noreferrer"><span>공식 홈페이지</span><strong>병원 안내 바로가기 ↗</strong></a></div></section>'
    body += f'<section class="original-section" id="guide-clinic"><p class="original-kicker">CLINIC INFORMATION</p><h2>병원 안내</h2>{P(c["clinicIntro"])}<dl class="original-facts">' + ''.join(f'<div><dt>{E(v["label"])}</dt><dd>{E(v["value"])}</dd></div>' for v in c['clinicFacts']) + '</dl><details class="original-references"><summary>안내에 참고한 공식 자료</summary><ul>' + ''.join(f'<li><a href="{E(v["url"])}" target="_blank" rel="noopener noreferrer">{E(v["label"])}</a></li>' for v in c['sources']) + '</ul></details></section>'
    body += f'<aside class="original-medical"><h2>의료정보 안내</h2><p>{E(c["disclaimer"])}</p></aside></article>'
    k = COST
    body += COST_STYLE + f'<section class="cost-guide" id="cost-maintenance" aria-labelledby="cost-maintenance-title" data-cost-revision="{E(k["revision"])}"><p class="cost-kicker">{E(k["eyebrow"])}</p><h2 id="cost-maintenance-title">{E(k["title"])}</h2>{P(k["intro"])}<p class="cost-date">{E(k["dateNote"])}</p>'
    body += f'<table><caption>{E(k["caption"])}</caption><thead><tr>' + ''.join(f'<th scope="col">{E(v)}</th>' for v in k['columns']) + '</tr></thead><tbody>'
    body += ''.join(f'<tr><th scope="row">{E(r["treatment"])}</th><td data-label="{E(k["columns"][1])}"><strong class="cost-price">{E(r["price"])}</strong></td><td data-label="{E(k["columns"][2])}">{E(r["timing"])}</td><td data-label="{E(k["columns"][3])}">{E(r["annual"])}</td></tr>' for r in k['rows'])
    body += f'</tbody></table><div class="cost-table-notes"><p>{E(k["methodNote"])}</p><ul>' + ''.join(f'<li><strong>{E(r["treatment"])}</strong>: <!-- -->{E(r["priceNote"])}</li>' for r in k['rows']) + '</ul></div>'
    body += f'<div class="cost-calculation"><h3>{E(k["calculationTitle"])}</h3>{L(k["calculation"])}</div><p class="cost-safety">{E(k["note"])}</p><details><summary>가격·관리 안내의 출처와 산정 기준</summary><ol class="cost-sources">' + ''.join(f'<li><a href="{E(s["url"])}" target="_blank" rel="noopener noreferrer">{E(s["label"])}</a><span>{E(s["note"])}</span></li>' for s in k['sources']) + '</ol></details></section></main>'
    meta = head_meta(C['homeTitle'], C['description'], '/', '/images/clinic.jpg', '청주웰치과 건물 외관')
    v = VARIANTS[CARDS[0]['image']]
    return page(meta, body, home=True, preloads=preload(None, 'high', v['srcSet'], v['sizes']))

def about_page():
    body = '<main id="main" class="detail-main">' + breadcrumb('웰치과 소개') + f'<header class="detail-header"><p class="eyebrow">ABOUT WELL</p><h1>{ABOUT_TITLE}</h1><p>진료를 이해하는 상담부터 치료 후 관리까지.<br/>청주웰치과의 의료진과 공간을 만나보세요.</p></header>'
    body += '<img class="wide-photo" src="/images/lobby.jpg" width="1600" height="1067" alt="청주웰치과의 접수와 대기 공간"/>'
    body += '<section class="about-statement"><p class="eyebrow">OUR APPROACH</p><h2>분과별 의료진이<br/>구강 상태를 함께 살펴봅니다.</h2><div><p>치아와 잇몸, 교합은 서로 연결되어 있습니다. 청주웰치과는 구강악안면외과, 치과교정과, 치과보철과, 치주과 등 각 진료 분야의 의료진과 상담할 수 있도록 진료를 안내합니다.</p><p>검사 결과를 바탕으로 필요한 치료를 이해하고 선택할 수 있도록, 치료 목적과 과정, 이후 관리에 대해 물어보세요. 적용 방법과 치료 기간은 개인의 구강 상태에 따라 달라집니다.</p></div></section>'
    body += '<section class="doctors-section"><p class="eyebrow">OUR DOCTORS</p><h2>의료진 안내</h2><p class="subtle">공식 홈페이지 의료진 소개 기준이며 진료 일정은 방문 전 확인해 주세요.</p><div class="doctors-grid">' + ''.join(f'<div class="doctor-name"><p>{n}<span>{r}</span></p><small>{s}</small></div>' for n, r, s in DOCTORS) + f'</div><a class="text-link" href="{CLINIC["homepage"]}doctors/" target="_blank" rel="noopener noreferrer">공식 홈페이지에서 의료진 자세히 보기 ↗</a></section>'
    body += CONTACT_BOX + HOME_LINK + '</main>'
    meta = head_meta(ABOUT_TITLE + ' | 의료진과 진료 공간', '청주웰치과의 분과별 의료진, 진료 공간과 상담 안내를 확인하세요.', '/about', '/images/clinic.jpg', '청주웰치과가 위치한 건물 외관')
    return page(meta, body, preloads=preload('/images/lobby.jpg'))

def visit_page():
    body = '<main id="main" class="detail-main">' + breadcrumb('오시는 길') + '<header class="detail-header"><p class="eyebrow">VISIT WELL</p><h1>청주웰치과 오시는 길</h1><p>방문하실 일정과 진료 내용을 미리 확인해 주세요.</p></header><div class="visit-grid"><div class="visit-info"><h2>주소</h2>'
    body += f'<p>{CLINIC["address"]}</p><a class="button" href="{CLINIC["naverPlace"]}" target="_blank" rel="noopener noreferrer">네이버지도에서 길찾기 ↗</a><h2>전화 상담</h2><a class="phone-large" href="{CLINIC["phoneHref"]}">043.238.9201</a><h2>주차 안내</h2><p>건물 지하 주차장을 이용할 수 있습니다.<br/>접수 시 차량 등록과 주차 지원을 확인해 주세요.</p><div class="inline-links"><a href="{CLINIC["kakao"]}" target="_blank" rel="noopener noreferrer">카카오톡 상담 ↗</a><a href="{CLINIC["naverPlace"]}" target="_blank" rel="noopener noreferrer">네이버지도 ↗</a></div></div>'
    body += '<section class="visit-times"><h2>진료시간</h2>' + HOURS_HTML + f'<p class="source-note">병원에서 확인한 진료시간입니다.<br/>공휴일 방문 시간과 진료과별 접수 마감은 전화로 확인해 주세요.</p><img src="{REP_IMAGE["src"]}" width="{REP_IMAGE["width"]}" height="{REP_IMAGE["height"]}" alt="{E(REP_IMAGE["alt"])}" loading="lazy"/></section></div></main>'
    meta = head_meta('청주웰치과 오시는 길 | 진료시간·전화·주차 안내', '청주웰치과 주소와 진료시간, 전화 상담 및 주차 안내입니다. 청주시 흥덕구 2순환로 1120 승리빌딩 3~5층.', '/visit', REP_IMAGE['src'], REP_IMAGE['alt'])
    return page(meta, body)

def not_found_page():
    # layout 의 기본 메타(title·description·icons·robots)만 있고 canonical/og 는 없다. Next 는 404 에 robots noindex 를 추가한다.
    meta = f'<meta name="robots" content="noindex"/><title>{E(C["homeTitle"])}</title><meta name="description" content="{E(C["description"])}"/><meta name="application-name" content="{SITE_NAME}"/><meta name="robots" content="{"index, follow" if LIVE else "noindex, nofollow"}"/>{ICONS}{VERIFICATION_META}'
    body = '<main id="main" class="detail-main"><div class="empty-articles"><p class="eyebrow">404</p><h1>요청한 페이지를 찾을 수 없습니다.</h1><p>주소를 확인하거나 진료 안내에서 필요한 내용을 찾아보세요.</p><a class="button" href="/">홈으로 돌아가기</a></div></main>'
    return page(meta, body)

# ---------- 출력 ----------
if D.exists():
    for child in D.iterdir():
        if child.name in ('images', 'icons'): continue
        shutil.rmtree(child) if child.is_dir() else child.unlink()
for sub in ('images', 'icons'):
    if (D / sub).exists(): shutil.rmtree(D / sub)
    shutil.copytree(R / 'public' / sub, D / sub)
for f in ('favicon.svg', 'favicon.ico', '_headers', '_redirects'):
    if (R / 'public' / f).exists(): shutil.copy(R / 'public' / f, D / f)

routes = []
write('index.html', home_page()); routes.append('/')
write('about.html', about_page()); routes.append('/about')
write('visit.html', visit_page()); routes.append('/visit')
write('404.html', not_found_page())
for t in TREATMENTS:
    write('treatments/' + t['slug'] + '.html', treatment_page(t)); routes.append('/treatments/' + t['slug'])
for a in ITEMS:
    write('articles/' + a['slug'] + '.html', post_page(a)); routes.append('/articles/' + a['slug'])
for topic in [None] + BLOG_TOPICS:
    n = 1
    while True:
        html_text, total = blog_page(topic, n)
        write(blog_file(topic['slug'] if topic else None, n), html_text); routes.append(blog_path(topic['slug'] if topic else None, n))
        if n >= total: break
        n += 1
if not QUERY_URLS:
    # 일부 이전 글의 treatmentSlug(소아치과·pediatric 등)는 블로그 주제가 아니어서 라이브의 /blog?topic=… 는 전체 목록(= /blog)을 보여줬다.
    # 경로형 주소에서도 같은 내용이 나오도록 그 주소에 /blog 1페이지 사본을 둔다(파일명은 디코딩된 slug, 요청은 퍼센트 인코딩 주소).
    for odd in sorted({a['treatmentSlug'] for a in ITEMS} - set(T_BY_SLUG)):
        write('blog/topic/' + odd + '.html', blog_page(None, 1)[0])

# sitemap.xml (app/sitemap.xml/route.ts)
paths = (['/', '/about', '/visit', '/blog'] + ['/treatments/' + t['slug'] for t in TREATMENTS] + ['/articles/' + a['slug'] for a in ITEMS]) if LIVE else []
write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{absolute(p)}</loc></url>' for p in paths) + '</urlset>')
# rss.xml (app/rss.xml/route.ts)
def xml(s): return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
def sec_text(sections): return '\n\n'.join(s['heading'] + '\n' + '\n\n'.join(s['paragraphs']) for s in sections)
def rss_item(title, path, description, published=None):
    url = xml(absolute(path))
    return '<item><title>' + xml(title) + '</title><link>' + url + '</link><guid isPermaLink="true">' + url + '</guid>' + (f'<pubDate>{utc_string(published)}</pubDate>' if published else '') + '<description>' + xml(description) + '</description></item>'
items = ''
for a in ITEMS:
    srcs = [s for s in a['sourceIds'] if s.startswith('https://')]
    items += rss_item(a['title'], '/articles/' + a['slug'], '\n\n'.join(x for x in [sec_text(a['sections']), '참고 자료\n' + '\n'.join(srcs) if srcs else ''] if x), a['_at'])
for t in (TREATMENTS if LIVE else []):
    items += rss_item(t['title'], '/treatments/' + t['slug'], '\n\n'.join([t['intro'], sec_text(t['sections']), '자주 궁금해하시는 내용\n' + '\n\n'.join(q['q'] + '\n' + q['a'] for q in t['questions']), '안내 근거\n' + '\n'.join(t['sources'])]))
write('rss.xml', '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>' + xml(SITE_NAME) + '</title><link>' + xml(absolute('/')) + '</link><description>청주웰치과의 진료와 구강건강 안내</description><language>ko-kr</language>' + items + '</channel></rss>')
# robots.txt (app/robots.txt/route.ts)
write('robots.txt', 'User-agent: *\nAllow: /\nDisallow: /review\nSitemap: ' + absolute('/sitemap.xml') + '\n' if LIVE else 'User-agent: *\nDisallow: /\n')
print(json.dumps({'dist': str(D.relative_to(R)), 'routes': len(routes), 'articles': len(ITEMS), 'held_future': len(_future), 'indexing': LIVE}, ensure_ascii=False))

# ---- quickmenu (2026-10-22): dist 전체 HTML의 </body> 앞에 오른쪽 고정 퀵메뉴 삽입 ----
def _qm_apply():
    import re as _re, pathlib as _pl
    here = _pl.Path(__file__).resolve()
    for root in (here.parent, here.parent.parent):
        f = root / 'quickmenu.html'
        if f.exists():
            frag = f.read_text(encoding='utf-8'); out = root / 'dist'; break
    else:
        return
    for p in out.rglob('*.html'):
        s = p.read_text(encoding='utf-8')
        s2 = _re.sub(r'<!-- quickmenu:start -->.*?<!-- quickmenu:end -->', '', s, flags=_re.S)
        if '</body>' in s2:
            s2 = s2.replace('</body>', frag + '</body>', 1)
        if s2 != s: p.write_text(s2, encoding='utf-8')
_qm_apply()

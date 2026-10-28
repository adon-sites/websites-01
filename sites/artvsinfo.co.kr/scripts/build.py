#!/usr/bin/env python3
"""artvsinfo.co.kr (부산 아트의원 정보 사이트) 정적 생성기.

입력: site-config.json, content/posts.json(이전 시점까지 공개된 글), content/posts/*.md(이후 추가 글),
      content/site-data.json(시술·가이드·관련 글 규칙), homepage-original.json, homepage-cost-guide.json,
      templates/*.css(라이브 사이트에서 가져온 컴파일 CSS), public/(이미지·폰트·favicon).
출력: dist/ 전체 (홈, about, contact, treatments/*, blog 목록·페이지·주제, journal/*, 404, robots, sitemap, rss).
마크업은 이전 Next.js(vinext) SSR 결과와 동일하게 맞추되 클라이언트 런타임(JS 청크·RSC payload)은 넣지 않는다.
"""
import json, re, html as _html, pathlib, datetime, shutil, os, sys, math

R = pathlib.Path(__file__).resolve().parents[1]
VERIFY = os.environ.get('ART_VERIFY') == '1'   # 라이브(미색인 상태)와 바이트 비교용 출력 모드
D = R / ('dist-verify' if VERIFY else 'dist')
C = json.loads((R / 'site-config.json').read_text(encoding='utf-8'))
if VERIFY:
    C['indexingEnabled'] = False
    C['blogUrlStyle'] = 'query'
    C['legacyQueryRedirectScript'] = False
S = json.loads((R / 'content/site-data.json').read_text(encoding='utf-8'))
HOME = json.loads((R / 'homepage-original.json').read_text(encoding='utf-8'))
COST = json.loads((R / 'homepage-cost-guide.json').read_text(encoding='utf-8'))
POSTS = json.loads((R / 'content/posts.json').read_text(encoding='utf-8'))

O = C['origin'].rstrip('/')
SITE_NAME = C['siteName']            # '부산 필러'
HEADER_NAME = C['headerSiteName']    # '부산필러'
LIVE = bool(C.get('indexingEnabled'))
START = datetime.datetime.fromisoformat(C['publicationStartAt'].replace('Z', '+00:00'))
KST = datetime.timezone(datetime.timedelta(hours=9))
TREATMENTS = S['treatments']
T_BY_SLUG = {t['slug']: t for t in TREATMENTS}
T_BY_NAME = {t['name']: t for t in TREATMENTS}
FEATURED_SLUGS = S['featuredSlugs']
IMAGES = S['images']
CLINIC_IMAGE = S['clinicImage']

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
DEFAULT_CHECKLIST = C['defaultChecklist']
def _load_md(path):
    raw = path.read_text(encoding='utf-8'); assert raw.startswith('---\n'), path
    fm, body = raw[4:].split('\n---\n', 1); meta = {}
    for line in fm.splitlines():
        if ':' in line: k, v = line.split(':', 1); meta[k.strip()] = v.strip().strip('"').strip("'")
    secs = []; cur = None
    for line in body.strip().splitlines():
        if line.startswith('## '): cur = [line[3:].strip(), []]; secs.append(cur)
        elif cur is not None and line.strip(): cur[1].append(line.strip())
    checklist = DEFAULT_CHECKLIST
    if secs and secs[-1][0] == '상담 전 확인할 내용':
        items = [l[2:].strip() for l in secs[-1][1] if l.startswith('- ')]
        assert items, ('checklist section must contain "- " items', path)
        checklist = items; secs = secs[:-1]
    assert 4 <= len(secs) <= 7, ('sections', path)
    sections = [{'heading': h, 'body': '\n\n'.join(lines)} for h, lines in secs]   # 줄(빈 줄 구분) 하나가 문단 하나
    t = T_BY_NAME.get(meta.get('category', ''))
    assert t, ('category must be one of ' + '/'.join(T_BY_NAME), path)
    assert re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00', meta['date']), ('date must be YYYY-MM-DDTHH:MM:SS+09:00', path)
    dt = datetime.datetime.fromisoformat(meta['date'])
    return {'slug': path.stem, 'treatment': t['slug'], 'title': meta['title'], 'short_title': meta.get('short_title', ''),
            'description': meta['description'], 'sections': sections, 'checklist': checklist,
            'order': None, 'releaseOffsetMs': int((dt - START).total_seconds() * 1000), 'publishedAt': iso_ms(dt), 'origin': 'markdown'}

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
    _stale = D / 'journal' / (_p['slug'] + '.html')
    if _stale.exists(): _stale.unlink()
POSTS = [p for p in POSTS if p not in _future]
# publicationState().items: 색인 모드(live)에서는 releaseOffsetMs 오름차순(같으면 order).
# 미색인(preview) 모드에서는 원본 publication.ts 가 approved 배열을 파일 순서 그대로 돌려주므로 posts.json 순서를 유지한다.
ITEMS = sorted(POSTS, key=lambda p: (p['releaseOffsetMs'], p['order'] if p['order'] is not None else 10**9)) if LIVE else list(POSTS)
for p in ITEMS:
    p['_at'] = parse_iso(p['publishedAt']) if LIVE else None   # 미색인 모드에서는 날짜를 노출하지 않는다 (publishedAt=null)
INDEX = {p['slug']: i for i, p in enumerate(ITEMS)}

# ---------- 관련 글 (content-navigation.ts relatedReading) ----------
READING = S['readingPaths']
def curated_reading(topic, published):
    path = READING.get(topic)
    if not path: return []
    by_slug = {a['slug']: a for a in published if a['treatment'] == topic}
    return [{**sel, 'article': by_slug[sel['slug']]} for sel in path['selections'] if sel['slug'] in by_slug]

def related_reading(article, published):
    same = [a for a in published if a['treatment'] == article['treatment'] and a['slug'] != article['slug']]
    if article['treatment'] == 'busan-forehead-filler' or article['slug'] in FEATURED_SLUGS:
        return [a for a in same if isinstance(a['order'], int) and a['order'] <= 781][-3:]
    text = (article['title'] + ' ' + article['description']).lower()
    scored = [(x, i, sum(1 for term in x['terms'] if term.lower() in text)) for i, x in enumerate(curated_reading(article['treatment'], published)) if x['article']['slug'] != article['slug']]
    scored.sort(key=lambda z: (-z[2], z[1]))
    selected = [z[0]['article'] for z in scored[:3]]
    seen = {a['slug'] for a in selected}
    return (selected + [a for a in reversed(same) if a['slug'] not in seen])[:3]

# ---------- 공통 레이아웃 ----------
INDEX_CSS = (R / 'templates/index.css').read_text(encoding='utf-8')
HOME_CSS = (R / 'templates/home.css').read_text(encoding='utf-8')
STYLE = '<style data-vinext-inline-css data-precedence="vite-rsc/importer-resources" data-href="/_next/static/css/index.BDEU9_pe.css">' + INDEX_CSS + '</style>'
HOME_STYLE = '<style data-vinext-inline-css data-precedence="vite-rsc/importer-resources" data-href="/_next/static/css/page.D-rMGjr2.css">' + HOME_CSS + '</style>'
FONT_PRELOAD = '<link rel="preload" href="/fonts/art-site-sans-common-v2.woff2" as="font" type="font/woff2" crossOrigin="anonymous"/>'.replace('crossOrigin', 'crossorigin')
LD_SITE = jsonld({'@context': 'https://schema.org', '@type': 'WebSite', '@id': absolute('/#website'), 'name': SITE_NAME, 'alternateName': HEADER_NAME, 'url': absolute('/'), 'inLanguage': 'ko-KR', 'publisher': {'@id': absolute('/#clinic')}})
LD_CLINIC = jsonld({'@context': 'https://schema.org', '@type': 'MedicalClinic', '@id': absolute('/#clinic'), 'name': '아트의원', 'url': absolute('/'), 'telephone': '+82-51-717-3717', 'address': {'@type': 'PostalAddress', 'streetAddress': '가야대로 784 A플러스메디컬빌딩 2층', 'addressLocality': '부산진구', 'addressRegion': '부산광역시', 'addressCountry': 'KR'}, 'sameAs': ['http://www.artvs.co.kr/'], 'image': absolute('/images/interior.jpg')})
MENU = ''.join(f'<a href="{h}">{t}</a>' for h, t in [('/', SITE_NAME), ('/blog', '블로그'), ('/#treatments', '시술 안내'), ('/about', '병원 소개'), ('/contact', '오시는 길')])
HEADER = f'<header class="site-header"><div class="header-inner"><a href="/" class="brand">{HEADER_NAME}</a><nav class="desktop-menu" aria-label="주 메뉴">{MENU}</nav><details class="mobile-menu"><summary>메뉴</summary><nav aria-label="모바일 메뉴">{MENU}</nav></details></div></header>'
HOME_HEADER = f'<header class="site-header"><div class="header-inner"><a href="/" class="brand">{HEADER_NAME}</a><nav class="homepage-keyword" aria-label="공식 병원 안내"><a href="http://www.artvs.co.kr/" target="_blank" rel="noopener noreferrer">{HEADER_NAME}</a></nav></div></header>'
QUICK = '<nav class="quick-links" aria-label="빠른 안내"><a href="tel:0517173717">전화 상담</a><a href="/contact">오시는 길</a><a href="#site-content">TOP ↑</a></nav>'
YEAR = datetime.datetime.now(datetime.timezone.utc).year
FOOTER = f'<footer class="site-footer"><strong>부산 아트의원</strong><p>부산 부산진구 가야대로 784 A플러스메디컬빌딩 2층 · 대표자 조재섭<br/><a href="tel:0517173717">051-717-3717</a> · <a href="http://www.artvs.co.kr/" target="_blank" rel="noreferrer">기존 홈페이지</a></p><p>시술의 적용 여부와 경과는 개인에 따라 다릅니다. 본 안내는 진료를 대신하지 않습니다.</p><p>© <!-- -->{YEAR}<!-- --> ART CLINIC</p></footer>'
ROBOTS_META = '' if LIVE else '<meta name="robots" content="noindex, nofollow">'
VERIFICATION_META = f'<meta name="naver-site-verification" content="{E(C["naverSiteVerification"])}">' if LIVE and C.get('naverSiteVerification') else ''

def head_meta(doc_title, og_title, description, path, picture, og_type='website', published=None, canonical=True, og_description=None):
    url = absolute(path) if path != '/' else O
    img = absolute(picture['src'])
    if og_description is None: og_description = description
    parts = [f'<title>{E(doc_title)}</title>', f'<meta name="description" content="{E(description)}">', ROBOTS_META, VERIFICATION_META,
             f'<meta property="og:title" content="{E(og_title)}">', f'<meta property="og:description" content="{E(og_description)}">',
             f'<meta property="og:url" content="{E(url)}">', f'<meta property="og:site_name" content="{E(SITE_NAME)}">',
             f'<meta property="og:type" content="{og_type}">', '<meta property="og:locale" content="ko_KR">',
             f'<meta property="og:image" content="{E(img)}">', f'<meta property="og:image:width" content="{picture["width"]}">',
             f'<meta property="og:image:height" content="{picture["height"]}">', f'<meta property="og:image:alt" content="{E(picture["alt"])}">']
    if og_type == 'article' and published: parts.append(f'<meta property="article:published_time" content="{published}">')
    parts += ['<meta name="twitter:card" content="summary_large_image">', f'<meta name="twitter:title" content="{E(og_title)}">',
              f'<meta name="twitter:description" content="{E(og_description)}">', f'<meta name="twitter:image" content="{E(img)}">',
              f'<link rel="shortcut icon" href="{absolute("/favicon.png")}">', f'<link rel="icon" href="{absolute("/favicon.png")}" type="image/png" sizes="96x96">']
    if canonical: parts.append(f'<link rel="canonical" href="{E(url)}">')
    return ''.join(parts)

def page(head_extra, meta, body, home=False, preloads=()):
    pre = ''.join(f'<link rel="preload" href="{p}" as="image"' + (f' fetchPriority="{fp}"' if fp else '') + '/>' for p, fp in preloads)
    head = '<!DOCTYPE html><html lang="ko"><head><meta charSet="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>' + pre
    if home: head += STYLE + HOME_STYLE + LD_SITE + LD_CLINIC + head_extra + meta
    else: head += STYLE + FONT_PRELOAD + LD_SITE + LD_CLINIC + head_extra + meta
    head += '</head>'
    hdr = HOME_HEADER if home else HEADER
    body_tag = '<body class="art-fast-home">' if home else '<body>'
    return head + body_tag + '<a class="skip-link" href="#site-content">본문 바로가기</a>' + hdr + QUICK + '<div id="site-content">' + body + '</div>' + FOOTER + '</body></html>'

def write(path, content):
    p = D / path; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(content, encoding='utf-8')

# ---------- URL ----------
QUERY_URLS = C.get('blogUrlStyle') == 'query'
def blog_path(n=1, topic=None):
    if QUERY_URLS:
        q = []
        if n > 1: q.append('page=' + str(n))
        if topic: q.append('topic=' + topic)
        return '/blog' + ('?' + '&'.join(q) if q else '')
    p = '/blog'
    if topic: p += '/topic/' + topic
    if n > 1: p += '/page/' + str(n)
    return p

def blog_file(n=1, topic=None):
    return blog_path(n, topic).lstrip('/') + '.html'

# ---------- 글 본문 (article-body.tsx) ----------
def article_blocks(a):
    g = S['guides'][a['treatment']]
    picture = featured_picture(a['slug'])
    guide_label = None
    if not picture and a['treatment'] != 'busan-forehead-filler':
        guide_label = S['guideOverviews'].get(a['treatment'], {}).get('linkLabel')
    b = []
    if picture: b.append(('image', picture))
    b.append(('lead', a['description']))
    if a.get('exampleNote'): b.append(('paragraph', a['exampleNote']))
    for i, s in enumerate(a['sections']):
        b.append(('heading', s['heading'], 'section-' + str(i))); b.append(('paragraph', s['body']))
    b.append(('heading', '상담 전 확인할 내용', 'article-check')); b.append(('list', a['checklist']))
    b.append(('heading', '위험과 주의사항', 'article-risks')); b.append(('paragraph', g['risks']))
    b.append(('paragraph', '본 글은 상담 준비를 위한 일반 정보입니다. 국내 사용 제품과 허가사항, 개인별 적용 여부와 회복은 의료진의 진료를 통해 확인하세요.'))
    if a.get('citations'):
        b.append(('heading', '참고 자료', 'article-sources'))
        for c in a['citations']: b.append(('link', c['title'], c['url']))
        b.append(('paragraph', '해외 기관의 일반 안내를 참고했습니다. 국내 제품의 허가사항이나 본원의 시술 제공 여부를 확인하는 자료는 아닙니다.'))
    b.append(('link', guide_label or '시술별 적용 여부와 주의사항 더 보기', '/treatments/' + a['treatment']))
    return b

def paragraphs(text):   # 마크다운 글의 빈 줄 구분 문단은 <p> 여러 개로
    return ''.join(f'<p>{E(x)}</p>' for x in text.split('\n\n'))

def article_body(a):
    out = []
    for b in article_blocks(a):
        k = b[0]
        if k == 'image': p = b[1]; out.append(f'<figure class="initial-post-image"><img src="{p["image"]}" alt="{E(p["alt"])}" width="{p["width"]}" height="{p["height"]}"/></figure>')
        elif k == 'lead': out.append(f'<p class="lead">{E(b[1])}</p>')
        elif k == 'paragraph': out.append(paragraphs(b[1]))
        elif k == 'heading': out.append(f'<h2 id="{b[2]}">{E(b[1])}</h2>')
        elif k == 'list': out.append('<ul>' + ''.join(f'<li>{E(x)}</li>' for x in b[1]) + '</ul>')
        elif k == 'link': out.append(f'<a class="text-link" href="{E(b[2])}">{E(b[1])}<!-- --> ↗</a>')
    return ''.join(out)

def xml_escape(s): return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')
def article_feed_html(a):
    out = []
    for b in article_blocks(a):
        k = b[0]
        if k == 'image': p = b[1]; out.append(f'<figure><img src="{xml_escape(absolute(p["image"]))}" alt="{xml_escape(p["alt"])}" width="{p["width"]}" height="{p["height"]}"/></figure>')
        elif k in ('lead', 'paragraph'): out.append(''.join(f'<p>{xml_escape(x)}</p>' for x in b[1].split('\n\n')))
        elif k == 'heading': out.append(f'<h2>{xml_escape(b[1])}</h2>')
        elif k == 'list': out.append('<ul>' + ''.join(f'<li>{xml_escape(x)}</li>' for x in b[1]) + '</ul>')
        elif k == 'link': href = b[2] if b[2].startswith('https://') else absolute(b[2]); out.append(f'<p><a href="{xml_escape(href)}">{xml_escape(b[1])}</a></p>')
    return ''.join(out)

# ---------- 대표 글 6편 (featured.ts) ----------
FEATURED = []
for slug in FEATURED_SLUGS:
    a = next(x for x in POSTS if x['slug'] == slug); pic = IMAGES[a['treatment']]
    FEATURED.append({'slug': slug, 'name': a['title'], 'description': a['description'], 'url': '/journal/' + slug, 'image': pic['src'], 'alt': pic['alt'], 'width': pic['width'], 'height': pic['height'], 'position': 'center'})
def featured_picture(slug): return next((f for f in FEATURED if f['slug'] == slug), None)

# ---------- 글 페이지 ----------
def post_page(a):
    t = T_BY_SLUG[a['treatment']]; pic = IMAGES[a['treatment']]
    related = related_reading(a, ITEMS); i = INDEX[a['slug']]
    prev = ITEMS[i - 1] if i > 0 else None; nxt = ITEMS[i + 1] if i + 1 < len(ITEMS) else None
    ld = {'@context': 'https://schema.org', '@type': 'Article', 'headline': a['title'], 'description': a['description'], 'image': [absolute(pic['src'])], 'mainEntityOfPage': absolute('/journal/' + a['slug']), 'author': {'@type': 'Organization', 'name': '아트의원 시술 안내'}, 'publisher': {'@id': absolute('/#clinic')}}
    if a['_at']: ld['datePublished'] = a['publishedAt']
    ld['inLanguage'] = 'ko-KR'
    time_el = f'<time datetime="{a["publishedAt"]}">{kst_long(a["_at"])}</time>' if a['_at'] else ''
    body = f'<main class="article journal-article">{jsonld(ld)}<header class="entry-header"><h1>{E(a["title"])}</h1><div class="blog-meta">{time_el}<span>작성자: 아트의원 시술 안내</span></div></header>'
    body += article_body(a)
    body += f'<p class="blog-category">카테고리 <a href="{E(blog_path(1, t["slug"]))}">{E(t["name"])}</a></p>'
    body += '<nav class="post-navigation" aria-label="이전 글과 다음 글">'
    if prev: body += f'<a href="/journal/{prev["slug"]}" rel="prev">← <!-- -->{E(prev["title"])}</a>'
    if nxt: body += f'<a href="/journal/{nxt["slug"]}" rel="next">{E(nxt["title"])}<!-- --> →</a>'
    body += '</nav>'
    if related: body += '<h2>같은 주제의 글</h2><ul>' + ''.join(f'<li><a href="/journal/{r["slug"]}">{E(r["title"])}</a></li>' for r in related) + '</ul>'
    body += '<div class="related"><a href="/blog">전체 글 보기</a><a href="/contact">아트의원 진료·위치 안내</a></div>'
    body += f'<p data-carousel-home-link="true" style="margin-top:32px;padding-top:20px;border-top:1px solid #dce4e8"><a href="{C["backlinkOrigin"]}" style="text-decoration:underline;text-underline-offset:3px;font-weight:600">{E(t["keyword"])}</a></p></main>'
    doc_title = a['short_title'] if a.get('short_title') else a['title'] + ' | ' + SITE_NAME
    meta = head_meta(doc_title, a['title'], a['description'], '/journal/' + a['slug'], pic, 'article', a['publishedAt'] if a['_at'] else None)
    pre = [(pic['src'], None)] if featured_picture(a['slug']) else []
    return page('', meta, body, preloads=pre)

# ---------- 블로그 목록 (journal-view.ts + blog/page.tsx) ----------
def journal_view(page_n, topic):
    filtered = [a for a in reversed(ITEMS) if not topic or a['treatment'] == topic['slug']]
    initial = sorted([a for a in filtered if a['slug'] in FEATURED_SLUGS], key=lambda a: FEATURED_SLUGS.index(a['slug']))
    later = [a for a in filtered if a['slug'] not in FEATURED_SLUGS]
    later_pages = math.ceil(len(later) / 10); total = max(1, later_pages + (1 if initial else 0))
    page_n = min(total, max(1, page_n))
    items = initial if initial and page_n == total else later[(page_n - 1) * 10: page_n * 10]
    return page_n, total, items

def blog_page(page_n, topic):
    page_n, total, items = journal_view(page_n, topic)
    tslug = topic['slug'] if topic else None
    title = (topic['keyword'] + ' 블로그' if topic else '부산 아트의원 블로그') + (' · ' + str(page_n) + '페이지' if page_n > 1 else '')
    description = '부산 아트의원의 시술별 상담 준비와 주의사항을 최신 글부터 살펴보세요.'
    pic = IMAGES[topic['slug']] if topic else CLINIC_IMAGE
    body = '<main class="blog-shell"><section class="blog-content">'
    body += f'<h1 class="blog-topic-heading">{E(topic["keyword"])} 이야기</h1>' if topic else '<h1 class="sr-only">아트의원 블로그</h1>'
    if not items: body += '<p>공개된 글이 아직 없습니다. 시술 안내에서 상담 전 확인할 내용을 살펴보세요.</p>'
    else:
        body += '<div class="blog-list">'
        for a in items:
            p = featured_picture(a['slug']); t = T_BY_SLUG[a['treatment']]
            summary = ' '.join(x for x in [a['description'], a['sections'][0]['body'] if a['sections'] else ''] if x)
            excerpt = re.sub(r'\s+\S*$', '', summary[:320]) + '…' if len(summary) > 320 else summary
            body += '<article>'
            if p: body += f'<a class="initial-post-image" href="{p["url"]}"><img src="{p["image"]}" alt="{E(p["alt"])}" width="{p["width"]}" height="{p["height"]}" loading="lazy"/></a>'
            time_el = f'<time datetime="{a["publishedAt"]}">{kst_long(a["_at"])}</time>' if a['_at'] else ''
            body += f'<h2><a href="/journal/{a["slug"]}">{E(a["title"])}</a></h2><div class="blog-meta">{time_el}<span>작성자: 아트의원 시술 안내</span></div>'
            body += f'<p class="blog-excerpt">{E(excerpt)}<!-- --> <a class="text-link blog-read-more" href="/journal/{a["slug"]}" aria-label="{E(a["title"] + " 더 읽기")}">더 읽기</a></p>'
            body += f'<p class="blog-category">카테고리 <a href="{E(blog_path(1, t["slug"]))}">{E(t["name"])}</a></p></article>'
        body += '</div>'
    if total > 1:
        pages = [n for n in range(1, total + 1) if n == 1 or n == total or abs(n - page_n) <= 1]
        body += '<nav class="blog-pagination" aria-label="글 목록 페이지">'
        if page_n > 1: body += f'<a href="{E(blog_path(page_n - 1, tslug))}" rel="prev">← 이전</a>'
        for i, n in enumerate(pages):
            body += '<span>' + ('<span class="page-gap" aria-hidden="true">…</span>' if i > 0 and n - pages[i - 1] > 1 else '')
            body += f'<a href="{E(blog_path(n, tslug))}" aria-label="{n}페이지"' + (' aria-current="page"' if n == page_n else '') + f'>{n}</a></span>'
        if page_n < total: body += f'<a href="{E(blog_path(page_n + 1, tslug))}" rel="next">다음 →</a>'
        body += '</nav>'
    body += '<nav class="related blog-topics" aria-label="블로그 주제"><a href="/blog"' + ('' if topic else ' aria-current="page"') + '>전체</a>'
    body += ''.join(f'<a href="{E(blog_path(1, t["slug"]))}"' + (' aria-current="page"' if topic and topic['slug'] == t['slug'] else '') + f'>{E(t["name"])}</a>' for t in TREATMENTS)
    body += '</nav></section></main>'
    extra = ''
    if C.get('legacyQueryRedirectScript') and page_n == 1 and not topic:
        extra = "<script>(function(){var q=new URLSearchParams(location.search),p=q.get('page'),t=q.get('topic');if(!p&&!t)return;var u='/blog';if(t&&/^[a-z-]+$/.test(t))u+='/topic/'+t;if(p&&/^\\d+$/.test(p)&&p!=='1')u+='/page/'+p;location.replace(u);})()</script>"
    meta = head_meta(title + ' | ' + SITE_NAME, title, description, blog_path(page_n, tslug), pic)
    return page(extra, meta, body), total

# ---------- 시술 안내 (treatments/[slug]/page.tsx) ----------
def treatment_page(t):
    slug = t['slug']; g = S['guides'][slug]; details = S['treatmentDetails'].get(slug); overview = S['guideOverviews'].get(slug)
    sections = details['sections'] if details else g['sections']; pic = IMAGES[slug]
    related = [a for a in ITEMS if a['treatment'] == slug]; path = READING.get(slug); core = curated_reading(slug, related)
    core_reading = ''
    if path and core:
        core_reading = f'<section id="core-reading" aria-labelledby="core-reading-heading"><h2 id="core-reading-heading">{E(t["keyword"])}<!-- -->, 질문별로 먼저 읽을 글</h2><p>{E(path["intro"])}</p><ol>'
        core_reading += ''.join(f'<li><a class="text-link" href="/journal/{x["article"]["slug"]}">{E(x["article"]["title"])}</a><p class="muted">{E(x["note"])}</p></li>' for x in core)
        core_reading += f'</ol><p><a class="text-link" href="{E(blog_path(1, slug))}">{E(t["keyword"])}<!-- --> 공개 글을 발행순으로 보기</a></p></section>'
    all_reading = '<ul>' + ''.join(f'<li><a class="text-link" href="/journal/{a["slug"]}">{E(a["title"])}</a></li>' for a in related) + '</ul>'
    body = '<main class="article">' + jsonld({'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [{'@type': 'ListItem', 'position': 1, 'name': SITE_NAME, 'item': absolute('/')}, {'@type': 'ListItem', 'position': 2, 'name': t['keyword'], 'item': absolute('/treatments/' + slug)}]})
    body += f'<a class="muted" href="/#treatments">시술 안내 / <!-- -->{E(t["name"])}</a><h1>{E(t["keyword"])}<!-- --> 상담 전 확인사항</h1><p class="lead">{E(g["intro"])}</p>'
    body += f'<figure class="article-photo"><img src="{pic["src"]}" alt="{E(pic["alt"])}" width="{pic["width"]}" height="{pic["height"]}" loading="lazy"/><figcaption>{E(pic["caption"])}</figcaption></figure>'
    body += '<div class="toc"><strong>이 페이지에서 살펴볼 내용</strong><ol>'
    if not overview and core: body += '<li><a href="#core-reading">질문별로 먼저 읽을 글</a></li>'
    body += ''.join(f'<li><a href="#section-{i}">{E(h)}</a></li>' for i, (h, _) in enumerate(sections))
    if overview: body += '<li><a href="#guide-questions">자주 묻는 질문</a></li>'
    if overview and core: body += '<li><a href="#core-reading">질문별로 먼저 읽을 글</a></li>'
    body += '<li><a href="#risks">위험과 주의사항</a></li>'
    if overview: body += '<li><a href="#clinic-visit">아트의원 상담·방문 안내</a></li>'
    body += '</ol></div>'
    if not overview: body += core_reading
    body += ''.join(f'<div id="section-{i}"><h2>{E(h)}</h2><p>{E(p)}</p></div>' for i, (h, p) in enumerate(sections))
    if overview:
        body += '<section id="guide-questions" aria-labelledby="guide-questions-heading"><h2 id="guide-questions-heading">자주 묻는 질문</h2>'
        body += ''.join(f'<div><h3>{E(q)}</h3><p>{E(a)}</p></div>' for q, a in overview['questions']) + '</section>'
        body += core_reading
    body += f'<h2 id="risks">위험과 주의사항</h2><p>{E(g["risks"])}</p><p class="muted">국내 사용 제품과 허가사항, 개인별 적용 여부는 진료 시 확인하세요. 해외 자료는 일반적인 안전정보 참고용입니다.</p>'
    body += f'<h2>상담 전 메모해 주세요</h2><ul><li>{E(t["focus"])}</li><li>기존 시술의 제품명과 날짜, 복용 중인 약</li><li>원하는 변화, 중요한 일정, 감수할 수 있는 회복 범위</li></ul>'
    if related:
        body += '<h2>함께 읽는 피부 이야기</h2>'
        body += (f'<details><summary>{E(t["keyword"])}<!-- --> 공개 글 전체 목록 (<!-- -->{len(related)}<!-- -->편)</summary>{all_reading}</details>' if path else all_reading)
    body += '<h2' + (' id="clinic-visit"' if overview else '') + '>부산 아트의원 상담 안내</h2><p>부산 부산진구 가야대로 784 A플러스메디컬빌딩 2층. 현재 취급 제품과 상담 가능 여부는 방문 전에 확인해 주세요.</p>'
    if overview: body += f'<p>{E(overview["visitNote"])}</p><p><a class="text-link" href="/contact">아트의원 진료시간·서면 위치·방문 연락처 확인</a></p>'
    body += '<a class="button" href="tel:0517173717">051-717-3717 전화 상담</a><div class="related">' + ''.join(f'<a href="/treatments/{x["slug"]}">{E(x["keyword"])}</a>' for x in TREATMENTS if x['slug'] != slug) + '</div>'
    body += f'<div class="notice"><p>일반적인 상담 준비 정보이며 개인별 진단이나 시술 권고를 대신하지 않습니다. 효과와 회복, 부작용에는 개인차가 있습니다.</p><p>참고: <a class="text-link" href="{E(g["source"])}" target="_blank" rel="noreferrer">{E(g["sourceName"])}</a></p></div>'
    if details:
        body += '<section aria-labelledby="guide-source-heading"><h2 id="guide-source-heading">상담 안내의 참고 자료</h2><ul>' + ''.join(f'<li><a class="text-link" href="{E(s["url"])}" target="_blank" rel="noreferrer">{E(s["title"])}</a><p class="muted">{E(s["scope"])}</p></li>' for s in details['sources']) + '</ul></section>'
    body += f'<p data-carousel-home-link="true" style="margin-top:32px;padding-top:20px;border-top:1px solid #dce4e8"><a href="{C["backlinkOrigin"]}" style="text-decoration:underline;text-underline-offset:3px;font-weight:600">{E(t["keyword"])}</a></p></main>'
    meta = head_meta(t['keyword'] + ' 상담 전 확인사항 | ' + SITE_NAME, t['keyword'] + ' 상담 전 확인사항', t['summary'] + ' · 부산 아트의원. 제품과 적용 가능 여부, 경과 관리 및 주의사항을 확인하세요.', '/treatments/' + slug, pic, og_description=t['summary'])
    return page('', meta, body)

# ---------- 홈 (page.tsx + home-original.tsx + home-cost-guide.tsx, worker/native-homepage.ts 적용 결과) ----------
def home_page():
    visible = [f for f in FEATURED if f['slug'] in INDEX]
    ld_list = jsonld({'@context': 'https://schema.org', '@type': 'ItemList', 'name': '부산 아트의원 주요 시술 안내', 'numberOfItems': len(visible), 'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'name': f['name'], 'image': absolute(f['image']), 'url': absolute(f['url'])} for i, f in enumerate(visible)]})
    body = '<main class="home-shell editorial-home" id="top"><section class="featured-section" aria-label="아트의원 주요 시술 안내"><ul class="featured-list">'
    for i, f in enumerate(visible):
        a = ITEMS[INDEX[f['slug']]]
        time_el = f'<time datetime="{a["publishedAt"]}">{kst_short(a["_at"])}</time>' if a['_at'] else ''
        body += f'<li><article class="featured-card"><a class="featured-thumb" href="{f["url"]}"><img src="{f["image"]}" alt="{E(f["alt"])}" width="{f["width"]}" height="{f["height"]}" loading="{"eager" if i < 3 else "lazy"}" fetchPriority="{"high" if i == 0 else "auto"}" decoding="async" style="object-position:{f["position"]}"/></a>'
        body += f'<div class="featured-copy"><h2><a href="{f["url"]}">{E(f["name"])}</a></h2><p class="card-meta">{time_el} · 아트의원</p><p class="card-excerpt">{E(f["description"])}</p><a class="card-more" href="{f["url"]}" aria-label="{E(f["name"] + " 더 읽기")}">더 읽기</a></div></article></li>'
    body += '</ul></section>'
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
    body += f'<section class="cost-guide" id="cost-maintenance" aria-labelledby="cost-maintenance-title" data-cost-revision="{E(k["revision"])}"><p class="cost-kicker">{E(k["eyebrow"])}</p><h2 id="cost-maintenance-title">{E(k["title"])}</h2>{P(k["intro"])}<p class="cost-date">{E(k["dateNote"])}</p>'
    body += f'<table><caption>{E(k["caption"])}</caption><thead><tr>' + ''.join(f'<th scope="col">{E(v)}</th>' for v in k['columns']) + '</tr></thead><tbody>'
    body += ''.join(f'<tr><th scope="row">{E(r["treatment"])}</th><td data-label="{E(k["columns"][1])}"><strong class="cost-price">{E(r["price"])}</strong></td><td data-label="{E(k["columns"][2])}">{E(r["timing"])}</td><td data-label="{E(k["columns"][3])}">{E(r["annual"])}</td></tr>' for r in k['rows'])
    body += f'</tbody></table><div class="cost-table-notes"><p>{E(k["methodNote"])}</p><ul>' + ''.join(f'<li><strong>{E(r["treatment"])}</strong>: <!-- -->{E(r["priceNote"])}</li>' for r in k['rows']) + '</ul></div>'
    body += f'<div class="cost-calculation"><h3>{E(k["calculationTitle"])}</h3>{L(k["calculation"])}</div><p class="cost-safety">{E(k["note"])}</p><details><summary>가격·관리 안내의 출처와 산정 기준</summary><ol class="cost-sources">' + ''.join(f'<li><a href="{E(s["url"])}" target="_blank" rel="noopener noreferrer">{E(s["label"])}</a><span>{E(s["note"])}</span></li>' for s in k['sources']) + '</ol></details></section></main>'
    description = '부산필러 부산 아트의원 시술 안내 및 부산 보톡스, 필러, 입술필러, 이마필러, 실리프팅, 쥬베룩 상담 전 확인할 정보를 살펴보세요.'
    meta = head_meta(SITE_NAME, SITE_NAME, description, '/', CLINIC_IMAGE)
    return page(ld_list, meta, body, home=True, preloads=[('/images/botox.jpg', 'auto'), ('/images/lip-filler.jpg', 'auto')])

def about_page():
    ci, ri, ti = S['clinicImage'], S['receptionImage'], S['treatmentRoomImage']
    body = f'<main class="article"><p class="eyebrow">ABOUT ART</p><h1>부산 아트의원 소개</h1><p class="lead">부산 부산진구 가야대로 784, A플러스메디컬빌딩 2층에 위치한 아트의원입니다.</p>'
    body += f'<img src="{ci["src"]}" alt="아트의원 대기 공간" width="{ci["width"]}" height="{ci["height"]}" class="full-image" decoding="async"/>'
    body += f'<img src="{ri["src"]}" alt="{E(ri["alt"])}" width="{ri["width"]}" height="{ri["height"]}" class="full-image" loading="lazy" decoding="async"/>'
    body += f'<img src="{ti["src"]}" alt="{E(ti["alt"])}" width="{ti["width"]}" height="{ti["height"]}" class="full-image" loading="lazy" decoding="async"/>'
    body += '<h2>상담 전 필요한 정보를 살펴보세요</h2><p>이 사이트는 보톡스, 필러, 실리프팅, 쥬베룩 등 시술 상담을 준비할 때 참고할 내용을 정리합니다. 현재 피부 상태와 기존 시술 이력에 따라 적용 여부와 계획은 달라질 수 있습니다.</p><p>의료진 정보와 병원의 상세 프로그램은 기존 홈페이지에서 확인하실 수 있습니다. 사진은 병원에서 제공한 자료이며 현재 공간 배치와 다를 수 있습니다.</p><a class="text-link" href="http://www.artvs.co.kr/" target="_blank" rel="noreferrer">아트의원 기존 홈페이지 ↗</a><div class="related"><a href="/contact">진료시간과 오시는 길</a><a href="/#treatments">시술별 안내</a></div></main>'
    d = '부산 서면 아트의원의 위치와 병원 공간을 확인하세요.'
    return page('', head_meta('병원 소개와 공간 안내 | ' + SITE_NAME, '부산 아트의원 소개와 공간 안내', d, '/about', ri), body, preloads=[(ci['src'], None)])

def contact_page():
    di = S['directionsImage']
    body = '<main class="article"><p class="eyebrow">VISIT ART</p><h1>진료시간과 오시는 길</h1><h2>부산 아트의원</h2><p>부산 부산진구 가야대로 784<br/>A플러스메디컬빌딩 2층</p><p>부산 서면 롯데백화점 정문 옆에 위치합니다. 주차 방법과 진료 가능 여부는 방문 전에 전화로 확인해 주세요.</p><a class="button" href="tel:0517173717">051-717-3717 전화 상담</a><h2>진료시간 안내</h2><dl class="hours"><dt>월요일 · 수요일</dt><dd>10:00–19:00</dd><dt>화요일 · 금요일</dt><dd>10:00–21:00</dd><dt>토요일</dt><dd>10:00–14:00 · 점심시간 없음</dd><dt>목요일 · 일요일 · 공휴일</dt><dd>휴진</dd></dl><p class="muted">기존 공식 홈페이지 안내 기준입니다. 임시 휴진 등 일정 변경은 병원에 확인해 주세요.</p><a class="text-link" href="https://map.naver.com/p/search/부산%20아트의원" target="_blank" rel="noreferrer">네이버 지도에서 위치 확인 ↗</a>'
    body += f'<img src="{di["src"]}" alt="{E(di["alt"])}" width="{di["width"]}" height="{di["height"]}" class="full-image" loading="lazy" decoding="async"/><p class="muted">지도는 기존 홈페이지 자료입니다. 현재 길찾기는 위 네이버 지도 링크를 이용해 주세요.</p></main>'
    d = '부산 부산진구 가야대로 784 A플러스메디컬빌딩 2층. 아트의원 전화 상담과 위치 안내.'
    return page('', head_meta('진료시간과 오시는 길 | ' + SITE_NAME, '부산 아트의원 진료시간과 오시는 길', d, '/contact', di), body)

def not_found_page():
    # 404 는 Next 의 기본 메타 렌더(자기닫힘 태그, robots noindex, rss alternate)를 head 에 그대로 둔다
    d = '부산필러 부산 아트의원 시술 안내 및 부산 보톡스, 필러, 입술필러, 이마필러, 실리프팅, 쥬베룩 상담 전 확인할 정보를 살펴보세요.'
    img = absolute(CLINIC_IMAGE['src'])
    meta = f'<meta name="robots" content="noindex"/><title>{SITE_NAME}</title><meta name="description" content="{E(d)}"/>' + ('' if LIVE else '<meta name="robots" content="noindex, nofollow"/>') + (f'<meta name="naver-site-verification" content="{E(C["naverSiteVerification"])}"/>' if LIVE and C.get('naverSiteVerification') else '')
    meta += f'<meta property="og:title" content="{SITE_NAME}"/><meta property="og:description" content="{E(d)}"/><meta property="og:url" content="{O}"/><meta property="og:site_name" content="{SITE_NAME}"/><meta property="og:type" content="website"/><meta property="og:locale" content="ko_KR"/><meta property="og:image" content="{img}"/><meta property="og:image:width" content="{CLINIC_IMAGE["width"]}"/><meta property="og:image:height" content="{CLINIC_IMAGE["height"]}"/><meta property="og:image:alt" content="{E(CLINIC_IMAGE["alt"])}"/><meta name="twitter:card" content="summary_large_image"/><meta name="twitter:title" content="{SITE_NAME}"/><meta name="twitter:description" content="{E(d)}"/><meta name="twitter:image" content="{img}"/><link rel="shortcut icon" href="{absolute("/favicon.png")}"/><link rel="icon" href="{absolute("/favicon.png")}" type="image/png" sizes="96x96"/><link rel="alternate" type="application/rss+xml" href="{absolute("/rss.xml")}"/>'
    head = '<!DOCTYPE html><html lang="ko"><head><meta charSet="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>' + STYLE + FONT_PRELOAD + meta + LD_SITE + LD_CLINIC + '</head>'
    body = '<main class="article"><h1>페이지를 찾을 수 없습니다</h1><p>주소가 변경되었거나 아직 공개되지 않은 글입니다.</p><a class="button" href="/">아트의원 홈으로</a></main>'
    return head + '<body><a class="skip-link" href="#site-content">본문 바로가기</a>' + HEADER + QUICK + '<div id="site-content">' + body + '</div>' + FOOTER + '</body></html>'

# ---------- 출력 ----------
if D.exists():
    for child in D.iterdir():
        if child.name in ('images', 'fonts'): continue
        shutil.rmtree(child) if child.is_dir() else child.unlink()
for sub in ('images', 'fonts'):
    src = R / 'public' / sub
    if (D / sub).exists(): shutil.rmtree(D / sub)
    shutil.copytree(src, D / sub)
for f in ('favicon.png', 'favicon.ico', '_headers', '_redirects'):
    if (R / 'public' / f).exists(): shutil.copy(R / 'public' / f, D / f)

routes = []
write('index.html', home_page()); routes.append('/')
write('about.html', about_page()); routes.append('/about')
write('contact.html', contact_page()); routes.append('/contact')
write('404.html', not_found_page())
for t in TREATMENTS:
    write('treatments/' + t['slug'] + '.html', treatment_page(t)); routes.append('/treatments/' + t['slug'])
for a in ITEMS:
    write('journal/' + a['slug'] + '.html', post_page(a)); routes.append('/journal/' + a['slug'])
for topic in [None] + TREATMENTS:
    n = 1
    while True:
        html_text, total = blog_page(n, topic)
        write(blog_file(n, topic['slug'] if topic else None), html_text); routes.append(blog_path(n, topic['slug'] if topic else None))
        if n >= total: break
        n += 1

# sitemap.xml (app/sitemap.ts)
urls = [absolute(p) for p in ['/', '/about', '/contact', '/blog'] + ['/treatments/' + t['slug'] for t in TREATMENTS]]
sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
for u in urls: sm += f'<url>\n<loc>{u}</loc>\n</url>\n'
for a in ITEMS: sm += f'<url>\n<loc>{absolute("/journal/" + a["slug"])}</loc>\n' + (f'<lastmod>{a["publishedAt"]}</lastmod>\n' if a['_at'] else '') + '</url>\n'
write('sitemap.xml', sm + '</urlset>\n')
# rss.xml (app/rss.xml/route.ts)
items = ''.join('<item><title>' + xml_escape(a['title']) + '</title><link>' + xml_escape(absolute('/journal/' + a['slug'])) + '</link><guid isPermaLink="true">' + xml_escape(absolute('/journal/' + a['slug'])) + '</guid><description>' + xml_escape(article_feed_html(a)) + '</description>' + (f'<pubDate>{utc_string(a["_at"])}</pubDate>' if a['_at'] else '') + '</item>' for a in reversed(ITEMS))
write('rss.xml', '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>' + xml_escape(SITE_NAME) + '</title><link>' + xml_escape(O) + '</link><description>시술 상담 전 확인할 정보</description><language>ko</language>' + items + '</channel></rss>')
# robots.txt (app/robots.ts)
write('robots.txt', ('User-Agent: *\nAllow: /\n' if LIVE else 'User-Agent: *\nDisallow: /\n') + '\nSitemap: ' + O + '/sitemap.xml\n')
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

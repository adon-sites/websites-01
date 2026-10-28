# Public runtime output must not be mistaken for legacy generator source.
from pathlib import Path as _CmsPath
import shutil as _cms_shutil
for _cms_name in ('client','server','.openai','_appgen_meta'):
    _cms_path=_CmsPath(__file__).resolve().parents[1]/'dist'/_cms_name
    if _cms_path.exists():_cms_shutil.rmtree(_cms_path)
from pathlib import Path
import json, re, html, math, datetime
from xml.sax.saxutils import escape as xml_escape
from backlink_policy import publication_links_for

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist'
C=json.loads((ROOT/'content/company.json').read_text())
ORIGIN=C['origin'].rstrip('/')
ESC=html.escape
POLICY=json.loads((ROOT/'content/publication.json').read_text())
all_articles=json.loads((ROOT/'content/reviewed-articles.json').read_text())
# Markdown posts (content/posts/*.md) are prepended, newest first; future dates are held back.
from markdown_posts import load_markdown_posts
_md_posts=load_markdown_posts(ROOT)
assert not ({a['id'] for a in _md_posts}&{a['id'] for a in all_articles}), 'markdown slug collides with an existing article id'
all_articles=_md_posts+all_articles
if POLICY['stage'] in ('private_carousel_preparation','private_content_distribution'):
    assert POLICY['allowArticleRendering'] and not POLICY['allowSearchIndexing']
    assert not C['searchIndexing'] and len(all_articles)==POLICY.get('expectedArticleCount',6)
    assert all(a.get('status')=='private_ready' and not a.get('publishedAt') for a in all_articles)
if POLICY['stage']=='preparation':
    assert not POLICY['allowArticleRendering'] and not POLICY['allowSearchIndexing']
    assert not C['searchIndexing'], 'Preparation sites must block indexing'
    assert all_articles==[], 'No manuscripts are permitted during setup'
assert ORIGIN.startswith('https://') and not ORIGIN.endswith('/'), 'Set this Site own origin before building'
articles=[]
for original in all_articles:
    a=dict(original)
    for key in ('image','alt','width','height'):a.pop(key,None)
    if not POLICY['allowArticleRendering'] or a.get('status') not in ('private_ready','published'):continue
    if C['searchIndexing'] and a.get('status')=='private_ready' and a['id'] not in POLICY.get('existingPublicArticleIds',[]):continue
    if a.get('content_origin')=='user_supplied_final_archive':
        import hashlib
        assert a.get('import_validation_passed') and a.get('import_batch')=='user-final-4648-20260921'
        assert hashlib.sha256(re.sub(r'\s+','','\n\n'.join(p for s in a['sections'] for p in s['paragraphs'])).encode()).hexdigest()==a['body_sha256']
    else:
        assert a.get('editorial_review_passed'), 'Reviewed carousel content required'
    if a.get('status')=='published':
        assert a.get('publishedAt'), 'Actual publication timestamp required'
        parsed=datetime.datetime.fromisoformat(a['publishedAt'].replace('Z','+00:00'))
        assert parsed.tzinfo and parsed<=datetime.datetime.now(datetime.timezone.utc), 'Publication time must be actual, not future'
    else:
        assert not a.get('publishedAt') and (not C['searchIndexing'] or a['id'] in POLICY.get('existingPublicArticleIds',[]))
    assert re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',a['slug'])
    a['path']='/blog/'+a['slug']+'/'
    articles.append(a)
assert len({a['id'] for a in articles})==len(articles)
assert len({a['slug'] for a in articles})==len(articles)
if C['searchIndexing']:assert all(a['status']=='published' or a['id'] in POLICY.get('existingPublicArticleIds',[]) for a in articles)
if C['searchIndexing']:
    from urllib.parse import urlsplit
    assert POLICY['stage']=='public' and POLICY['allowSearchIndexing']
    assert C.get('customDomain') and urlsplit(ORIGIN).hostname==C['customDomain']
features=json.loads((ROOT/'content/carousel.json').read_text())
assert len(features)==6 and [f['slot'] for f in features]==list(range(1,7))
assert len({f['image'] for f in features})==6
by_id={a['id']:a for a in articles}
featured=[]
for feature in features:
    assert (OUT/feature['image'].lstrip('/')).is_file()
    if feature.get('status') not in ('private_ready','published'):continue
    assert feature.get('articleId') in by_id, 'A visible carousel card must link to a real rendered post'
    a=by_id[feature['articleId']]
    assert feature['status']==a['status']
    assert a not in featured, 'Each carousel slot needs a different article'
    a.update({k:feature[k] for k in ('image','alt','width','height')})
    featured.append(a)
# Clean only generated pages, including stale post/pagination output.
import shutil
if (OUT/'blog').exists():shutil.rmtree(OUT/'blog')
if (OUT/'category').exists():shutil.rmtree(OUT/'category')
for f in OUT.rglob('*.html'):f.unlink()
if (OUT/'category').exists():
    for _d in sorted((p for p in (OUT/'category').rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):
        if not any(_d.iterdir()):_d.rmdir()

def inline_html(value):
    result=[];start=0
    for match in re.finditer(r'\[([^\]\n]+)\]\((https?://[^\s)]+)\)',value):
        result.extend([ESC(value[start:match.start()]),'<a href="'+ESC(match.group(2))+'">'+ESC(match.group(1))+'</a>']);start=match.end()
    result.append(ESC(value[start:]));return ''.join(result)

def reference_links(article):
    refs=[]
    for item in article.get('source_urls',[]):
        if isinstance(item,str):refs.append(('참고 자료',item))
        elif item.get('url'):refs.append((item.get('title',item.get('label','참고 자료')),item['url']))
    return '<section><h2>참고 자료</h2><ul>'+''.join('<li><a href="'+ESC(url)+'">'+ESC(label)+'</a></li>' for label,url in refs)+'</ul></section>' if refs else ''

def jscript(data):
    return '<script type="application/ld+json">'+json.dumps(data,ensure_ascii=False).replace('<','\\u003c')+'</script>'

def brand():
    return '<a class="brand" href="/" aria-label="애드온 홈"><img class="logo" src="/images/brand/adon-logo.svg" alt="" width="345" height="124" decoding="async"><span class="brand-text"><strong>애드온</strong><small>HOSPITAL MARKETING</small></span></a>'

def navigation(active):
    links=[('/','병원 광고대행'),('/blog/','마케팅 인사이트'),('/#contact','문의·회사 정보')]
    return ''.join(f'<a href="{p}"'+(' class="active" aria-current="page"' if active==p else '')+f'>{t}</a>' for p,t in links)

def footer():
    return f'''<footer class="footer"><div class="footer-inner"><strong>애드온 AD-ON</strong><p>병원 정보를 정확하게 정리하고, 필요한 곳에서 읽히도록.</p><nav aria-label="하단 메뉴"><a href="/">메인</a><a href="/blog/">마케팅 인사이트</a><a href="mailto:{C['email']}">이메일 문의</a></nav><p>상호 {C['name']} (AD-ON) · 대표 {C['representative']} · 사업자등록번호 {C['businessNumber']}<br>{C['address']}<br>이메일 <a href="mailto:{C['email']}">{C['email']}</a></p><p>검색 노출과 상담 성과는 운영 상황 및 검색 환경에 따라 달라질 수 있습니다.</p><p>© 2026 AD-ON. All rights reserved.</p></div></footer>'''

def layout(title,description,path,body,active='/',extra=None,article=None):
    canonical=ORIGIN+path
    robots='index,follow,max-image-preview:large' if C['searchIndexing'] else 'noindex,nofollow,noarchive'
    schema={'@context':'https://schema.org','@type':'Organization','@id':ORIGIN+'/#organization','name':'애드온','alternateName':'AD-ON','url':ORIGIN+'/','email':C['email'],'address':{'@type':'PostalAddress','streetAddress':C['address'],'addressCountry':'KR'},'taxID':C['businessNumber']}
    if article:
        schema={'@context':'https://schema.org','@type':'BlogPosting','headline':article['title'],'description':description,'url':canonical,'mainEntityOfPage':canonical,'author':{'@type':'Organization','name':'애드온'},'publisher':{'@type':'Organization','name':'애드온','url':ORIGIN+'/'},'inLanguage':'ko-KR'}
        if article.get('image'):
            _io={'@type':'ImageObject','url':ORIGIN+article['image'],'width':article.get('width',860),'height':article.get('height',860),'caption':article.get('alt','')}
            schema['image']=_io;schema['mainEntityOfPage']={'@type':'WebPage','@id':canonical,'primaryImageOfPage':_io}
        if C['searchIndexing'] and article.get('publishedAt'):
            schema['datePublished']=article['publishedAt']
            schema['dateModified']=article.get('modifiedAt',article['publishedAt'])
    icon="/images/brand/adon-favicon.svg"
    verification=f'<meta name="naver-site-verification" content="{ESC(C["verification"])}">' if C.get('verification') else ''
    if article and article.get('image'):
        verification+=f'<meta property="og:image" content="{ORIGIN+article["image"]}"><meta property="og:image:width" content="{article.get("width",860)}"><meta property="og:image:height" content="{article.get("height",860)}"><meta property="og:image:alt" content="{ESC(article["alt"])}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{ORIGIN+article["image"]}">'
    elif path=='/' and featured and featured[0].get('image'):
        verification+=f'<meta property="og:image" content="{ORIGIN+featured[0]["image"]}"><meta property="og:image:width" content="{featured[0].get("width",860)}"><meta property="og:image:height" content="{featured[0].get("height",860)}"><meta property="og:image:alt" content="{ESC(featured[0]["alt"])}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{ORIGIN+featured[0]["image"]}">'
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{ESC(title)} | 애드온</title><meta name="description" content="{ESC(description)}"><meta name="robots" content="{robots}"><link rel="canonical" href="{canonical}"><meta property="og:type" content="{'article' if article else 'website'}"><meta property="og:locale" content="ko_KR"><meta property="og:site_name" content="애드온 병원마케팅"><meta property="og:title" content="{ESC(title)} | 애드온"><meta property="og:description" content="{ESC(description)}"><meta property="og:url" content="{canonical}"><meta name="theme-color" content="#1d1c21"><link rel="icon" type="image/svg+xml" href="{icon}"><link rel="stylesheet" href="/style.css"><link rel="alternate" type="application/rss+xml" title="애드온 인사이트" href="/rss.xml">{verification}{jscript(schema)}{jscript(extra) if extra else ''}</head><body><a class="skip" href="#main-content">본문 바로가기</a><aside class="sidebar">{brand()}<nav aria-label="주 메뉴">{navigation(active)}</nav><div class="side-bottom"><p>블로그 · 카페 · 플레이스<br>홈페이지 · 검색 콘텐츠</p><a class="button" href="mailto:{C['email']}">이메일 상담</a> <a class="button" href="{C['openChat']}" target="_blank" rel="noopener">카카오 오픈채팅</a></div></aside><header class="mobile-header">{brand()}<details><summary>메뉴</summary><nav aria-label="모바일 메뉴">{navigation(active)}</nav></details></header><main id="main-content" class="main"><div class="wrap">{body}</div></main>{footer()}</body></html>'''

def write(path,content):
    p=OUT/('index.html' if path=='/' else path.lstrip('/')+'index.html')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(content)

def consultation():
    return f'''<section class="consultation" id="contact"><span class="eyebrow">CONSULTATION</span><h2>어떤 정보를, 어디에 전할지<br>함께 정리해보세요.</h2><p>병원의 현재 운영 채널과 필요한 작업을 알려주세요.<br>원고·이미지·홈페이지 중 필요한 업무 범위부터 확인합니다.</p><a class="button" href="mailto:{C['email']}">이메일로 문의하기</a> <a class="button" href="{C['openChat']}" target="_blank" rel="noopener">카카오 오픈채팅</a></section>'''

def sidebar():
    result=f'''<aside class="aside"><section class="aside-block"><span class="eyebrow">CONTACT</span><h3>병원마케팅 문의</h3><p>현재 운영 중인 채널과<br>필요한 작업을 보내주세요.</p><a href="mailto:{C['email']}">{C['email']}</a></section><section class="aside-block"><span class="eyebrow">COMPANY</span><h3>애드온 AD-ON</h3><p>서비스 / 광고대행·웹 제작<br>대표 / {C['representative']}<br>사업자번호 / {C['businessNumber']}</p><p>{C['address']}</p></section><section class="aside-block"><span class="eyebrow">READ MORE</span><h3>함께 읽는 인사이트</h3><ul>'''+''.join(f'<li><a href="{a["path"]}">{ESC(a["title"])}</a></li>' for a in featured[:5])+'''</ul></section></aside>'''
    if not featured:result=re.sub(r'<section class="aside-block"><span class="eyebrow">READ MORE</span>.*?</section>','',result)
    return result

def _markdown_bundle_section(article):
    links=article['publication_backlinks']
    return '<section class="hospital-links publication-backlinks link-bundle" aria-label="관련 사이트 안내"><h2>관련 사이트 안내</h2><ul>'+''.join(f'<li><a href="{ESC(x["url"],quote=True)}">{ESC(x["keyword"])}</a></li>' for x in links)+'</ul></section>'

def hospital_links():
    return '<section class="hospital-links" aria-label="병원 홈페이지 안내"><h2>병원 홈페이지 안내</h2><ul>'+''.join(f'<li><a href="{l["url"]}">{l["label"]}</a></li>' for l in C['hospitalLinks'])+'</ul></section>'


def publication_links(article):
    if article.get('content_origin')=='markdown':return _markdown_bundle_section(article)
    links=publication_links_for(article)
    if not links:return hospital_links()
    return '<section class="hospital-links publication-backlinks" aria-label="관련 사이트 안내"><h2>관련 사이트 안내</h2><ul>'+''.join(f'<li><a href="{ESC(x["url"],quote=True)}">{ESC(x["keyword"])}</a></li>' for x in links)+'</ul></section>'

feature_html='<section class="feature-grid" aria-label="주요 마케팅 가이드">'
item_list=[]
for i,a in enumerate(featured):
    feature_html+=f'''<a class="feature" href="{a['path']}"><img src="{a['image']}" alt="{a['alt']}" width="{a['width']}" height="{a['height']}" decoding="async" loading="{'eager' if i<3 else 'lazy'}"><div class="feature-body"><span class="eyebrow">{a['category']}</span><h3>{ESC(a['title'])}</h3><span class="read">더 읽기 →</span></div></a>'''
    item_list.append({'@type':'ListItem','position':i+1,'name':a['title'],'url':ORIGIN+a['path'],'image':ORIGIN+a['image']})
feature_html+='</section>'
if not featured:feature_html=''
carousel_schema={'@context':'https://schema.org','@type':'ItemList','name':'애드온 주요 마케팅 가이드','numberOfItems':len(item_list),'itemListOrder':'https://schema.org/ItemListOrderAscending','itemListElement':item_list} if item_list else None

home_sections=[
 ('service','01. SERVICE','채널마다 필요한 정보를, 맡은 역할에 맞게', '<p>홈페이지에서 진료 안내를 읽는 사람과 지도에서 위치를 확인하는 사람은 서로 다른 정보를 찾습니다. 애드온은 글을 작성하기 전에 독자가 어디에서 들어오고 무엇을 확인하려는지 정리합니다. 채널에 맞는 안내와 다음 행동을 연결하는 것이 운영의 출발점입니다.</p><div class="service-list"><div><strong>블로그</strong><p>상담 전 자주 나오는 질문을 원고 주제로 정리합니다.</p></div><div><strong>카페</strong><p>게시판의 맥락에 맞춰 확인된 정보를 전달합니다.</p></div><div><strong>플레이스</strong><p>방문에 필요한 업체 정보와 사진을 점검합니다.</p></div><div><strong>홈페이지</strong><p>각 페이지의 목적과 내부 이동 경로를 다듬습니다.</p></div></div>'),
 ('why','02. WHY','방문하기 전에 생기는 질문에 답해야 합니다', '<p>처음 방문하는 사람은 위치, 준비 사항, 예약 방식부터 확인합니다. 필요한 내용이 흩어져 있거나 서로 다르면 문의를 해야만 다음 단계로 넘어갈 수 있습니다. 병원이 알고 있는 정보를 독자가 이해할 수 있는 순서로 정리하는 일이 그래서 중요합니다.</p><p>운영 중인 채널에서 반복해서 나오는 질문을 모으고, 이미 설명된 부분과 빠진 부분을 구분합니다. 새 글이 필요한 경우에는 독립된 주제로 작성하고, 기존 안내가 오래됐다면 해당 페이지를 먼저 수정합니다.</p>'),
 ('content','03. CONTENT','한 편마다 다른 질문, 확인한 자료로 쓰는 원고', '<p>제목의 지역명이나 단어 몇 개를 바꿔 같은 설명을 반복하지 않습니다. 글마다 해결할 질문과 사용할 자료를 정하고, 본문에서 그 답을 찾을 수 있게 구성합니다. 실제로 경험하지 않은 일을 환자 후기처럼 서술하거나 확인되지 않은 수치를 더하지 않습니다.</p><ul><li>작성 전: 독자의 질문과 사실 자료 확인</li><li>검토: 제목·본문·사진 설명의 일치 여부 확인</li><li>게시 전: 기존 원고와 질문·문장·구성 중복 점검</li><li>게시 후: 공개 주소와 변경 내용을 기록</li></ul>'),
 ('channel','04. CHANNEL','지도와 홈페이지에서도 같은 정보를 만날 수 있도록', '<p>병원 이름과 주소, 연락처가 채널마다 다르면 같은 곳인지 다시 확인하게 됩니다. 기준이 되는 업체 정보를 정하고 홈페이지, 지도, 예약 화면에서 일관되게 안내하는지 살펴봅니다. 운영시간이 바뀔 때에는 텍스트뿐 아니라 사진에 적힌 안내도 함께 확인합니다.</p><p>홈페이지는 모바일 화면에서 읽기 쉬운지, 필요한 페이지를 바로 열 수 있는지도 점검합니다. 검색에서 들어온 사람이 제목에서 기대한 내용을 실제 본문에서 확인하도록 만드는 것이 핵심입니다.</p>'),
 ('process','05. PROCESS','자료 확인부터 게시 이후 점검까지', '<ol class="steps"><li><strong>현황 확인</strong>기존 채널, 공개 페이지와 필요한 작업을 살펴봅니다.</li><li><strong>주제 설계</strong>핵심 질문을 나누고 원고별 역할을 정합니다.</li><li><strong>작성과 확인</strong>제공된 사실 자료로 작성하고 담당자가 내용을 검토합니다.</li><li><strong>게시와 연결</strong>확인한 콘텐츠를 올리고 관련 안내로 이어지게 합니다.</li><li><strong>변경 기록</strong>게시 주소와 수정 사항, 다음 점검 항목을 남깁니다.</li></ol>'),
 ('standard','06. STANDARD','작업 내용과 확인한 결과를 구분해 안내합니다', '<p>글을 올린 것, 검색 로봇이 읽은 것, 실제 검색 결과에 나온 것은 서로 다른 상태입니다. 애드온은 진행한 작업과 확인한 결과를 나눠 기록합니다. 확인하지 않은 순위나 성과를 추정해 완료로 표시하지 않습니다.</p><p>설명은 독자가 이해할 수 있는 말로 작성하고, 진료에 관한 내용은 병원에서 확인한 범위로 다룹니다. 수정이 필요한 정보를 발견하면 기록을 남겨 다음 운영에서도 같은 혼선이 반복되지 않도록 정리합니다.</p>')]
home_body=feature_html+'<div class="breadcrumbs">HOME › 병원 광고대행</div><span class="eyebrow">HOSPITAL MARKETING / AD-ON</span><h1>병원 마케팅,<br>정보의 기본부터 실행까지.</h1><p class="lead">블로그 · 카페 · 플레이스 · 홈페이지<br>병원의 정보를 정리하고, 읽는 사람의 다음 행동을 연결합니다.</p><div class="columns"><div class="article-body"><nav class="toc" aria-label="본문 목차"><span class="eyebrow">CONTENTS</span><ol>'
home_body+=''.join(f'<li><a href="#{sid}">{heading}</a></li>' for sid,label,heading,content in home_sections)+'</ol></nav>'
home_body+=''.join(f'<section id="{sid}"><span class="eyebrow">{label}</span><h2>{heading}</h2>{content}</section>' for sid,label,heading,content in home_sections)
home_body+='</div>'+sidebar()+'</div>'+consultation()
write('/',layout('병원 광고대행 · 블로그·카페·홈페이지 마케팅','애드온은 병원 블로그·카페 콘텐츠와 플레이스·홈페이지 정보를 정리합니다. 원고 작성부터 게시 이후 점검까지 필요한 업무를 안내합니다.','/',home_body,extra=carousel_schema))

categories=json.loads((ROOT/'content/categories.json').read_text())
for category in categories:
    category['article_ids']=[a['id'] for a in articles if a['category']==category['name']]
(ROOT/'content/categories.json').write_text(json.dumps(categories,ensure_ascii=False,indent=2)+'\n')
category_paths={c['name']:'/category/'+c['slug']+'/' for c in categories}
for _m in reversed(_md_posts):
    for _c in categories:
        if _c['name']==_m['category'] and _m['id'] not in _c['article_ids']:_c['article_ids'].insert(0,_m['id'])
def category_nav():
    return '<nav class="toc category-nav" aria-label="글 카테고리"><strong>카테고리</strong><ul><li><a href="/blog/">전체 글</a></li>'+''.join('<li><a href="'+category_paths[c['name']]+'">'+ESC(c['name'])+' ('+str(len(c['article_ids']))+')</a></li>' for c in categories)+'</ul></nav>'
for i,a in enumerate(articles):
    body=f'<div class="breadcrumbs"><a href="/">HOME</a> › <a href="/blog/">마케팅 인사이트</a> › <a href="{category_paths[a["category"]]}">{ESC(a["category"])}</a></div><div class="columns"><article><header class="article-heading"><span class="eyebrow">{a["category"]}</span><h1>{ESC(a["title"])}</h1><p class="lead">{a["description"]}</p><div class="meta">애드온 편집팀</div></header><div class="article-content">'
    if a.get('image'):
        body+=f'<figure class="cover guide-cover"><img src="{a["image"]}" alt="{ESC(a["alt"])}" width="{a["width"]}" height="{a["height"]}" loading="eager" fetchpriority="high"><figcaption>주제 이해를 돕기 위해 제작한 이미지</figcaption></figure>'
    for s in a['sections']:
        if s['heading']:body+='<h2>'+ESC(s['heading'])+'</h2>'
        body+=''.join('<p>'+inline_html(p)+'</p>' for p in s['paragraphs'])
    body+=reference_links(a)
    body+='</div>'+publication_links(a)+'<nav class="post-nav" aria-label="이전 다음 글">'
    if i>0:body+=f'<a href="{articles[i-1]["path"]}">← {ESC(articles[i-1]["title"])}</a>'
    else:body+='<span></span>'
    if i<len(articles)-1:body+=f'<a href="{articles[i+1]["path"]}">{ESC(articles[i+1]["title"])} →</a>'
    body+='</nav><p><a href="'+category_paths[a['category']]+'">같은 카테고리 글 보기</a> · <a href="/blog/">전체 글 보기</a></p></article>'+sidebar()+'</div>'+consultation()
    _page=layout(a['title'],a['description'],a['path'],body,active='/blog/',article=a)
    if a.get('short_title'):
        _page=_page.replace('<title>'+ESC(a['title'])+' | 애드온</title>','<title>'+ESC(a['short_title'])+'</title>',1)
        _page=_page.replace('<meta property="og:title" content="'+ESC(a['title'])+' | 애드온">','<meta property="og:title" content="'+ESC(a['short_title'])+'">',1)
    write(a['path'],_page)

PER_PAGE=10
page_count=max(1,math.ceil(len(articles)/PER_PAGE))
listing_sets=[('/blog/','마케팅 인사이트',articles)]+[(category_paths[c['name']],c['name'],[a for a in articles if a['category']==c['name']]) for c in categories]
category_page_paths=[]
for base_path,category_title,category_articles in listing_sets:
  local_page_count=max(1,math.ceil(len(category_articles)/PER_PAGE))
  for page in range(1,local_page_count+1):
    path=base_path if page==1 else base_path+f'page/{page}/'
    if base_path!='/blog/':category_page_paths.append(path)
    posts=category_articles[(page-1)*PER_PAGE:page*PER_PAGE]
    title=category_title+(f' · {page}페이지' if page>1 else '')
    description=f'애드온의 콘텐츠 기획, 채널 운영과 홈페이지 점검 원고를 읽어보세요. 마케팅 인사이트 {page}페이지입니다.'
    body=f'<header class="journal-head"><span class="eyebrow">MARKETING JOURNAL</span><h1>{title}</h1><p class="lead">확인할 정보를 정리하고, 실행하는 방법을 기록합니다.</p><p class="meta">전체 {len(category_articles)}편 · {page} / {local_page_count}페이지</p></header>{category_nav()}<div class="columns"><div><div class="post-grid">'
    if not posts:body+='<div class="empty"><p>아직 등록된 글이 없습니다.</p></div>'
    for a in posts:
        body+=f'<article class="post-card"><a href="{a["path"]}"><div class="post-info"><span class="eyebrow">{a["category"]}</span><h2>{ESC(a["title"])}</h2><p>{a["description"]}</p><span class="read">더 읽기 →</span></div></a></article>'
    body+='</div><nav class="pagination" aria-label="글 목록 페이지">'
    for n in (sorted({1,local_page_count,*range(max(1,page-2),min(local_page_count,page+2)+1)}) if articles else []):
        p=base_path if n==1 else base_path+f'page/{n}/'
        body+=f'<span aria-current="page">{n}</span>' if n==page else f'<a href="{p}" aria-label="{n}페이지">{n}</a>'
    body+='</nav>'+hospital_links()+'</div>'+sidebar()+'</div>'+consultation()
    write(path,layout(title,description,path,body,active='/blog/'))

error=layout('페이지를 찾을 수 없습니다','요청한 페이지가 없거나 주소가 변경되었습니다.','/404/', '<div class="empty"><span class="eyebrow">404</span><h1>페이지를 찾을 수 없습니다.</h1><p>주소를 확인하거나 글 목록에서 필요한 내용을 찾아보세요.</p><a class="button" href="/blog/">글 목록으로 이동</a></div>')
(OUT/'404.html').write_text(error.replace('content="index,follow,max-image-preview:large"','content="noindex,follow"'))
public_paths=['/','/blog/']+[f'/blog/page/{n}/' for n in range(2,page_count+1)]+[a['path'] for a in articles]
public_paths+=category_page_paths
indexed_paths=public_paths if C['searchIndexing'] else []
sitemap='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{xml_escape(ORIGIN+p)}</loc></url>' for p in indexed_paths)+'</urlset>'
(OUT/'sitemap.xml').write_text(sitemap)
from search_feeds import build_rss
rss=build_rss(ROOT,ORIGIN,articles if C['searchIndexing'] else [])
(OUT/'rss.xml').write_text(rss)
(OUT/'robots.txt').write_text(('User-agent: *\nAllow: /\nSitemap: '+ORIGIN+'/sitemap.xml\n') if C['searchIndexing'] else 'User-agent: *\nDisallow: /\n')
(OUT/'_headers').write_text('/*\n  X-Robots-Tag: '+('index, follow' if C['searchIndexing'] else 'noindex, nofollow, noarchive')+'\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  X-Frame-Options: SAMEORIGIN\n/images/*\n  Cache-Control: public, max-age=86400\n/style.css\n  Cache-Control: public, max-age=3600\n')
status={'sitePages':len(public_paths),'storedArticles':len(all_articles),'renderedArticles':len(articles),'publicArticles':len(articles) if C['searchIndexing'] else 0,'customDomain':C['customDomain'],'searchIndexing':C['searchIndexing'],'publicationMode':POLICY['stage'],'carouselSlots':6,'visibleCarouselItems':len(featured),'draftCarouselSlots':6-len(featured),'privateReadyCarouselItems':sum(a['status']=='private_ready' for a in featured),'ordinaryArticlesTextOnly':True,'sitemapUrls':len(indexed_paths),'remaining':['개별 도메인 결정 및 연결','HTTPS 확인','추가 원고가 있을 때만 작성·검수 및 반영' ,'공개 범위 및 검색 허용 전환','검색 도구 등록과 실제 수집·색인 확인']}
(ROOT/'content/build-status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(status,ensure_ascii=False))

# Apply this independently managed site design after generating all routes.
import subprocess, sys
subprocess.run([sys.executable,str(ROOT/"scripts/design.py")],check=True)

# Reapply the site keyword mapping and network links after the site design.
subprocess.run([sys.executable,str(ROOT/"scripts/apply_keyword_settings.py")],check=True)

# Preserve content while delivering smaller responsive images.
import subprocess, sys
subprocess.run([sys.executable,str(ROOT/"scripts/optimize_images.py")],check=True)

# Keep visible article dates on every future build.
import subprocess, sys
subprocess.run([sys.executable,str(ROOT/"scripts/visible_dates.py")],check=True)

# Sort complete archives after rendering visible dates.
subprocess.run([sys.executable,str(ROOT/"scripts/sort_article_lists.py")],check=True)

# Keep approved keyword links on existing and future published articles.
import subprocess, sys
subprocess.run([sys.executable,str(ROOT/"scripts/extra_clinic_links.py")],check=True)

# Reapply the homepage-only editorial and keyword representative after route generation.
subprocess.run([sys.executable,str(ROOT/"scripts/homepage_editorial.py")],check=True)

# Preserve first-visit image and stylesheet optimizations after every content build.
import runpy as _speed_runpy
_speed_runpy.run_path(str(ROOT/"scripts/optimize_first_visit.py"), run_name="__main__")

# ---- extra-info (2026-10-23): content/extra-info.json 규칙을 dist 본문 하단에 반영 (tools/extra_info.py apply) ----
def _ei_apply():
    import subprocess, sys as _s, pathlib as _pl
    t = _pl.Path(__file__).resolve().parents[1] / 'tools' / 'extra_info.py'
    if t.exists(): subprocess.run([_s.executable, '-I', str(t), 'apply'], check=False)
_ei_apply()

# ---- carousel 2-B (2026-10-27): 홈 카드 6장의 대상 페이지 대표 이미지 = 그 카드 JPG (tools/patch_cards.py, 멱등) ----
import subprocess as _cs, sys as _csys
_cs.run([_csys.executable,'-I',str(ROOT/'tools'/'patch_cards.py'),str(OUT)],check=True)

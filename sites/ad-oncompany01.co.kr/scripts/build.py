# Remove only generated Worker packaging before rebuilding the original static site.
from pathlib import Path as _CmsPath
import shutil as _cms_shutil
for _cms_name in ('client','server','.openai','_appgen_meta'):
    _cms_path=_CmsPath(__file__).resolve().parents[1]/'dist'/_cms_name
    if _cms_path.exists():_cms_shutil.rmtree(_cms_path)
from pathlib import Path
import json, re, html, math, datetime, sys, importlib.util
from xml.sax.saxutils import escape as xml_escape
from urllib.parse import quote, urlencode
from publication_backlink_policy import effective_publication_backlinks

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist'
C=json.loads((ROOT/'content/company.json').read_text())
ORIGIN=C['origin'].rstrip('/')
ESC=html.escape
state_spec=importlib.util.spec_from_file_location('content_state', ROOT/'scripts/content-state.py')
state=importlib.util.module_from_spec(state_spec)
state_spec.loader.exec_module(state)
articles=[]
legacy_source_ids={'blog-question-design':242,'cafe-information-post':246,'place-information-consistency':244,'website-crawl-basics':250,'integrated-search-observation':248,'agency-work-scope':252,'business-name-reservation':1895,'autocomplete-observation':1894,'search-snippet-review':1893,'quarterly-content-plan':1892,'content-asset-library':1891,'new-branch-content':1890,'promotion-closing':1889,'anonymous-operation-example':1888,'outsourcing-brief':1887,'underperforming-article-review':1886}
source_index=json.loads((ROOT/'content/adviser-source-index.json').read_text())
source_by_id={a['source_id']:a for a in source_index['posts']}
blocks=[(False,b) for b in (ROOT/'content/articles-adviser.txt').read_text().split('@@ ')[1:]]
for manuscript in sorted((ROOT/'content').glob('adviser-batch-*.txt')):
    blocks.extend((True,b) for b in manuscript.read_text().split('@@ ')[1:])
for mapped,block in blocks:
    line,body=block.split('\n',1)
    if mapped:
        source_id,line=line.split('|',1)
        source_id=int(source_id)
    slug,category,title,description=line.split('|',3)
    if not mapped:source_id=legacy_source_ids[slug]
    sections=[]
    for part in body.strip().split('\n## '):
        if not sections: sections.append({'heading':None,'text':part.strip()})
        else:
            heading,text=part.split('\n',1)
            sections.append({'heading':heading.strip(),'text':text.strip()})
    a={'slug':slug,'category':category,'title':title,'description':description,'sections':sections,'date':'2026-09-20','path':f'/2026/09/20/{slug}/','status':'draft_pending_semantic_review','source_id':source_id,'source_url':source_by_id[source_id]['source_url'],'source_title':source_by_id[source_id]['title']}
    articles.append(a)
assert len({a['source_id'] for a in articles})==len(articles),'A source article was mapped more than once'
(ROOT/'content/articles.json').write_text(json.dumps(articles,ensure_ascii=False,indent=2))

ASSETS={
 'search':('검색 정보를 살피는 돋보기와 콘텐츠 화면','통합검색 콘텐츠'),
 'place':('방문 위치를 안내하는 지도와 초록색 위치 표시','플레이스 정보 관리'),
 'cafe':('질문과 답을 주고받는 말풍선','카페 콘텐츠'),
 'blog':('질문과 설명을 정리하는 노트와 펜','블로그 콘텐츠'),
 'website':('페이지 구조를 보여주는 노트북 화면','웹사이트 운영'),
 'operation':('마케팅 작업을 확인하는 일정표와 체크리스트','마케팅 운영'),
 'consult':('이메일과 대화를 상징하는 봉투와 말풍선','이메일·카카오 상담')}
FEATURED_SLUGS=['blog-question-design','place-information-consistency','cafe-information-post','integrated-search-observation','website-crawl-basics','agency-work-scope']
FEATURED_ASSETS=['search','place','cafe','blog','website','operation']
by_slug={a['slug']:a for a in articles}
featured=[by_slug[slug] for slug in FEATURED_SLUGS]
for _i,(a,asset) in enumerate(zip(featured,FEATURED_ASSETS),1):
    a.update(image=f'/images/carousel-0{_i}-860.jpg',alt=f'애드온 {ASSETS[asset][1]} 안내 이미지',width=860,height=860,imageWidth=860,imageHeight=860)
(ROOT/'content/articles.json').write_text(json.dumps(articles,ensure_ascii=False,indent=2))

if '--catalog-only' in sys.argv:
    print(json.dumps({'authored':len(articles),'remaining':len(source_by_id)-len(articles)}))
    raise SystemExit(0)

all_articles=articles
release_file=ROOT/'content/publication.json'
release=json.loads(release_file.read_text()) if release_file.exists() else {'enabled':False,'sourceIds':[]}
approved,review_decisions=state.eligible_articles(ROOT,all_articles,release)
if release.get('enabled'):
    articles=approved
    for a in articles:
        a['status']='approved_for_publication'
        a['publishedAt']=release.get('articlePublishedAt',{}).get(str(a['source_id']),release['publishedAt'])
    by_slug={a['slug']:a for a in articles}
    assert all(slug in by_slug for slug in FEATURED_SLUGS),'All homepage features must pass review before public release'
    featured=[by_slug[slug] for slug in FEATURED_SLUGS]

health_file=ROOT/'content/health-4452-articles.json'
if health_file.exists():
    health_articles=json.loads(health_file.read_text())
    assert all(a.get('content_origin')=='library_health_4452' and a.get('publishedAt') for a in health_articles)
    articles=health_articles+articles
# Markdown posts (content/posts/*.md) are prepended, newest first; future dates are held back.
from markdown_posts import load_markdown_posts
_md_posts=load_markdown_posts(ROOT)
for _m in _md_posts:_m.update(source_id=-1,date=_m['allocation_date_kst'])  # never enters the review ledger or the source_id-ordered sidebar
assert not ({a['slug'] for a in _md_posts}&{a['slug'] for a in articles}), 'markdown slug collides with an existing article'
articles=_md_posts+articles

# These HTML files are generated here; remove obsolete draft routes before rendering.
for old_page in OUT.rglob('*.html'):
    old_page.unlink()
for _top in ('category','blog','2026'):
    if (OUT/_top).exists():
        for _d in sorted((p for p in (OUT/_top).rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):
            if not any(_d.iterdir()):_d.rmdir()

receipt_file=ROOT/'content/publication-receipt.json'
receipt=json.loads(receipt_file.read_text()) if receipt_file.exists() else {}
verified_hashes=receipt.get('articleHashes',{}) if receipt.get('accessMode')=='public' and receipt.get('deploymentStatus')=='succeeded' else {}
confirmed_ids={a['source_id'] for a in all_articles if verified_hashes.get(str(a['source_id']))==state.content_hash(a)}

references=json.loads((ROOT/'content/article-references.json').read_text()) if (ROOT/'content/article-references.json').exists() else {}

for a in all_articles:
    a['status']='publicly_published' if a['source_id'] in confirmed_ids else 'approved_for_publication' if review_decisions.get(a['source_id']) else 'draft_pending_semantic_review'
(ROOT/'content/articles.json').write_text(json.dumps(all_articles,ensure_ascii=False,indent=2))

def figure(asset,caption='',eager=False):
    return f'<figure class="content-figure"><img src="/images/{asset}.webp" alt="{ASSETS[asset][0]}" width="1024" height="1024" loading="{"eager" if eager else "lazy"}"><figcaption>{ESC(caption or ASSETS[asset][1])}</figcaption></figure>'

def jscript(data):
    return '<script type="application/ld+json">'+json.dumps(data,ensure_ascii=False).replace('<','\\u003c')+'</script>'

def contact_buttons():
    return f'<div class="contact-actions"><a class="button" href="mailto:{C["email"]}">이메일 상담</a><a class="button kakao" href="{C["openChat"]}" target="_blank" rel="noopener">카카오 오픈채팅</a></div>'

def brand():
    return '<a class="brand" href="/" aria-label="애드온 홈"><img class="logo" src="/images/brand/adon-logo-white.svg" alt="" width="345" height="124" decoding="async"><span class="brand-text"><strong>애드온</strong><small>HOSPITAL MARKETING</small></span></a>'

def navigation(active):
    links=[('/','병원 광고대행'),('/blog/','마케팅 인사이트'),('/#contact','문의·회사 정보')]
    return ''.join(f'<a href="{p}"'+(' class="active" aria-current="page"' if active==p else '')+f'>{t}</a>' for p,t in links)

def footer():
    return f'''<footer class="footer"><div class="footer-inner"><strong>애드온 AD-ON</strong><p>병원 정보를 정확하게 정리하고, 필요한 곳에서 읽히도록.</p><nav aria-label="하단 메뉴"><a href="/">메인</a><a href="/blog/">마케팅 인사이트</a><a href="mailto:{C['email']}">이메일 문의</a></nav><p>상호 {C['name']} (AD-ON) · 대표 {C['representative']} · 사업자등록번호 {C['businessNumber']}<br>{C['address']}<br>이메일 <a href="mailto:{C['email']}">{C['email']}</a><br><a href="{C['openChat']}" target="_blank" rel="noopener">카카오 오픈채팅 상담</a></p><p>검색 노출과 상담 성과는 운영 상황 및 검색 환경에 따라 달라질 수 있습니다.</p><p>© 2026 AD-ON. All rights reserved.</p></div></footer>'''

def location_map():
    # Search the street address, leaving the office floor/unit in readable text.
    # No invented coordinates or unverified business place ID are used.
    street=C['address'].split(',',1)[0]
    query=quote(street,safe='')
    embed='https://maps.google.com/maps?'+urlencode({'q':street,'z':16,'hl':'ko','output':'embed'})
    return f'''<section class="location" id="location" aria-labelledby="location-heading"><div class="location-info"><span class="eyebrow">LOCATION</span><h2 id="location-heading">애드온 오시는 길</h2><address>{ESC(C['address'])}</address><div class="map-actions"><a class="button" href="https://map.naver.com/p/search/{query}" target="_blank" rel="noopener noreferrer">네이버 지도 열기</a><a class="button map-secondary" href="https://map.kakao.com/?q={query}" target="_blank" rel="noopener noreferrer">카카오맵 열기</a></div></div><div class="location-map"><iframe src="{ESC(embed)}" title="애드온 사업장 위치 지도 — {ESC(street)}" width="720" height="360" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe></div></section>'''

def layout(title,description,path,body,active='/',extra=None,article=None):
    canonical=ORIGIN+path
    robots='index,follow,max-image-preview:large' if C['searchIndexing'] else 'noindex,follow'
    schema={'@context':'https://schema.org','@type':'ProfessionalService','@id':ORIGIN+'/#organization','name':'애드온','alternateName':'AD-ON','url':ORIGIN+'/','email':C['email'],'address':{'@type':'PostalAddress','streetAddress':C['address'],'addressCountry':'KR'},'taxID':C['businessNumber']}
    if article:
        schema={'@context':'https://schema.org','@type':'BlogPosting','headline':article['title'],'description':description,'url':canonical,'mainEntityOfPage':canonical,'author':{'@type':'Organization','name':'애드온'},'publisher':{'@type':'Organization','name':'애드온','url':ORIGIN+'/'},'inLanguage':'ko-KR'}
        if article.get('image'):
            _io={'@type':'ImageObject','url':ORIGIN+article['image'],'width':860,'height':860,'caption':article.get('alt','')}
            schema['image']=_io;schema['mainEntityOfPage']={'@type':'WebPage','@id':canonical,'primaryImageOfPage':_io}
        if article.get('publishedAt'):
            schema['datePublished']=article['publishedAt']
            schema['dateModified']=article['publishedAt']
    icon="/images/brand/adon-favicon.svg"
    image_meta=''
    if not article or article.get('image'):
        og_image=ORIGIN+(article['image'] if article else featured[0]['image'])
        og_alt=article['alt'] if article else featured[0]['alt']
        image_meta=f'<meta property="og:image" content="{og_image}"><meta property="og:image:width" content="860"><meta property="og:image:height" content="860"><meta property="og:image:alt" content="{ESC(og_alt)}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{og_image}">'
    verification=f'<meta name="naver-site-verification" content="{ESC(C["verification"])}">' if C.get('verification') else ''
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{ESC(title)} | 애드온</title><meta name="description" content="{ESC(description)}"><meta name="robots" content="{robots}"><link rel="canonical" href="{canonical}"><meta property="og:type" content="{'article' if article else 'website'}"><meta property="og:locale" content="ko_KR"><meta property="og:site_name" content="애드온 병원마케팅"><meta property="og:title" content="{ESC(title)} | 애드온"><meta property="og:description" content="{ESC(description)}"><meta property="og:url" content="{canonical}">{image_meta}<meta name="theme-color" content="#03c75a"><link rel="icon" type="image/svg+xml" href="{icon}"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&family=Noto+Serif+KR:wght@500;600;700&display=swap" rel="stylesheet"><link rel="stylesheet" href="/style.css"><link rel="alternate" type="application/rss+xml" title="애드온 인사이트" href="/rss.xml">{verification}{jscript(schema)}{jscript(extra) if extra else ''}</head><body><a class="skip" href="#main-content">본문 바로가기</a><header class="site-header"><div class="header-inner">{brand()}<nav class="desktop-nav" aria-label="주 메뉴">{navigation(active)}</nav><a class="button header-contact" href="{C['openChat']}" target="_blank" rel="noopener">카카오 상담</a><details class="mobile-menu"><summary>메뉴</summary><nav aria-label="모바일 메뉴">{navigation(active)}</nav></details></div></header><main id="main-content" class="main"><div class="wrap">{body}{location_map()}</div></main>{footer()}</body></html>'''

def write(path,content):
    p=OUT/('index.html' if path=='/' else path.lstrip('/')+'index.html')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(content)

def consultation():
    return f'''<section class="consultation" id="contact"><span class="eyebrow">CONSULTATION</span><h2>어떤 정보를, 어디에 전할지<br>함께 정리해보세요.</h2><p>병원의 현재 운영 채널과 필요한 작업을 알려주세요.<br>원고·이미지·홈페이지 중 필요한 업무 범위부터 확인합니다.</p>{contact_buttons()}</section>'''

def sidebar():
    return f'''<aside class="aside"><section class="aside-block"><span class="eyebrow">CONTACT</span><h3>병원마케팅 문의</h3><p>현재 운영 중인 채널과<br>필요한 작업을 보내주세요.</p><a href="mailto:{C['email']}">{C['email']}</a><p><a href="{C['openChat']}" target="_blank" rel="noopener">카카오 오픈채팅 상담</a></p></section><section class="aside-block"><span class="eyebrow">COMPANY</span><h3>애드온 AD-ON</h3><p>서비스 / 광고대행·웹 제작<br>대표 / {C['representative']}<br>사업자번호 / {C['businessNumber']}</p><p>{C['address']}</p></section><section class="aside-block"><span class="eyebrow">READ MORE</span><h3>함께 읽는 인사이트</h3><ul>'''+''.join(f'<li><a href="{a["path"]}">{a["title"]}</a></li>' for a in sorted(articles,key=lambda x:x['source_id'],reverse=True)[:5])+'''</ul></section></aside>'''

def _markdown_bundle_section(article):
    links=article['publication_backlinks']
    return '<section class="hospital-links publication-backlinks link-bundle" aria-label="관련 사이트 안내"><h2>관련 사이트 안내</h2><ul>'+''.join(f'<li><a href="{ESC(x["url"],quote=True)}">{ESC(x["keyword"])}</a></li>' for x in links)+'</ul></section>'

def hospital_links():
    return '<section class="hospital-links" aria-label="병원 홈페이지 안내"><h2>병원 홈페이지 안내</h2><ul>'+''.join(f'<li><a href="{l["url"]}">{l["label"]}</a></li>' for l in C['hospitalLinks'])+'</ul></section>'


def publication_links(article):
    if article.get('content_origin')=='markdown':return _markdown_bundle_section(article)
    links=effective_publication_backlinks(article)
    if not links:return hospital_links()
    return '<section class="hospital-links publication-backlinks" aria-label="관련 사이트 안내"><h2>관련 사이트 안내</h2><ul>'+''.join(f'<li><a href="{ESC(x["url"],quote=True)}">{ESC(x["keyword"])}</a></li>' for x in links)+'</ul></section>'

feature_html='<section class="feature-grid" aria-label="주요 마케팅 가이드">'
item_list=[]
for i,a in enumerate(featured):
    feature_html+=f'''<a class="feature" href="{a['path']}"><img src="{a['image']}" alt="{a['alt']}" width="860" height="860" loading="{'eager' if i<3 else 'lazy'}"><div class="feature-body"><span class="eyebrow">애드온</span><h3>{a['title']}</h3><span class="read">더 읽기 →</span></div></a>'''
    item_list.append({'@type':'ListItem','position':i+1,'name':a['title'],'url':ORIGIN+a['path'],'image':ORIGIN+a['image']})
feature_html+='</section>'

home_sections=[('service', '01. SERVICE', '병원의 안내를 찾는 화면마다, 필요한 내용을 채웁니다', '<p>어떤 글을 몇 편 만들지 결정하기 전에 병원이 현재 어디에서 소개되는지 살펴봅니다. 검색 결과의 짧은 소개, 지도에 표시되는 방문 정보, 홈페이지의 상세 설명은 읽는 시간도 쓰임도 다릅니다. 애드온은 각 화면에서 독자가 확인해야 할 항목을 정한 뒤 그에 맞는 원고와 이미지를 준비합니다.</p><div class="service-list"><div><strong>블로그 원고</strong><p>한 글에서 해결할 질문을 좁히고 설명과 예시를 배치합니다.</p></div><div><strong>카페 안내</strong><p>해당 게시판에서 허용하는 범위와 질문의 상황을 살핍니다.</p></div><div><strong>플레이스 관리</strong><p>출입구·운영시간처럼 방문 판단에 쓰이는 정보를 확인합니다.</p></div><div><strong>웹사이트 제작</strong><p>서비스 소개부터 문의까지 문서의 순서와 연결을 설계합니다.</p></div></div>'), ('why', '02. WHY', '검색한 사람이 다시 묻지 않아도 이해할 수 있게', '<p>안내문을 만든 사람에게 익숙한 표현도 처음 읽는 사람에게는 설명이 필요합니다. 예를 들어 건물명만 적힌 위치 안내보다 어느 출입구로 들어와야 하는지 적힌 안내가 방문 준비에 도움이 됩니다. 콘텐츠 검토에서는 이런 간격을 찾아 실제로 답할 수 있는 정보로 채웁니다.</p><p>문의가 반복되는 부분은 기존 페이지에 답이 없는지, 답이 있어도 찾기 어려운지 나눠 살펴봅니다. 앞의 경우에는 필요한 설명을 보충하고, 뒤의 경우에는 제목이나 배치를 조정합니다. 수정 이유를 정해 두면 같은 내용을 여러 게시물에 늘어놓는 일을 줄일 수 있습니다.</p>'), ('content', '03. CONTENT', '주제는 분명하게, 설명은 원고마다 독립적으로', '<p>원고를 시작할 때 핵심 질문, 확인할 근거, 다루지 않을 범위를 먼저 적습니다. 비슷한 주제를 다루더라도 독자가 처한 상황이나 판단해야 하는 사항이 다르다면 그 차이가 본문에 드러나야 합니다. 표현만 바꾸는 방식으로 글 수를 늘리지 않고 문단이 맡은 역할까지 검토합니다.</p><ul><li>제목에서 약속한 내용을 본문이 실제로 설명하는지 읽습니다.</li><li>사진과 도표가 주변 설명과 맞는지 대조합니다.</li><li>기존 글과 비슷한 문장뿐 아니라 질문과 결론의 반복을 살핍니다.</li><li>확인되지 않은 경험담이나 효과 수치를 문장에 추가하지 않습니다.</li></ul>'), ('channel', '04. CHANNEL', '한 번 바뀐 정보가 다른 채널에도 반영되도록', '<p>주소나 운영시간이 변경되면 수정할 곳은 홈페이지 한 페이지에 그치지 않을 수 있습니다. 카드 이미지에 들어간 문구, 예전 공지, 지도 소개에도 이전 정보가 남습니다. 변경 항목과 노출 위치를 짝지은 목록을 두고 채널별 반영 상태를 확인합니다.</p><p>내용이 길어질 때에는 모든 정보를 첫 화면에 담기보다 요약과 상세 안내를 연결합니다. 모바일 방문자가 링크를 눌렀을 때 예상한 설명으로 이동하는지, 문의 버튼에서 실제 연락 수단을 열 수 있는지도 함께 살핍니다.</p>'), ('process', '05. PROCESS', '요청 내용을 작업 목록으로 바꾸는 순서', '<ol class="steps"><li><strong>자료 모으기</strong>현재 운영 주소와 사용 가능한 사진, 최신 업체 정보를 받습니다.</li><li><strong>우선순위 합의</strong>누락된 안내와 오래된 설명 중 먼저 손볼 항목을 정합니다.</li><li><strong>초안 구성</strong>주제별 질문에 맞춰 문장·이미지·관련 페이지를 배치합니다.</li><li><strong>담당자 검토</strong>사실관계와 표현을 확인하고 필요한 수정 사항을 반영합니다.</li><li><strong>게시 확인</strong>실제 주소에서 문서와 링크를 확인한 뒤 다음 점검 내용을 남깁니다.</li></ol>'), ('standard', '06. STANDARD', '완료한 작업은 근거와 함께 확인할 수 있습니다', '<p>원고 초안과 공개된 페이지를 같은 상태로 기록하지 않습니다. 초안에는 검토할 내용을, 공개 기록에는 실제 게시 주소와 확인 시점을 남깁니다. 검색 수집이나 노출은 별도로 확인할 항목이므로 콘텐츠를 올렸다는 사실만으로 성과를 단정하지 않습니다.</p><p>병원에서 제공한 자료도 사용 범위와 최신 여부를 확인합니다. 진료 관련 설명의 담당 검토와 사진의 사용 가능 여부를 작업 과정에 포함하고, 보완이 필요한 항목은 미확인 상태로 표시합니다. 이렇게 남긴 기록은 이후 정보가 바뀌었을 때 다시 살펴볼 기준이 됩니다.</p>')]
home_sections.append(('closing','07. CONTACT','병원 마케팅, 다음 작업을 함께 정리해요','<p>현재 운영 중인 채널과 해결하고 싶은 문제를 알려주세요. 준비된 자료와 필요한 업무를 살펴보고, 어떤 정보부터 정리할지 순서를 맞춥니다.</p>'+contact_buttons()))
section_assets={'service':'operation','why':'place','content':'blog','process':'website','closing':'consult'}
home_body=feature_html+'<div class="columns home-columns"><article class="article-body"><nav class="breadcrumbs" aria-label="현재 위치"><a href="/">HOME</a> › SERVICE › 병원마케팅</nav><header class="home-heading"><h1>병원마케팅,<br>애드온과 차근차근.</h1><p class="meta">애드온 마케팅팀 · 블로그·카페·홈페이지 운영</p>'+contact_buttons()+'</header>'+figure('search','병원의 정보를 정리하는 마케팅 파트너 · 애드온',True)+'<p>검색 결과에서 처음 만나는 소개부터 방문 직전에 확인하는 위치까지, 병원 정보는 여러 화면에 나뉘어 있습니다. 각 화면에 필요한 설명을 채우고 서로 다른 안내가 없는지 살피는 것이 온라인 운영의 출발점입니다.</p><p>애드온은 콘텐츠 기획과 원고 작성, 홈페이지와 채널 정보 점검을 연결해 진행합니다. 아래에서 작업의 범위와 순서를 확인해 보세요.</p><nav class="toc" aria-label="본문 목차"><span class="eyebrow">CONTENTS</span><ol>'
home_body+=''.join(f'<li><a href="#{sid}">{heading}</a></li>' for sid,label,heading,content in home_sections)+'</ol></nav>'
for sid,label,heading,content in home_sections:
    home_body+=f'<section id="{sid}"><span class="eyebrow">{label}</span><h2>{heading}</h2>'+(figure(section_assets[sid]) if sid in section_assets else '')+content+'</section>'
home_body+='<nav class="topic-tags" aria-label="관련 주제">'+''.join(f'<a href="/blog/">#{tag}</a>' for tag in ['병원마케팅','병원블로그','카페콘텐츠','플레이스','홈페이지','콘텐츠기획','애드온'])+'</nav></article>'+sidebar()+'</div>'+consultation()
write('/',layout('병원마케팅 · 블로그·카페·홈페이지 운영','애드온의 병원 마케팅 안내. 검색 콘텐츠 기획과 블로그·카페 원고, 플레이스·홈페이지 정보 관리, 운영 점검의 범위와 진행 과정을 확인하세요.','/',home_body,extra={'@context':'https://schema.org','@type':'ItemList','name':'애드온 주요 마케팅 가이드','numberOfItems':6,'itemListOrder':'https://schema.org/ItemListOrderAscending','itemListElement':item_list}))

for i,a in enumerate(articles):
    body=f'<div class="breadcrumbs"><a href="/">HOME</a> › <a href="/blog/">마케팅 인사이트</a> › {a["category"]}</div><div class="columns"><article><header class="article-heading"><span class="eyebrow">{a["category"]}</span><h1>{a["title"]}</h1><p class="lead">{a["description"]}</p><div class="meta">애드온 편집팀</div></header><div class="article-content">'
    if a.get('image'):
        body+=f'<figure class="post-cover"><img src="{a["image"]}" alt="{ESC(a["alt"])}" width="860" height="860" loading="eager" fetchpriority="high"></figure>'
    for s in a['sections']:
        if s['heading']:body+='<h2>'+ESC(s['heading'])+'</h2>'
        body+=''.join('<p>'+ESC(x)+'</p>' for x in s.get('paragraphs',[s.get('text','')]))
    if a['slug']=='website-crawl-basics':body+='<p class="meta">참고: <a href="https://searchadvisor.naver.com/guide/site-summary">네이버 서치어드바이저 사이트 상태 안내</a></p>'
    for ref in references.get(str(a['source_id']),[]):
        body+=f'<p class="meta">참고: <a href="{ESC(ref["url"])}">{ESC(ref["title"])}</a></p>'
    body+='</div>'+publication_links(a)+'<nav class="post-nav" aria-label="이전 다음 글">'
    if i>0:body+=f'<a href="{articles[i-1]["path"]}">← {articles[i-1]["title"]}</a>'
    else:body+='<span></span>'
    if i<len(articles)-1:body+=f'<a href="{articles[i+1]["path"]}">{articles[i+1]["title"]} →</a>'
    body+='</nav><p><a href="/blog/">전체 글 보기</a></p></article>'+sidebar()+'</div>'+consultation()
    _page=layout(a['title'],a['description'],a['path'],body,active='/blog/',article=a)
    if a.get('short_title'):
        _page=_page.replace('<title>'+ESC(a['title'])+' | 애드온</title>','<title>'+ESC(a['short_title'])+'</title>',1)
        _page=_page.replace('<meta property="og:title" content="'+ESC(a['title'])+' | 애드온">','<meta property="og:title" content="'+ESC(a['short_title'])+'">',1)
    write(a['path'],_page)

PER_PAGE=10
page_count=math.ceil(len(articles)/PER_PAGE)
for page in range(1,page_count+1):
    path='/blog/' if page==1 else f'/blog/page/{page}/'
    posts=articles[(page-1)*PER_PAGE:page*PER_PAGE]
    title='병원마케팅 인사이트'+(f' · {page}페이지' if page>1 else '')
    description=f'애드온의 병원 마케팅 실무 글을 읽어보세요. 콘텐츠 기획, 채널 운영과 홈페이지 점검 안내 {page}페이지입니다.'
    body=(feature_html if page==1 else '')+f'<header class="journal-head"><span class="eyebrow">MARKETING JOURNAL</span><h1>{title}</h1><p class="lead">확인할 정보를 정리하고, 실행하는 방법을 기록합니다.</p><p class="meta">전체 {len(articles)}편 · {page} / {page_count}페이지</p></header><div class="columns"><div><div class="post-grid">'
    for a in posts:
        image_html=f'<img src="{a["image"]}" alt="{ESC(a["alt"])}" width="860" height="860" loading="lazy">' if a.get('image') else ''
        card_class='post-card' if a.get('image') else 'post-card post-card-text'
        body+=f'<article class="{card_class}"><a href="{a["path"]}">{image_html}<div class="post-info"><span class="eyebrow">{a["category"]}</span><h2>{a["title"]}</h2><p>{a["description"]}</p><span class="read">더 읽기 →</span></div></a></article>'
    body+='</div><nav class="pagination" aria-label="글 목록 페이지">'
    for n in sorted({1,page_count,*range(max(1,page-2),min(page_count,page+2)+1)}):
        p='/blog/' if n==1 else f'/blog/page/{n}/'
        body+=f'<span aria-current="page">{n}</span>' if n==page else f'<a href="{p}" aria-label="{n}페이지">{n}</a>'
    body+='</nav>'+hospital_links()+'</div>'+sidebar()+'</div>'+consultation()
    write(path,layout(title,description,path,body,active='/blog/'))

error=layout('페이지를 찾을 수 없습니다','요청한 페이지가 없거나 주소가 변경되었습니다.','/404/', '<div class="empty"><span class="eyebrow">404</span><h1>페이지를 찾을 수 없습니다.</h1><p>주소를 확인하거나 글 목록에서 필요한 내용을 찾아보세요.</p><a class="button" href="/blog/">글 목록으로 이동</a></div>')
(OUT/'404.html').write_text(error.replace('content="index,follow,max-image-preview:large"','content="noindex,follow"'))
public_paths=['/','/blog/']+[f'/blog/page/{n}/' for n in range(2,page_count+1)]+[a['path'] for a in articles]
indexed_paths=public_paths if C['searchIndexing'] else []
sitemap='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{xml_escape(ORIGIN+p)}</loc></url>' for p in indexed_paths)+'</urlset>'
(OUT/'sitemap.xml').write_text(sitemap)
from search_feeds import build_rss
rss=build_rss(ROOT,ORIGIN,articles if C['searchIndexing'] else [])
(OUT/'rss.xml').write_text(rss)
(OUT/'robots.txt').write_text(('User-agent: *\nAllow: /\nSitemap: '+ORIGIN+'/sitemap.xml\n') if C['searchIndexing'] else 'User-agent: *\nDisallow: /\n')
(OUT/'style.css').write_text((ROOT/'scripts/site.css').read_text())
(OUT/'_headers').write_text('/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  X-Frame-Options: SAMEORIGIN\n/images/*\n  Cache-Control: public, max-age=86400\n/style.css\n  Cache-Control: public, max-age=3600\n')
remaining=[]
if len(all_articles)<len(source_by_id) or not (len(all_articles)==len(source_by_id) and all(review_decisions.values())):
    remaining.append('Write and semantically review the remaining source topics')
if not C['customDomain']:
    remaining.extend(['Confirm custom domain and DNS authority','Activate custom domain and SSL'])
if not C['searchIndexing']:
    remaining.append('Add user-owned search verification token and submit sitemap/RSS')
(ROOT/'content/build-status.json').write_text(json.dumps({'sitePages':len(public_paths),'authoredArticles':len(all_articles),'draftArticles':sum(not review_decisions[a['source_id']] for a in all_articles),'semanticallyApprovedArticles':sum(review_decisions.values()),'releaseArticles':len(articles) if release.get('enabled') else 0,'publicArticles':len(confirmed_ids),'referencePostInventory':len(source_by_id),'remainingArticles':len(source_by_id)-len(all_articles),'entireReferenceCorpusRewritten':len(all_articles)==len(source_by_id),'entireCorpusSemanticallyReviewed':len(all_articles)==len(source_by_id) and all(review_decisions.values()),'customDomain':C['customDomain'],'searchIndexing':C['searchIndexing'],'publicationMode':'reviewed_release' if release.get('enabled') else 'private_review','sourceScopeConfirmed':True,'executionMode':'in_conversation_no_external_api','remaining':remaining},ensure_ascii=False,indent=2))
article_by_source={a['source_id']:a for a in all_articles}
ledger=[]
for source in source_index['posts']:
    a=article_by_source.get(source['source_id'])
    status='publicly_published' if source['source_id'] in confirmed_ids else 'approved_for_publication' if review_decisions.get(source['source_id']) else 'draft_pending_semantic_review' if a else 'awaiting_rewrite'
    ledger.append({'source_id':source['source_id'],'source_title':source['title'],'source_url':source['source_url'],'status':status,'new_slug':a['slug'] if a else None,'new_title':a['title'] if a else None,'new_path':a['path'] if a else None,'publiclyPublished':source['source_id'] in confirmed_ids})
(ROOT/'content/rewrite-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2))
print(json.dumps({'pages':len(public_paths),'articles':len(articles),'list_pages':page_count,'indexing':C['searchIndexing']},ensure_ascii=False))

# Apply this independently managed site design after generating all routes.
import subprocess, sys
subprocess.run([sys.executable,str(ROOT/"scripts/design.py")],check=True)

# Reapply the site keyword mapping and network links after the site design.
subprocess.run([sys.executable,str(ROOT/"scripts/apply_keyword_settings.py")],check=True)

# Keep visible article dates on every future build.
import subprocess, sys
subprocess.run([sys.executable,str(ROOT/"scripts/visible_dates.py")],check=True)

# Sort complete archives after rendering visible dates.
subprocess.run([sys.executable,str(ROOT/"scripts/sort_article_lists.py")],check=True)

# Keep approved keyword links on existing and future published articles.
import subprocess, sys
subprocess.run([sys.executable,str(ROOT/"scripts/extra_clinic_links.py")],check=True)

# Keep the requested homepage editorial and representative guide after all generated output.
subprocess.run([sys.executable,str(ROOT/"scripts/homepage_editorial.py")],check=True)

# Preserve first-visit image and stylesheet optimizations after every content build.
import runpy as _speed_runpy
_speed_runpy.run_path(str(ROOT/"scripts/optimize_first_visit.py"), run_name="__main__")

# Keep local homepage font subsets and layout-matched image selection after builds.
_speed_runpy.run_path(str(ROOT/"scripts/optimize_home_fonts.py"), run_name="__main__")


# ---- extra-info (2026-10-23): content/extra-info.json 규칙을 dist 본문 하단에 반영 (tools/extra_info.py apply) ----
def _ei_apply():
    import subprocess, sys as _s, pathlib as _pl
    t = _pl.Path(__file__).resolve().parents[1] / 'tools' / 'extra_info.py'
    if t.exists(): subprocess.run([_s.executable, '-I', str(t), 'apply'], check=False)
_ei_apply()

# ---- carousel 2-B (2026-10-27): 홈 카드 6장의 대상 페이지 대표 이미지 = 그 카드 JPG (tools/patch_cards.py, 멱등) ----
import subprocess as _cs, sys as _csys
_cs.run([_csys.executable,'-I',str(ROOT/'tools'/'patch_cards.py'),str(OUT)],check=True)

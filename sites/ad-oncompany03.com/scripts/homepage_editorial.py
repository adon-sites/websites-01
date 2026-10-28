"""Apply homepage-only editorial and optional independent representative guide.
Existing imported articles, campaign ledgers and reserve material are never edited.
"""
from pathlib import Path
import json,re,html
R=Path(__file__).resolve().parents[1];D=R/'dist'
C=json.loads((R/'content/company.json').read_text());G=json.loads((R/'content/homepage-editorial.json').read_text());E=html.escape;origin=C['origin'].rstrip('/')
s=(D/'index.html').read_text()
if G.get('guide'):
 f=G['guide']; featured=dict(title=f['title'],category=f['category'],path='/guides/'+f['slug']+'/')
else:
 from publication_hold import load_published_articles
 source=load_published_articles(R) if G.get('articleSource','reviewed-articles.json')=='reviewed-articles.json' else json.loads((R/'content'/G['articleSource']).read_text()); a=next(a for a in source if a.get('id',a['slug'])==G['featuredArticleId']);featured=dict(title=a['title'],category=a['category'],path=a.get('path','/blog/'+a['slug']+'/'))
 assert (D/featured['path'].lstrip('/')/'index.html').is_file(),'Existing published article required'
assert re.sub(r'\s','',C['seo']['primary']) in re.sub(r'\s','',featured['title']), 'First card title must contain current primary keyword'
card=re.search(r'<a class="feature" href="[^"]+">.*?</a>',s,re.S);assert card
new=re.sub(r'href="[^"]+"','href="'+featured['path']+'"',card[0],count=1)
new=re.sub(r'(<h3>).*?(</h3>)',lambda m:m[1]+E(featured['title'])+m[2],new,count=1,flags=re.S)
new=re.sub(r'(<span class="eyebrow">).*?(</span>)',lambda m:m[1]+E(featured['category'])+m[2],new,count=1,flags=re.S)
s=s[:card.start()]+new+s[card.end():]
def schema_update(m):
 obj=json.loads(m[1])
 if obj.get('@type')=='ItemList':obj['itemListElement'][0].update(name=featured['title'],url=origin+featured['path'])
 return '<script type="application/ld+json">'+json.dumps(obj,ensure_ascii=False).replace('<','\\u003c')+'</script>'
s=re.sub(r'<script type="application/ld\+json">(.*?)</script>',schema_update,s,flags=re.S)
def paras(ps):return ''.join('<p>'+E(p)+'</p>' for p in ps)
body='<article class="home-editorial" id="keyword-guide"><header class="home-editorial-intro"><span class="eyebrow">AD-ON · 마케팅 운영 가이드</span><h1>'+E(C['seo']['primary'])+'</h1><p class="home-deck">'+E(G['deck'])+'</p>'+paras(G['intro'])+'</header>'
for i,sec in enumerate(G['sections'],1):body+='<section class="home-practical"><span class="eyebrow">'+str(i).zfill(2)+' · '+E(sec['label'])+'</span><h2>'+E(sec['heading'])+'</h2>'+paras(sec['paragraphs'])+'</section>'
body+='<section class="home-faq" id="homepage-faq"><span class="eyebrow">FAQ</span><h2>'+E(C['seo']['primary'])+' 자주 묻는 질문</h2>'+''.join('<details><summary>'+E(q['question'])+'</summary><p>'+E(q['answer'])+'</p></details>' for q in G['faq'])+'</section>'
body+='<section class="home-company" id="company-information"><span class="eyebrow">COMPANY</span><h2>애드온 회사·문의 안내</h2><dl>'+''.join('<div><dt>'+E(k)+'</dt><dd>'+E(v)+'</dd></div>' for k,v in [('상호',C['name']+' (AD-ON)'),('대표',C['representative']),('사업자등록번호',C['businessNumber']),('소재지',C['address']),('이메일',C['email'])])+'</dl><p class="home-notice">'+E(G['notice'])+'</p></section></article>'
start=re.search(r'<section class="feature-grid[^\"]*".*?</section>',s,re.S);assert start
end=s.find('<section class="hospital-links marketing-network-links"',start.end());assert end>start.end()
s=s[:start.end()]+body+s[end:]
css='''<style id="homepage-editorial-style">.home-editorial{max-width:880px;margin:0 auto 56px;background:#fff;padding:clamp(24px,5vw,64px);border-radius:var(--radius,12px);border:1px solid var(--line,#ddd)}.home-editorial section{padding:40px 0;border-top:1px solid var(--line,#ddd)}.home-editorial-intro{padding-bottom:40px}.home-editorial h1{margin:12px 0 24px;font-size:clamp(30px,3.5vw,48px)}.home-editorial h2{margin:12px 0 24px;font-size:clamp(23px,2.5vw,30px)}.home-editorial h3{font-size:20px}.home-editorial p{font-size:17px;line-height:2;margin:18px 0;word-break:keep-all;overflow-wrap:anywhere}.home-editorial .home-deck{font-size:21px;color:var(--accent,#254763);font-weight:600;line-height:1.7}.home-faq details{border-bottom:1px solid var(--line,#ddd);padding:18px 0}.home-faq summary{cursor:pointer;font-size:18px;font-weight:700;min-height:32px}.home-faq details p{margin-bottom:4px}.home-company dl>div{display:grid;grid-template-columns:130px 1fr;gap:20px;padding:14px 0;border-bottom:1px solid var(--line,#ddd)}.home-company dt{font-weight:700}.home-company dd{margin:0;overflow-wrap:anywhere}.home-editorial .home-notice{font-size:14px;color:var(--muted,#56616d);padding:20px;background:var(--pale,#f4f7f9)}@media(max-width:700px){.home-editorial{padding:26px 22px;margin-top:24px}.home-editorial section{padding:30px 0}.home-company dl>div{grid-template-columns:1fr;gap:4px}.home-editorial p{font-size:16px;line-height:1.95}.home-editorial .home-deck{font-size:19px}.home-faq summary{font-size:17px}}</style>'''
s=re.sub(r'<style id="homepage-editorial-style">.*?</style>','',s,flags=re.S).replace('</head>',css+'</head>',1)
s=re.sub(r'<script type="application/ld\+json" id="homepage-faq-schema">.*?</script>','',s,flags=re.S)
faq={'@context':'https://schema.org','@type':'FAQPage','mainEntity':[{'@type':'Question','name':q['question'],'acceptedAnswer':{'@type':'Answer','text':q['answer']}} for q in G['faq']]}
s=s.replace('</head>','<script type="application/ld+json" id="homepage-faq-schema">'+json.dumps(faq,ensure_ascii=False).replace('<','\\u003c')+'</script></head>',1)
(D/'index.html').write_text(s)
if G.get('guide'):
 t=s; start=re.search(r'<section class="feature-grid[^\"]*".*?</section>',t,re.S);end=t.find('<section class="hospital-links marketing-network-links"',start.end())
 guidebody=body.replace('<h1>'+E(C['seo']['primary'])+'</h1>','<h1>'+E(featured['title'])+'</h1>')
 t=t[:start.start()]+guidebody+t[end:]
 t=re.sub(r'<title>.*?</title>','<title>'+E(featured['title'])+' | 애드온</title>',t,count=1)
 for prop,val in [('og:title',featured['title']+' | 애드온'),('og:url',origin+featured['path']),('og:description',G['deck']),('og:type','article')]:t=re.sub(r'(<meta property="'+prop+r'" content=")[^"]*',lambda m:m[1]+E(val,quote=True),t,count=1)
 t=re.sub(r'(<meta name="description" content=")[^"]*',lambda m:m[1]+E(G['deck'],quote=True),t,count=1)
 t=re.sub(r'(<link rel="canonical" href=")[^"]*',lambda m:m[1]+origin+featured['path'],t,count=1)
 def remove_items(m):return '' if json.loads(m[1]).get('@type')=='ItemList' else m[0]
 t=re.sub(r'<script type="application/ld\+json">(.*?)</script>',remove_items,t,flags=re.S)
 article={'@context':'https://schema.org','@type':'Article','headline':featured['title'],'description':G['deck'],'url':origin+featured['path'],'mainEntityOfPage':origin+featured['path'],'author':{'@type':'Organization','name':C['name']},'inLanguage':'ko-KR'}
 t=t.replace('</head>','<script type="application/ld+json">'+json.dumps(article,ensure_ascii=False)+'</script></head>')
 p=D/featured['path'].lstrip('/')/'index.html';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t)
 sm=(D/'sitemap.xml').read_text();url=origin+featured['path']
 if '<loc>'+url+'</loc>' not in sm:sm=sm.replace('</urlset>','<url><loc>'+url+'</loc></url></urlset>');(D/'sitemap.xml').write_text(sm)
print(json.dumps({'homepage':True,'domain':C['customDomain'],'primary':C['seo']['primary'],'firstCard':featured,'faq':len(G['faq']),'newGuide':bool(G.get('guide'))},ensure_ascii=False))

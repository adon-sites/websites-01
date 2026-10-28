"""Render recorded publication dates without inventing historical dates."""
from pathlib import Path
import json,re,html,datetime
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist'
KST=datetime.timezone(datetime.timedelta(hours=9))
records={}
def remember(path,value,label,priority):
    if not path or not value:return
    try:
        dt=datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
        if dt.tzinfo:dt=dt.astimezone(KST)
        date=dt.date().isoformat()
    except (ValueError,TypeError):return
    path=urlsplit(path).path
    if path not in records or priority>records[path][2]:records[path]=(date,label,priority)
release=ROOT/'content/search-release.json'
if release.exists():
    r=json.loads(release.read_text());m=re.search(r'\d{4}-\d{2}-\d{2}',r.get('authorization',''))
    if m:
        for u in r.get('existingPublicArticleUrls',[]):remember(u,m[0],'공개 확인일',1)
for filename in ['reviewed-articles.json','articles.json','health-4452-articles.json']:
    f=ROOT/'content'/filename
    if not f.exists():continue
    from publication_hold import load_published_articles
    data=load_published_articles(ROOT) if filename=='reviewed-articles.json' else json.loads(f.read_text())
    if not isinstance(data,list):continue
    for a in data:
        path=a.get('path') or '/blog/'+a.get('slug','')+'/'
        remember(path,a.get('publishedAt') or a.get('published_at'),'발행일',3)
for f in (ROOT/'content/publication-runs').rglob('*.json'):
    try:r=json.loads(f.read_text())
    except (ValueError,OSError):continue
    if isinstance(r,dict) and r.get('status') in ['published_verified','deployment_succeeded','published','deployed']:
        remember(r.get('actual_url'),r.get('actual_published_at'),'발행일',4)
from markdown_posts import load_markdown_posts
for a in load_markdown_posts(ROOT):remember(a['path'],a['publishedAt'],'발행일',3)
f=ROOT/'content/date-display-evidence.json'
if f.exists():
    for path,value in json.loads(f.read_text()).get('confirmed_public_paths',{}).items():remember(path,value,'공개 확인일',0)
def markup(path):
    date,label,_=records[path]
    return '<span class="article-date" style="display:block;font-size:0.875rem;line-height:1.6;margin-top:0.5rem;color:inherit">'+label+' <time datetime="'+date+'">'+date.replace('-','.')+'</time></span>'
count=cards=0;unknown=[]
for f in OUT.rglob('*.html'):
    s=f.read_text();old=s
    s=re.sub(r'<span class="article-date"[^>]*>.*?</span>','',s,flags=re.S)
    path='/'+str(f.relative_to(OUT)).removesuffix('index.html')
    if 'class="article-heading"' in s:
        if path in records:
            s=re.sub(r'(<header class="article-heading"[^>]*>.*?</h1>)',lambda m:m[0]+markup(path),s,count=1,flags=re.S);count+=1
        else:unknown.append(path)
    def card(m):
        global cards
        block=m[0];link=re.search(r'<a[^>]+href="([^"]+)"',block)
        target=urlsplit(html.unescape(link[1])).path if link else ''
        if target in records:
            block=re.sub(r'(</h2>)',lambda n:n[0]+markup(target),block,count=1);cards+=1
        return block
    s=re.sub(r'<article class="post-card[^\"]*".*?</article>',card,s,flags=re.S)
    if s!=old:f.write_text(s)
assert not unknown, 'Missing date evidence: '+str(unknown[:10])
print(json.dumps({'dated_articles':count,'dated_cards':cards,'unknown':len(unknown)},ensure_ascii=False))

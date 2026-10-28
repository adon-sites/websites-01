"""Apply persisted keyword settings to static output, without rewriting manuscripts."""
from pathlib import Path
import html, json, re, xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist'
C = json.loads((ROOT / 'content/company.json').read_text())
SEO = C['seo']
ESC = html.escape
TITLE = SEO['primary'] + ' | ' + ' | '.join(SEO['secondary']) + ' | 애드온'
DESCRIPTION = SEO['description']
KEYWORDS = ', '.join([SEO['primary'], *SEO['secondary']])
BLOCK = '<section class="hospital-links marketing-network-links" aria-label="마케팅 서비스 안내"><h2>마케팅 서비스 안내</h2><ul>' + ''.join('<li><a href="'+ESC(x['url'],quote=True)+'">'+ESC(x['label'])+'</a></li>' for x in C['marketingLinks'] if x['url'].rstrip('/') != C['origin'].rstrip('/')) + '</ul></section>'
STYLE = '<style id="marketing-network-style">.marketing-network-links ul{display:flex;flex-wrap:wrap;gap:10px 20px;list-style:none;padding:0;margin:0}.marketing-network-links li{margin:0;max-width:100%}.marketing-network-links a{font-size:1rem;overflow-wrap:anywhere}.marketing-network-links{margin:32px 0;padding-top:24px;border-top:1px solid var(--line,#ddd)}.marketing-network-links h2{font-size:1.1rem}.marketing-keyword-summary{max-width:75ch;line-height:1.8}</style>'

def set_meta(s, attr, key, value):
    tag='<meta '+attr+'="'+key+'" content="'+ESC(value,quote=True)+'">'
    pattern=r'<meta\b(?=[^>]*\b'+attr+r'=[\"\x27]'+re.escape(key)+r'[\"\x27])[^>]*>'
    if re.search(pattern,s,re.I):return re.sub(pattern,lambda _:tag,s,flags=re.I)
    return s.replace('</head>',tag+'</head>',1)

def add_links(s):
    if 'class="hospital-links publication-backlinks"' in s:
        return s
    s=re.sub(r'<section class="hospital-links marketing-network-links".*?</section>','',s,flags=re.S)
    match=re.search(r'<section class="hospital-links".*?</section>',s,re.S)
    if match:return s[:match.end()]+BLOCK+s[match.end():]
    # The homepage has no hospital-links section; insert inside its content container.
    consultation=re.search(r'<section class="consultation"',s)
    if consultation:return s[:consultation.start()]+BLOCK+s[consultation.start():]
    if '</main>' in s:return s.replace('</main>',BLOCK+'</main>',1)
    return s

count=0
for p in OUT.rglob('*.html'):
    s=p.read_text()
    if p.name=='404.html':continue
    s=set_meta(s,'name','keywords',KEYWORDS)
    s=set_meta(s,'property','og:site_name',SEO['primary']+' | 애드온')
    if p==OUT/'index.html':
        s=re.sub(r'<title>.*?</title>',lambda _:'<title>'+ESC(TITLE)+'</title>',s,count=1,flags=re.S)
        for attr,key,value in [('name','description',DESCRIPTION),('property','og:title',TITLE),('property','og:description',DESCRIPTION)]:s=set_meta(s,attr,key,value)
        s=re.sub(r'(<h1\b[^>]*>).*?</h1>',lambda m:m[1]+ESC(SEO['primary'])+'<br>애드온</h1>',s,count=1,flags=re.S)
        s=re.sub(r'<p class="marketing-keyword-summary">.*?</p>','',s,flags=re.S)
        s=re.sub(r'(</h1>)',lambda m:m[1]+'<p class="marketing-keyword-summary">'+ESC(DESCRIPTION)+'</p>',s,count=1)
    s=add_links(s)
    s=re.sub(r'<style id="marketing-network-style">.*?</style>','',s,flags=re.S)
    if 'marketing-network-links' in s:s=s.replace('</head>',STYLE+'</head>',1);count+=1
    p.write_text(s)

rss=OUT/'rss.xml'
tree=ET.parse(rss)
channel=tree.getroot().find('channel')
channel.find('title').text=SEO['primary']+' | 애드온 인사이트'
channel.find('description').text=DESCRIPTION
for item in channel.findall('item'):
    d=item.find('description')
    if d is not None and d.text:
        content=re.sub(r'<section class="hospital-links marketing-network-links".*?</section>','',d.text,flags=re.S)
        if 'publication-backlinks' in content:
            d.text=content
        else:
            d.text=add_links(content) if 'class="hospital-links"' in content else content+BLOCK
tree.write(rss,encoding='utf-8',xml_declaration=True)
print(json.dumps({'domain':C['customDomain'],'primary':SEO['primary'],'linkedPages':count,'rssItems':len(channel.findall('item'))},ensure_ascii=False))

"""Persist the two approved clinic keyword links in generated article footers."""
from pathlib import Path
from html.parser import HTMLParser
import re, json, xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
LINKS=[('소프웨이브','https://brandnewclinicinfo.co.kr/'),('대구필러','http://myseasonclinicinfo.co.kr/')]
PATTERN=r'<section\b(?=[^>]*class="hospital-links(?: publication-backlinks)?")[^>]*>.*?</section>'
class Anchors(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.href=None;self.text=''
    def handle_starttag(self,t,a):
        if t=='a':self.href=dict(a).get('href');self.text=''
    def handle_data(self,d):
        if self.href is not None:self.text+=d
    def handle_endtag(self,t):
        if t=='a' and self.href is not None:self.links.append((self.text,self.href));self.href=None
def apply(text,required=False):
    match=re.search(PATTERN,text,re.S)
    if not match:
        if required:raise AssertionError('Article footer missing')
        return text
    block=match.group(0)
    for keyword,url in LINKS:
        parser=Anchors();parser.feed(block)
        existing=[x for x in parser.links if x[1].rstrip('/')==url.rstrip('/')]
        if existing:
            assert existing==[(keyword,url)],existing
        else:
            assert '</ul>' in block
            block=block.replace('</ul>',f'<li><a href="{url}">{keyword}</a></li></ul>',1)
    return text[:match.start()]+block+text[match.end():]
pages=0
for p in (ROOT/'dist').rglob('*.html'):
    text=p.read_text()
    if 'class="hospital-links publication-backlinks link-bundle"' in text:pages+=1;continue
    article='class="article-content"' in text
    updated=apply(text,article)
    if article:
        parser=Anchors();parser.feed(updated)
        for pair in LINKS:assert parser.links.count(pair)==1,(str(p),pair)
        pages+=1
    if updated!=text:p.write_text(updated)
rss=ROOT/'dist/rss.xml'
if rss.exists():
    tree=ET.parse(rss);changed=False
    for d in tree.findall('./channel/item/description'):
        old=d.text or '';d.text=apply(old);changed|=old!=d.text
    if changed:tree.write(rss,encoding='utf-8',xml_declaration=True)
assert pages>0,'No article pages verified'
print(json.dumps({'extra_clinic_links':True,'article_pages':pages,'keywords':[x[0] for x in LINKS]},ensure_ascii=False))

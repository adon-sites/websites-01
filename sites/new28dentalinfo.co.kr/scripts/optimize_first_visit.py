"""Preserve homepage content while removing critical-path asset round trips.
Run after the normal content build. Originals, other routes, URLs, metadata,
publication dates, carousel order, and outbound links remain unchanged.
"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit
from PIL import Image, ImageOps
import hashlib, html, json, re, sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist'
ATTR = re.compile(r'''\b([\w:-]+)\s*=\s*(["'])(.*?)\2''', re.S)
def attrs(tag): return {m[1].lower(): html.unescape(m[3]) for m in ATTR.finditer(tag)}
def put(tag, key, value):
    pattern = re.compile(r'''\s+''' + re.escape(key) + r'''\s*=\s*(["']).*?\1''', re.S|re.I)
    tag = pattern.sub('', tag)
    return tag[:-1] + ' ' + key + '="' + html.escape(value, quote=True) + '">'
def local(url):
    u = urlsplit(url)
    if u.scheme or u.netloc or not u.path.startswith('/'): return None
    p = (OUT/u.path.lstrip('/')).resolve()
    return p if OUT.resolve() in p.parents and p.is_file() else None

class Invariant(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.skip=0;self.text=[];self.anchors=[];self.metadata=[];self.images=[];self.scripts=[];self.script=None
    def handle_starttag(self,t,a):
        a=dict(a)
        if t=='style':self.skip+=1
        if t=='script':self.skip+=1;self.script=[a,'']
        if t=='a':self.anchors.append(a)
        if t=='meta' or (t=='link' and a.get('rel') not in ['stylesheet','preload']):self.metadata.append((t,a))
        if t=='img':self.images.append({k:v for k,v in a.items() if k not in ['src','srcset','sizes','loading','fetchpriority','decoding','data-speed-original']})
    def handle_data(self,d):
        if self.script is not None:self.script[1]+=d
        elif not self.skip:self.text.append(d)
    def handle_endtag(self,t):
        if t in ['style','script']:self.skip=max(0,self.skip-1)
        if t=='script' and self.script is not None:self.scripts.append(self.script);self.script=None
    def result(self):return [self.text,self.anchors,self.metadata,self.images,self.scripts]

def optimize(root=ROOT):
    global ROOT, OUT
    ROOT=Path(root);OUT=ROOT/'dist';page=OUT/'index.html'
    before=page.read_text();h=before
    # Rebuild only our own prior inline styles, keeping the stylesheet order.
    h=re.sub(r'<style\b[^>]*data-speed-css="([^"]+)"[^>]*>.*?</style>',lambda m:'<link rel="stylesheet" href="'+m[1]+'">',h,flags=re.S)
    h=re.sub(r'<link\b[^>]*data-speed-preload="first-image"[^>]*>','',h)
    h=re.sub(r'<!--speed-font-start-->(.*?)<noscript>(.*?)</noscript><!--speed-font-end-->',lambda m:m[2],h,flags=re.S)
    css_records=[]
    def css(match):
        tag=match[0];a=attrs(tag)
        if a.get('rel')!='stylesheet':return tag
        p=local(a.get('href',''))
        if not p:
            if a.get('href','').startswith('https://fonts.googleapis.com/'):
                return '<!--speed-font-start-->'+put(put(tag,'media','print'),'onload',"this.media='all'")+'<noscript>'+tag+'</noscript><!--speed-font-end-->'
            return tag
        c=p.read_text()
        # These sites use root-relative URLs and no imported external sheets.
        if '@import' in c or '</style' in c.lower():raise AssertionError('Unsupported stylesheet '+str(p))
        def absolute_url(m):
            v=m[1].strip(' \"\'')
            if not v or v.startswith(('/', '#', 'data:', 'http:', 'https:')):return m[0]
            base=Path(a['href'].split('?')[0]).parent
            return 'url("'+str(base/v)+'")'
        c=re.sub(r'url\(([^)]+)\)',absolute_url,c)
        c=re.sub(r'@charset\s+[^;]+;','',c)
        css_records.append({'url':a['href'],'bytes':len(c.encode())})
        media=(' media="'+html.escape(a['media'],quote=True)+'"') if a.get('media') else ''
        return '<style data-speed-css="'+html.escape(a['href'],quote=True)+'"'+media+'>'+c+'</style>'
    h=re.sub(r'<link\b[^>]*>',css,h)
    image_records=[];first=None;index=0
    def image(match):
        nonlocal first,index
        tag=match[0];a=attrs(tag);src=a.get('data-speed-original',a.get('src',''));p=local(src)
        if not p or p.suffix.lower() not in ['.png','.jpg','.jpeg','.webp']:return tag
        if 'logo' in a.get('class','').lower() or 'logo' in p.stem.lower():return tag
        try:
            with Image.open(p) as original:
                if original.width<250 or original.height<200:return tag
                # Leave established responsive images intact and keep originals.
                if (not a.get('srcset') or a.get('data-speed-original')) and not p.stem.endswith('-860'):  # 2026-10-28: 860 카드는 변환만 건너뛰고 eager/preload 처리는 그대로
                    original.load();im=ImageOps.exif_transpose(original)
                    digest=hashlib.sha256(p.read_bytes()).hexdigest()[:12]
                    widths=sorted({min(w,im.width) for w in [400,800,1280]})
                    variants=[]
                    target=OUT/'images/first-visit';target.mkdir(parents=True,exist_ok=True)
                    for w in widths:
                        height=round(im.height*w/im.width)
                        name=f'{p.stem}.{digest}-{w}.webp';dest=target/name
                        if not dest.exists():
                            resized=im.resize((w,height),Image.Resampling.LANCZOS)
                            resized.save(dest,'WEBP',quality=88,method=6)
                        with Image.open(dest) as check:
                            check.load();assert check.size==(w,height)
                        variants.append({'url':'/images/first-visit/'+name,'width':w,'bytes':dest.stat().st_size})
                    fallback=next((v for v in variants if v['width']>=800),variants[-1])
                    if fallback['bytes']<p.stat().st_size:
                        tag=put(tag,'src',fallback['url']);tag=put(tag,'data-speed-original',src)
                        tag=put(tag,'srcset',', '.join(f'{v["url"]} {v["width"]}w' for v in variants))
                        # Preserve 1/2/3-column clinic layouts, conservative for wide cards.
                        sizes='(max-width: 600px) calc(100vw - 40px), (max-width: 1000px) 50vw, 400px'
                        if a.get('loading')=='lazy':sizes='auto, '+sizes
                        tag=put(tag,'sizes',sizes)
                        image_records.append({'original':src,'original_bytes':p.stat().st_size,'variants':variants})
        except (OSError, ValueError) as e:raise AssertionError(str(p)+': '+str(e))
        if index==0:
            tag=put(tag,'loading','eager');tag=put(tag,'fetchpriority','high');first=attrs(tag)
        else:
            tag=put(tag,'loading','lazy')
            if attrs(tag).get('sizes') and not attrs(tag)['sizes'].startswith('auto, '):tag=put(tag,'sizes','auto, '+attrs(tag)['sizes'])
        tag=put(tag,'decoding','async');index+=1
        return tag
    h=re.sub(r'<img\b[^>]*>',image,h)
    if first:
        preload='<link data-speed-preload="first-image" rel="preload" as="image" href="'+html.escape(first['src'],quote=True)+'" fetchpriority="high"'
        if first.get('srcset'):preload+=' imagesrcset="'+html.escape(first['srcset'],quote=True)+'" imagesizes="'+html.escape(first['sizes'],quote=True)+'"'
        preload+='>'
        h=h.replace('<head>','<head>'+preload,1)
    b=Invariant();b.feed(before);a=Invariant();a.feed(h)
    assert b.result()==a.result(),'Homepage content, links, metadata, scripts or image descriptions changed'
    active=re.sub(r'<noscript>.*?</noscript>','',h,flags=re.S)
    assert all(attrs(m[0]).get('media')=='print' for m in re.finditer(r'<link\b[^>]*rel="stylesheet"[^>]*>',active)),'A render-blocking stylesheet remains' 
    assert first and first.get('loading')=='eager'
    if h!=before:page.write_text(h)
    report={'home':str(page),'html_before_bytes':len(before.encode()),'html_after_bytes':len(h.encode()),'blocking_stylesheets_before':len(css_records),'blocking_stylesheets_after':0,'images':image_records,'content_links_metadata_scripts_preserved':True,'first_image':first['src']}
    print(json.dumps(report,ensure_ascii=False))
    return report

if __name__=='__main__':optimize(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT)

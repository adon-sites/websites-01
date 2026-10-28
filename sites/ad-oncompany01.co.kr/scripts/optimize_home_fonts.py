"""Preserve Noto typography while serving only homepage characters locally.
Subsets are made locally from official Noto source files; no site text is sent
to a third party. A new homepage character set refreshes the subset locally.
A dependency/source-download failure preserves the existing Google stylesheet.
"""
from pathlib import Path
from urllib.parse import urlsplit
import subprocess
from PIL import Image,ImageOps
import hashlib,json,re,html
from optimize_first_visit import attrs,put,Invariant
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist';PAGE=OUT/'index.html'
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36'
ORIGINAL='https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&family=Noto+Serif+KR:wght@500;600;700&display=swap'
SIZES='(max-width: 380px) calc(100vw - 74px), (max-width: 520px) calc(50vw - 51px), (max-width: 700px) calc(50vw - 61px), (max-width: 1000px) calc(21vw - 26.04px), (max-width: 1100px) calc(21vw - 28.56px), (max-width: 1250px) calc(21vw - 25.2px), 237.3px'
def semantic(h):
 p=Invariant();p.feed(h);r=p.result();r[2]=[(t,a) for t,a in r[2] if not(t=='link' and a.get('rel')=='preconnect')];return r

def optimize():
 before=PAGE.read_text();h=before;p=Invariant();p.feed(h)
 characters=set(''.join(p.text)+''.join(chr(i) for i in range(32,127))+'→←↗↑−·')
 characters={c for c in characters if c==' ' or not c.isspace()}
 manifest=ROOT/'content/home-fonts.json';saved=json.loads(manifest.read_text()) if manifest.exists() else None
 reusable=saved and characters<=set(saved['characters']) and all((OUT/f['local'].lstrip('/')).is_file() for f in saved['fonts'])
 if not reusable:
  try:
   result=subprocess.run(['/usr/bin/python3',str(ROOT/'scripts/build_home_font_assets.py')],capture_output=True,text=True)
   if result.returncode:raise RuntimeError(result.stderr[-1000:])
   saved=json.loads(manifest.read_text())
  except Exception as e:
   print(json.dumps({'font_optimization':'original-retained','reason':str(e)},ensure_ascii=False));return
 h=re.sub(r'<!--speed-font-start-->.*?<!--speed-font-end-->','',h,flags=re.S)
 h=re.sub(r'<style\b[^>]*data-home-fonts[^>]*>.*?</style>','',h,flags=re.S)
 h=re.sub(r'<link\b[^>]*data-home-font-preload[^>]*>','',h)
 def remove_google(m):
  a=attrs(m[0]);host=urlsplit(a.get('href','')).hostname
  return '' if host in ['fonts.googleapis.com','fonts.gstatic.com'] else m[0]
 h=re.sub(r'<link\b[^>]*>',remove_google,h)
 styles='<style data-home-fonts>'+saved['css']+'</style>'
 preload=''.join('<link data-home-font-preload rel="preload" as="font" type="font/woff2" crossorigin="anonymous" href="'+f['local']+'">' for f in saved['fonts'])
 h=h.replace('</head>',styles+preload+'</head>',1)
 # Match the existing 1/2-column mobile and 42%-width desktop card layout.
 def image(m):
  tag=m[0];a=attrs(tag);src=a.get('data-speed-original',a.get('src',''))
  if not src.startswith('/images/') or 'logo' in src or '-860.jpg' in src:return tag
  original=OUT/src.lstrip('/')
  if not original.is_file():return tag
  im=ImageOps.exif_transpose(Image.open(original));im.load();digest=hashlib.sha256(original.read_bytes()).hexdigest()[:12]
  variants=[];target=OUT/'images/first-visit';target.mkdir(exist_ok=True)
  for w in sorted({min(w,im.width) for w in [320,400,640,800,1024]}):
   f=target/f'{original.stem}.{digest}-{w}.webp'
   if not f.exists():im.resize((w,round(im.height*w/im.width)),Image.Resampling.LANCZOS).save(f,'WEBP',quality=88,method=6)
   variants.append((w,'/'+str(f.relative_to(OUT))))
  tag=put(tag,'src',next(u for w,u in variants if w==400));tag=put(tag,'srcset',', '.join(f'{u} {w}w' for w,u in variants));tag=put(tag,'sizes',('auto, ' if a.get('loading')=='lazy' else '')+SIZES)
  return tag
 h=re.sub(r'<img\b[^>]*>',image,h)
 first=next(attrs(m[0]) for m in re.finditer('<img\\b[^>]*>',h) if attrs(m[0]).get('fetchpriority')=='high')
 def preload_image(m):
  a=attrs(m[0])
  if a.get('data-speed-preload')!='first-image':return m[0]
  if not first.get('srcset'):return put(m[0],'href',first['src'])  # 단일 src(캐러셀 860 JPG)
  return put(put(put(m[0],'href',first['src']),'imagesrcset',first['srcset']),'imagesizes',SIZES)
 h=re.sub(r'<link\b[^>]*>',preload_image,h)
 assert semantic(h)==semantic(before),'Visible content, metadata, links, image descriptions or scripts changed'
 assert 'fonts.googleapis.com' not in h and 'fonts.gstatic.com' not in h
 if h!=before:PAGE.write_text(h)
 print(json.dumps({'font_files':len(saved['fonts']),'font_bytes':sum(f['bytes'] for f in saved['fonts']),'characters':len(saved['characters']),'fonts_served_locally':True,'external_font_requests':0,'sizes':SIZES,'content_preserved':True},ensure_ascii=False))
if __name__=='__main__':optimize()

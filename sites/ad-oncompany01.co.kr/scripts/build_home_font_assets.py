"""Subset official Noto sources locally; no site text is sent outside this process."""
from pathlib import Path
from urllib.request import Request,urlopen
from fontTools import subset
from fontTools.ttLib import TTFont
from optimize_first_visit import Invariant
import hashlib,json,tempfile
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist';cache=Path(tempfile.gettempdir())/'site-noto-font-sources';cache.mkdir(exist_ok=True)
p=Invariant();p.feed((OUT/'index.html').read_text());characters=set(''.join(p.text)+''.join(chr(i) for i in range(32,127))+'→←↗↑−·');characters={c for c in characters if c==' ' or not c.isspace()}
entries=[('notosanskr','NotoSansKR%5Bwght%5D.ttf','Noto Sans KR','400 700'),('notoserifkr','NotoSerifKR%5Bwght%5D.ttf','Noto Serif KR','500 700')]
css=[];records=[];licenses=[];(OUT/'fonts').mkdir(exist_ok=True)
for directory,filename,family,weights in entries:
 url='https://raw.githubusercontent.com/google/fonts/main/ofl/'+directory+'/'+filename;source=cache/(directory+'.ttf')
 if not source.exists():
  with urlopen(Request(url,headers={'User-Agent':'SiteFontBuild/1.0'}),timeout=90) as r:data=r.read(48*1024*1024)
  assert len(data)<48*1024*1024 and data[:4] in [b'\x00\x01\x00\x00',b'OTTO'];source.write_bytes(data)
 original=TTFont(source,recalcTimestamp=False);cmap=original.getBestCmap();points=set(map(ord,characters))&set(cmap)
 font=TTFont(source,recalcTimestamp=False);options=subset.Options();options.layout_features=['*'];options.name_IDs=['*'];options.name_languages=['*'];options.name_legacy=True;options.notdef_outline=True;options.recommended_glyphs=True;options.glyph_names=True;options.hinting=True;options.recalc_timestamp=False
 sub=subset.Subsetter(options=options);sub.populate(unicodes=points);sub.subset(font);font.flavor='woff2'
 digest=hashlib.sha256(source.read_bytes()+json.dumps(sorted(points)).encode()).hexdigest()[:16];local='/fonts/'+directory+'-home.'+digest+'.woff2';dest=OUT/local.lstrip('/');font.save(dest)
 check=TTFont(dest,recalcTimestamp=False);assert set(check.getBestCmap())==points
 axes=lambda f:[(a.axisTag,a.minValue,a.defaultValue,a.maxValue) for a in f['fvar'].axes]
 assert axes(check)==axes(original)
 for cp,glyph in check.getBestCmap().items():assert check['hmtx'][glyph]==original['hmtx'][cmap[cp]],hex(cp)
 css.append('@font-face{font-family:"'+family+'";font-style:normal;font-weight:'+weights+';font-display:swap;src:url("'+local+'") format("woff2");unicode-range:'+','.join('U+'+format(cp,'X') for cp in sorted(points))+'}')
 license_url='https://raw.githubusercontent.com/google/fonts/main/ofl/'+directory+'/OFL.txt';license_file=OUT/'fonts'/('OFL-'+directory+'.txt')
 if not license_file.exists():
  with urlopen(license_url,timeout=45) as r:license_data=r.read()
  assert b'SIL OPEN FONT LICENSE' in license_data;license_file.write_bytes(license_data)
 copyright=' | '.join(sorted({n.toUnicode() for n in original['name'].names if n.nameID==0}))
 records.append({'source':url,'local':local,'bytes':dest.stat().st_size,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'copyright':copyright,'axes_preserved':axes(check),'glyph_advance_metrics_preserved':True,'characters':len(points)})
 licenses.append('/fonts/'+license_file.name)
saved={'characters':''.join(sorted(characters)),'css':'\n'.join(css),'fonts':records,'method':'Local-only fontTools subsets of official Noto fonts, preserving family, glyph advances, variable axes and license metadata. No text transmission.','licenses':licenses}
(ROOT/'content/home-fonts.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'font_bytes':sum(x['bytes'] for x in records),'font_files':len(records),'characters':len(characters)}))

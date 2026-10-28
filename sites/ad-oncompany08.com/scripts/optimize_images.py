from pathlib import Path
import hashlib, json, re
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist'

def optimize(root=ROOT):
    out = root / 'dist'
    mapping = {}
    records = []
    target = out / 'images/optimized'
    target.mkdir(parents=True, exist_ok=True)
    for source in sorted((out / 'images').glob('*.png')):
        with Image.open(source) as original:
            if original.width < 300 or original.height < 300:
                continue
            original.load()
            digest = hashlib.sha256(source.read_bytes()).hexdigest()[:10]
            widths = sorted(set([min(w, original.width) for w in (320, 640, 960, original.width)]))
            variants = []
            for width in widths:
                dest = target / f'{source.stem}.{digest}-{width}.webp'
                height = round(original.height * width / original.width)
                if not dest.exists():
                    resized = original.resize((width, height), Image.Resampling.LANCZOS)
                    resized.save(dest, 'WEBP', quality=85, method=6)
                with Image.open(dest) as check:
                    check.load()
                    assert check.size == (width, height)
                variants.append({'url': '/' + str(dest.relative_to(out)), 'width': width, 'bytes': dest.stat().st_size})
            old = '/' + str(source.relative_to(out))
            mapping[old] = variants
            records.append({'original': old, 'original_bytes': source.stat().st_size, 'width': original.width, 'height': original.height, 'variants': variants})
    changed = 0
    for page in out.rglob('*.html'):
        before = page.read_text()
        def replace_img(match):
            tag = match.group(0)
            src = re.search(r'\bsrc="([^"]+)"', tag)
            if not src or src.group(1) not in mapping:
                return tag
            variants = mapping[src.group(1)]
            tag = tag.replace(src.group(0), 'src="' + variants[-1]['url'] + '"')
            tag = re.sub(r'\s+(?:srcset|sizes)="[^"]*"', '', tag)
            is_home = page == out / 'index.html'
            sizes = '(max-width: 380px) calc(100vw - 36px), (max-width: 700px) calc((100vw - 62px) / 2), (max-width: 1000px) 50vw, 33vw' if is_home else '(max-width: 1000px) calc(100vw - 48px), 800px'
            if 'loading="lazy"' in tag:
                sizes = 'auto, ' + sizes
            if 'decoding=' not in tag:
                tag = tag[:-1] + ' decoding="async">'
            return tag[:-1] + ' srcset="' + ', '.join(f'{v["url"]} {v["width"]}w' for v in variants) + '" sizes="' + sizes + '">'
        after = re.sub(r'<img\b[^>]*>', replace_img, before)
        # Keep visible image, structured data and social metadata in agreement.
        for old, variants in mapping.items():
            after = after.replace(old, variants[-1]['url'])
        if after != before:
            page.write_text(after)
            changed += 1
    (root / 'content/image-optimization.json').write_text(json.dumps({'format': 'WebP', 'quality': 85, 'records': records}, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'site': root.name, 'images': len(records), 'updated_pages': changed, 'original_bytes': sum(x['original_bytes'] for x in records), 'full_webp_bytes': sum(x['variants'][-1]['bytes'] for x in records), 'webp_640_bytes': sum(next(v['bytes'] for v in x['variants'] if v['width'] == 640) for x in records)}), flush=True)

if __name__ == '__main__':
    optimize()

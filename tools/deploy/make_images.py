#!/usr/bin/env python3
"""글별 이미지 2장 생성(글 형식 보강 v4): <dist>/images/enrich/<slug>-1.webp(제목 카드, 1200×675) · <slug>-2.webp(첫 표 요약 카드).
글 HTML(보강 완료본)에서 제목·키워드·표 제목·표 행을 읽어 텍스트 카드로 만든다. 결정적(같은 입력 → 같은 바이트) · 매번 다시 만든다(결정적이므로 R2 동기화 때 바뀐 파일만 올라감).
usage: make_images.py <sites.json> <domain> <dist root> <post files...>
"""
import hashlib, html, json, re, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONT_B = str(HERE / 'fonts' / 'NotoSansKR-Bold-subset.otf')
FONT_R = str(HERE / 'fonts' / 'NotoSansKR-Regular-subset.otf')
W, H = 1200, 675
PALETTES = [  # (배경 진한색, 배경 밝은색, 강조색) — 도메인 해시로 고정
    ('#17324d', '#1f4a70', '#f0b429'), ('#1d3b2f', '#2a5a45', '#ffd166'), ('#3a2a4d', '#54407a', '#ffb4a2'), ('#4a2c2a', '#6b3f3b', '#ffd6a5'),
    ('#1f3a3d', '#2c5c60', '#9ee6d1'), ('#2b2d42', '#3f4160', '#ef9f9f'), ('#2f3e1f', '#4b5f30', '#e9ff70'), ('#3b2f1f', '#5a4830', '#ffe8a3'),
    ('#1a2e4a', '#28466e', '#8ecae6'), ('#3d1f3b', '#5c2f58', '#f7c6ff'), ('#1f3d30', '#2e5a47', '#b8f2a8'), ('#3a3a1f', '#575732', '#fff2a8'),
]

def strip_tags(s): return html.unescape(re.sub(r'<[^>]+>', '', s)).strip()

def font(path, size):
    return ImageFont.truetype(path, size)

def wrap(draw, text, f, max_w):
    words = text.split(' '); lines = []; cur = ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if draw.textlength(t, font=f) <= max_w: cur = t
        else:
            if cur: lines.append(cur)
            # 한 어절이 너무 길면 글자 단위로 자름
            while draw.textlength(w, font=f) > max_w:
                k = len(w)
                while k > 1 and draw.textlength(w[:k], font=f) > max_w: k -= 1
                lines.append(w[:k]); w = w[k:]
            cur = w
    if cur: lines.append(cur)
    return lines

def hexrgb(h): return tuple(int(h[i:i+2], 16) for i in (1, 3, 5))

_GRAD = {}
def gradient(c1, c2):
    if (c1, c2) not in _GRAD:
        a, b = hexrgb(c1), hexrgb(c2)
        col = Image.new('RGB', (1, H))
        col.putdata([tuple(int(a[i] + (b[i] - a[i]) * y / (H - 1)) for i in range(3)) for y in range(H)])
        _GRAD[(c1, c2)] = col.resize((W, H))
    return _GRAD[(c1, c2)].copy()

def card1(title, kw, site, pal):
    img = gradient(pal[0], pal[1]); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 14, H], fill=pal[2])
    fk = font(FONT_B, 30); d.rounded_rectangle([70, 60, 70 + d.textlength(kw, font=fk) + 44, 112], radius=26, fill=pal[2])
    d.text((92, 69), kw, font=fk, fill=pal[0])
    size = 60
    while True:
        ft = font(FONT_B, size); lines = wrap(d, title, ft, W - 140)
        if len(lines) <= 3 or size <= 40: break
        size -= 4
    y = 170
    for ln in lines[:3]:
        d.text((70, y), ln, font=ft, fill='#ffffff'); y += int(size * 1.45)
    fs = font(FONT_R, 26); d.text((70, H - 80), site, font=fs, fill='#e8eef5')
    d.line([70, H - 96, 70 + min(400, d.textlength(site, font=fs)), H - 96], fill=pal[2], width=2)
    return img

def card2(cap, rows, kw, site, pal):
    img = Image.new('RGB', (W, H), '#f6f8fb'); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 96], fill=pal[0]); d.rectangle([0, 96, W, 102], fill=pal[2])
    d.text((70, 28), cap, font=font(FONT_B, 36), fill='#ffffff')
    y = 150; fh = font(FONT_B, 32); fb = font(FONT_R, 27)
    for lab, kp, cl in rows[:3]:
        d.rounded_rectangle([70, y, 70 + 150, y + 48], radius=10, fill=pal[1])
        d.text((70 + 75 - d.textlength(lab, font=fh) / 2, y + 4), lab, font=fh, fill='#ffffff')
        d.text((250, y + 6), kp, font=fh, fill=pal[0])
        yy = y + 58
        for ln in wrap(d, cl, fb, W - 320)[:2]:
            d.text((250, yy), ln, font=fb, fill='#333a44'); yy += 38
        y = yy + 30
    fs = font(FONT_R, 24); d.text((70, H - 64), f'{kw} · {site}', font=fs, fill='#5b6675')
    return img

def parse(s):
    t = re.search(r'<h1 class="enrich-title">(.*?)</h1>', s, re.S)
    title = strip_tags(t.group(1)) if t else strip_tags(re.search(r'<h1\b[^>]*>(.*?)</h1>', s, re.S).group(1))
    m = re.search(r'<p class="tbl-label"><em>(.*?)</em></p><div class="cmp-wrap"><table class="cmp">.*?<tbody>(.*?)</tbody>', s, re.S)
    cap, rows = '', []
    if m:
        cap = strip_tags(m.group(1))
        for tr in re.findall(r'<tr>(.*?)</tr>', m.group(2), re.S):
            tds = [strip_tags(x) for x in re.findall(r'<td>(.*?)</td>', tr, re.S)]
            if len(tds) >= 3: rows.append((tds[0], tds[1], tds[2]))
    return title, cap, rows

def main():
    cfg = json.load(open(sys.argv[1], encoding='utf-8')); domain = sys.argv[2]; dist = Path(sys.argv[3]); files = sys.argv[4:]
    me = cfg[domain]; kw = me['keyword']; site = me.get('site_name') or domain
    pal = PALETTES[int(hashlib.md5(domain.encode()).hexdigest(), 16) % len(PALETTES)]
    outdir = dist / 'images' / 'enrich'; outdir.mkdir(parents=True, exist_ok=True)
    made = skipped = 0
    for f in files:
        p = Path(f); s = p.read_text(encoding='utf-8')
        if '<!-- enrich:v4 -->' not in s: skipped += 1; continue
        slug = p.parent.name if p.name == 'index.html' else p.stem
        title, cap, rows = parse(s)
        o1, o2 = outdir / f'{slug}-1.webp', outdir / f'{slug}-2.webp'
        card1(title, kw, site, pal).save(o1, 'WEBP', quality=80, method=4)
        card2(cap or f'{kw} 확인 순서', rows or [('1단계', f'{kw} 확인', '상담 전에 현재 상태와 궁금한 점을 적어 둡니다')], kw, site, pal).save(o2, 'WEBP', quality=80, method=4)
        made += 1
    print(json.dumps({'domain': domain, 'images_made': made, 'skipped': skipped}, ensure_ascii=False))

if __name__ == '__main__': main()

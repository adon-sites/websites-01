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


# ---- 간단한 그림(실루엣 픽토그램, 그룹별 고정) — 글자만 있던 카드에 그림 1개 추가 (2026-11-18 사용자 "간단한 그림 하나 넣어주면 좋을듯")
def _pts(pts, k, ox, oy): return [(ox + x * k, oy + y * k) for x, y in pts]

def draw_icon(d, kind, ox, oy, size, fill):
    """(ox, oy) 왼쪽 위, size 한 변. 0~100 좌표계를 size 로 확대. 실루엣(채움)만 써서 겹침선이 없다."""
    k = size / 100.0
    R = lambda x0, y0, x1, y1, r: d.rounded_rectangle([ox + x0 * k, oy + y0 * k, ox + x1 * k, oy + y1 * k], radius=r * k, fill=fill)
    E = lambda x0, y0, x1, y1: d.ellipse([ox + x0 * k, oy + y0 * k, ox + x1 * k, oy + y1 * k], fill=fill)
    P = lambda pts: d.polygon(_pts(pts, k, ox, oy), fill=fill)
    if kind == 'dental':      # 치아: 둥근 크라운 + 뿌리 2개
        R(16, 14, 84, 64, 26); E(18, 8, 50, 34); E(50, 8, 82, 34)
        P([(20, 52), (46, 52), (40, 94), (28, 94)]); P([(54, 52), (80, 52), (72, 94), (60, 94)])
    elif kind == 'skin':      # 물방울 + 반짝임 2개
        E(24, 36, 76, 92); P([(50, 6), (25, 56), (75, 56)])
        P([(86, 14), (90, 24), (100, 28), (90, 32), (86, 42), (82, 32), (72, 28), (82, 24)])
        P([(8, 60), (11, 67), (18, 70), (11, 73), (8, 80), (5, 73), (-2, 70), (5, 67)])
    elif kind == 'gyn':       # 하트
        E(14, 18, 56, 60); E(44, 18, 86, 60); P([(16, 45), (84, 45), (50, 92)])
    elif kind == 'marketing': # 막대 3개 + 상승 화살표
        R(12, 62, 30, 92, 4); R(41, 46, 59, 92, 4); R(70, 30, 88, 92, 4)
        d.line(_pts([(14, 46), (48, 26), (72, 36), (92, 10)], k, ox, oy), fill=fill, width=max(2, int(5 * k)), joint='curve')
        P([(76, 6), (96, 6), (96, 26)])
    else:                     # 병원 일반: 둥근 십자
        R(38, 10, 62, 90, 8); R(10, 38, 90, 62, 8)

def icon_badge(img, kind, cx, cy, radius, pal, white=True):
    """부드러운 원 배경(강조색, 반투명) 위에 흰 실루엣. RGBA 레이어로 합성."""
    L = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    c = hexrgb(pal[2])
    d.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=c + (70,))
    d.ellipse([cx - radius * 0.78, cy - radius * 0.78, cx + radius * 0.78, cy + radius * 0.78], fill=c + (110,))
    sz = radius * 0.95; draw_icon(d, kind, cx - sz / 2, cy - sz / 2, sz, (255, 255, 255, 255) if white else hexrgb(pal[0]) + (255,))
    return Image.alpha_composite(img.convert('RGBA'), L).convert('RGB')

BRAND = {'marketing': 'AD-ON'}  # 그룹별 영문 문구(사용자 20:19 "AD-ON 문구 영어로도") — 마케팅 업체 카드에만
def brand_mark(d, kind, x_right, y, pal, dark_bg=True):
    t = BRAND.get(kind)
    if not t: return
    fb = font(FONT_B, 30); w = d.textlength(t, font=fb) + 8 * (len(t) - 1)
    x = x_right - w
    for ch in t:  # 자간 넓게
        d.text((x, y), ch, font=fb, fill=pal[2] if dark_bg else pal[0]); x += d.textlength(ch, font=fb) + 8

def card1(title, kw, site, pal, kind='other'):
    img = gradient(pal[0], pal[1]); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 14, H], fill=pal[2])
    fk = font(FONT_B, 30); d.rounded_rectangle([70, 60, 70 + d.textlength(kw, font=fk) + 44, 112], radius=26, fill=pal[2])
    d.text((92, 69), kw, font=fk, fill=pal[0])
    size = 60
    while True:
        ft = font(FONT_B, size); lines = wrap(d, title, ft, W - 480)
        if len(lines) <= 4 or size <= 40: break
        size -= 4
    y = 170
    for ln in lines[:4]:
        d.text((70, y), ln, font=ft, fill='#ffffff'); y += int(size * 1.45)
    fs = font(FONT_R, 26); d.text((70, H - 80), site, font=fs, fill='#e8eef5')
    d.line([70, H - 96, 70 + min(400, d.textlength(site, font=fs)), H - 96], fill=pal[2], width=2)
    img = icon_badge(img, kind, W - 250, H // 2 + 10, 165, pal); brand_mark(ImageDraw.Draw(img), kind, W - 70, H - 92, pal, True)
    return img

def card2(cap, rows, kw, site, pal, kind='other'):
    img = Image.new('RGB', (W, H), '#f6f8fb'); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 96], fill=pal[0]); d.rectangle([0, 96, W, 102], fill=pal[2])
    d.text((70, 28), cap, font=font(FONT_B, 36), fill='#ffffff')
    img = icon_badge(img, kind, W - 90, 48, 34, pal); d = ImageDraw.Draw(img)
    y = 150; fh = font(FONT_B, 32); fb = font(FONT_R, 27)
    for lab, kp, cl in rows[:3]:
        d.rounded_rectangle([70, y, 70 + 150, y + 48], radius=10, fill=pal[1])
        d.text((70 + 75 - d.textlength(lab, font=fh) / 2, y + 4), lab, font=fh, fill='#ffffff')
        d.text((250, y + 6), kp, font=fh, fill=pal[0])
        yy = y + 58
        for ln in wrap(d, cl, fb, W - 320)[:2]:
            d.text((250, yy), ln, font=fb, fill='#333a44'); yy += 38
        y = yy + 30
    img = icon_badge(img, kind, W - 170, H - 190, 120, pal, white=False); d = ImageDraw.Draw(img)
    fs = font(FONT_R, 24); d.text((70, H - 64), f'{kw} · {site}', font=fs, fill='#5b6675'); brand_mark(d, kind, W - 70, H - 70, pal, False)
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
    me = cfg[domain]; kw = me['keyword']; site = me.get('site_name') or domain; kind = me.get('group') or 'other'
    pal = PALETTES[int(hashlib.md5(domain.encode()).hexdigest(), 16) % len(PALETTES)]
    outdir = dist / 'images' / 'enrich'; outdir.mkdir(parents=True, exist_ok=True)
    made = skipped = 0
    for f in files:
        p = Path(f); s = p.read_text(encoding='utf-8')
        if '<!-- enrich:v4 -->' not in s: skipped += 1; continue
        slug = p.parent.name if p.name == 'index.html' else p.stem
        title, cap, rows = parse(s)
        o1, o2 = outdir / f'{slug}-1.webp', outdir / f'{slug}-2.webp'
        card1(title, kw, site, pal, kind).save(o1, 'WEBP', quality=80, method=4)
        card2(cap or f'{kw} 확인 순서', rows or [('1단계', f'{kw} 확인', '상담 전에 현재 상태와 궁금한 점을 적어 둡니다')], kw, site, pal, kind).save(o2, 'WEBP', quality=80, method=4)
        made += 1
    print(json.dumps({'domain': domain, 'images_made': made, 'skipped': skipped}, ensure_ascii=False))

if __name__ == '__main__': main()

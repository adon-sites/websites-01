#!/usr/bin/env python3
"""qa_cards.py — 새 글 구조(v5) 소제목 이미지의 틀 4종(2026-11-26 시범).
  para    답변 한 문단형   : 질문 + 그 절 본문의 앞 문장들(세로 줄)
  bullets 글머리표 3줄형   : 질문 + 그 절 본문의 문장 3개
  cards2  카드 2개형       : 질문 + 그 절 표의 앞 2줄(첫 칸 = 카드 제목, 둘째 칸 = 설명, 셋째 칸이 있으면 머리글 꼬리표와 함께 아래에)
  cards3  카드 3개형       : 질문 + 그 절 표의 앞 3줄
이미지에 넣는 글자는 전부 그 절의 본문(문단·표)에서 그대로 가져온다. 새로 쓰지 않고, 자리가 모자라면 문장 수를 줄이거나 끝을 …로 자른다.
어느 틀을 쓸지는 choose() 가 정한다(이유 문자열과 함께 돌려준다). 적용 대상은 photo_sets.json 의 qcards[도메인](from·limit)."""
import hashlib, re
from pathlib import Path
from PIL import Image, ImageDraw
CODE = hashlib.sha1(Path(__file__).read_bytes()).hexdigest()[:12]
W, H = 1200, 675

def sentences(text):
    return [x.strip() for x in re.split(r'(?<=[.?!])\s+', (text or '').strip()) if x.strip()]

def _fit(M, d, text, path, size, min_size, width, max_lines):
    """글꼴을 줄여 가며 max_lines 안에 넣는다. 끝내 넘치면 마지막 줄을 …로 자른다. returns (font, lines)"""
    while True:
        f = M.font(path, size); lines = M.wrap(d, text, f, width)
        if len(lines) <= max_lines or size <= min_size: break
        size -= 2
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while lines[-1] and d.textlength(lines[-1] + '…', font=f) > width: lines[-1] = lines[-1][:-1]
        lines[-1] = lines[-1].rstrip() + '…'
    return f, lines

NEG = ('피해야', '피할', '잘못', '오해', '틀린', '금지', '하지 말', '쓰지 말', '나쁜', '부적절', '위험한 표현', '과장')   # 첫 열이 부정 예시인 표 → 카드형 금지

def choose(sections):
    """sections: layout_v5.parse_v5()['sections'] → [(틀, 자료, 이유)] (절 순서대로 5개)."""
    out = []; n_table = 0; last_plain = None
    for s in sections:
        ps = [b[1] for b in s['blocks'] if b[0] == 'p']; tb = next((b for b in s['blocks'] if b[0] == 'table'), None)
        sents = [x for p in ps for x in sentences(p)]
        neg = bool(tb) and any(w in f'{tb[1] if len(tb) > 1 and isinstance(tb[1], str) else ""} {tb[2][0] if tb[2] else ""}' for w in NEG)
        if tb and len(tb[3]) >= 2 and len(tb[2]) >= 2 and not neg:
            n_table += 1; hd = list(tb[2])[:3]; rows = [{'cells': list(r[:3]), 'heads': hd[:len(r[:3])]} for r in tb[3]]
            short = all(len(r['cells'][0]) <= 14 and all(len(c) <= 40 for c in r['cells'][1:]) for r in rows[:3])
            if n_table % 2 == 0 and len(rows) >= 3 and short:
                out.append(('cards3', rows[:3], f'이 절에 표가 있고(글에서 두 번째 표) 앞 3줄의 칸 글자가 짧아 카드 3개에 들어감')); continue
            why = '이 절에 표가 있음(글에서 첫 번째 표)' if n_table % 2 == 1 else ('이 절에 표가 있으나 칸 글자가 길어 카드 3개에는 넘침' if len(rows) >= 3 else '이 절에 표가 있고 내용이 2줄')
            out.append(('cards2', rows[:2], why + ' → 표의 앞 2줄을 카드 2개로')); continue
        if neg: n_table += 1; negnote = '이 절의 표는 첫 열이 부정 예시(피해야 할 것·잘못된 예·오해)라 카드형을 쓰지 않음 — '
        else: negnote = ''
        if len(ps) >= 3:
            out.append(('bullets', [sentences(p)[0] for p in ps[:3]], negnote + '표가 없고 문단이 3개 → 문단마다 첫 문장을 한 줄씩')); last_plain = 'bullets'; continue
        if len(sents) >= 3 and last_plain == 'para':
            out.append(('bullets', sents[:3], negnote + '표가 없고 문단이 2개 — 앞 절이 한 문단형이라 겹치지 않게 본문의 앞 문장 3개를 한 줄씩')); last_plain = 'bullets'; continue
        out.append(('para', sents[:3], negnote + '표가 없고 문단이 2개 → 첫 문단의 앞 문장들을 한 문단으로')); last_plain = 'para'
    return out

MAT = Path(__file__).resolve().parent / 'qmat'
def assign(posts, cfg):
    """posts: [(slug, 진료과 번호|None, [틀 5개])] 날짜순 → {slug: [(배경, 인물) × 5]}. cfg = photo_sets.json 의 qmat.
    한 글의 5장은 서로 다른 배경 / 글 주제 전용 + 공용 재료만 / 마케팅 업무 글은 work + 공용(진료과 전용 공용 제외) / 바로 앞 글과 같은 배경·인물 조합은 피함."""
    hh = lambda *a: hashlib.md5('|'.join(a).encode()).hexdigest()
    out = {}; prev = set()
    for slug, dep, tpls in posts:
        if dep:
            own_b = list(cfg['bg'].get(dep, [])); com_b = list(cfg['bg']['common']); own_p = list(cfg['person'].get(dep, [])); com_p = list(cfg['person']['common'])
        else:
            own_b = list(cfg['bg']['work']); com_b = [x for x in cfg['bg']['common'] if x not in cfg.get('dept_only_bg', [])]; own_p = list(cfg['person']['work']); com_p = []
        own_b.sort(key=lambda k: hh(slug, k)); com_b.sort(key=lambda k: hh(slug, k))
        bgs = (own_b[:2] + com_b)[:5] if dep else (own_b[:2] + com_b[:3]); bgs.sort(key=lambda k: hh(slug, 'o', k))
        dark = [b for b in bgs if b in cfg.get('dark_bg', [])]
        if dark and 'cards3' in tpls:   # 어두운 배경은 카드 3개형 자리로
            i3 = tpls.index('cards3'); j = bgs.index(dark[0]); bgs[i3], bgs[j] = bgs[j], bgs[i3]
        ppl = sorted(own_p, key=lambda k: hh(slug, k)) + sorted(com_p, key=lambda k: hh(slug, k)); used = []; res = []
        for i, b in enumerate(bgs):
            cand = [p for p in ppl if p not in used and (b, p) not in prev] or [p for p in ppl if (b, p) not in prev] or ppl
            p = cand[0]; used.append(p); res.append((b, p))
        out[slug] = res; prev = set(res)
    return out

def _bg(M, pal, dark):
    img = M.gradient(pal[0], pal[1]).copy() if dark else Image.new('RGB', (W, H), '#eef1f6')
    d = ImageDraw.Draw(img)
    if not dark:
        d.rectangle([0, 0, W, 12], fill=pal[0]); d.ellipse([W - 330, -210, W + 150, 270], fill='#e3e8f0'); d.ellipse([-160, H - 190, 220, H + 190], fill='#e6eaf1')
    return img, d

def _head(M, d, n, kw, site, dark, pal):
    fg = '#ffffff' if dark else pal[0]; sub = '#e8eef5' if dark else '#5b6675'
    d.text((64, 44), site, font=M.font(M.FONT_B, 24), fill=fg)
    x = 64 + d.textlength(site, font=M.font(M.FONT_B, 24)) + 28
    lab = f'Q{n}'; fl = M.font(M.FONT_B, 22); wl = d.textlength(lab, font=fl)
    d.rounded_rectangle([x, 40, x + wl + 28, 76], radius=18, fill=pal[2] if dark else pal[0]); d.text((x + 14, 44), lab, font=fl, fill=pal[0] if dark else '#ffffff')
    d.text((x + wl + 44, 46), kw, font=M.font(M.FONT_R, 22), fill=sub)

def _person(img, person, right, bottom, height):
    im = Image.open(MAT / f'{person}.png').convert('RGBA'); w = round(im.width * height / im.height); im = im.resize((w, height), Image.LANCZOS)
    img.paste(im, (right - w, bottom - height), im); return w

def draw(tpl, n, question, data, kw, site, pal, bg=None, person=None, dark_bgs=()):
    """bg·person 이 있으면(3판) 배경 사진 위에 흰 패널을 올리고 인물을 패널 구석에 작게 넣는다. 어두운 배경 + 카드 3개형은 패널 없이 배경 위에 바로."""
    import make_images as M
    dark = tpl == 'cards3'; panel = False
    if bg:
        img = Image.open(MAT / f'{bg}.jpg').convert('RGB')
        if img.size != (W, H): img = img.resize((W, H), Image.LANCZOS)
        if dark and bg in dark_bgs:
            img = Image.blend(img, Image.new('RGB', (W, H), '#0b1020'), 0.35)
        else:
            dark = False; panel = True; ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(ov).rounded_rectangle([36, 30, W - 36, H - 30], radius=30, fill=(255, 255, 255, 236))
            img = Image.alpha_composite(img.convert('RGBA'), ov).convert('RGB')
        d = ImageDraw.Draw(img)
    else:
        img, d = _bg(M, pal, dark)
    cut = 190 if person else 0
    _head(M, d, n, kw, site, dark, pal)
    if tpl in ('para', 'bullets'):
        if not panel: d.rounded_rectangle([44, 100, W - 44, H - 40], radius=30, fill='#ffffff')
        if person: _person(img, person, W - 56, H - 30, 250)
        fq, ql = _fit(M, d, question, M.FONT_B, 46, 36, W - 200, 2); y = 140
        for ln in ql: d.text((84, y), ln, font=fq, fill=pal[0]); y += int(fq.size * 1.36)
        y += 26
        if tpl == 'para':
            text = ' '.join(data); room = (H - 76 - y); f, lines = _fit(M, d, text, M.FONT_R, 34, 26, W - 230 - cut, max(2, room // 50))
            while len(lines) * int(f.size * 1.55) > room and len(data) > 1: data = data[:-1]; f, lines = _fit(M, d, ' '.join(data), M.FONT_R, 34, 26, W - 230 - cut, max(2, room // 50))
            lh = int(f.size * 1.55); y += max(0, (room - len(lines) * lh) // 3); d.rounded_rectangle([84, y + 4, 91, y + len(lines) * lh - 6], radius=3, fill=pal[0])
            for ln in lines: d.text((114, y), ln, font=f, fill='#2b3440'); y += lh
        else:
            room = (H - 70 - y) // 3
            for s_ in data[:3]:
                f, lines = _fit(M, d, s_, M.FONT_R, 31, 24, W - 250 - cut, 2 if not cut else 3); lh = int(f.size * 1.42)
                d.ellipse([88, y + f.size // 2 - 5, 100, y + f.size // 2 + 7], fill=pal[0])
                yy = y
                for ln in lines: d.text((122, yy), ln, font=f, fill='#2b3440'); yy += lh
                y += max(room, len(lines) * lh + 8)
        return img
    # 카드형: 바탕 위에 질문, 그 아래 흰 카드 2~3개. 칸마다 [열 제목 꼬리표] → 칸 내용 순서(꼬리표가 먼저 보인다).
    fg = '#ffffff' if dark else pal[0]
    fq, ql = _fit(M, d, question, M.FONT_B, 46, 36, W - 128 - (150 if person else 0), 2); y = 108
    for ln in ql: d.text((64, y), ln, font=fq, fill=fg); y += int(fq.size * 1.36)
    k = len(data); gap = 26; cw = (W - 128 - gap * (k - 1)) // k; top = y + 22; room = H - 44 - top; inner = cw - 56
    def layout(sc):
        """글자 배율 sc 로 카드별 그리기 목록과 높이를 잰다 → ([[(종류, 글꼴, 줄들|글자, 줄높이)]], 가장 큰 높이, 잘림 여부)"""
        cards = []; cut = False
        for row in data:
            items = []; h = 30
            for ci, cell in enumerate(row['cells']):
                head = row['heads'][ci] if ci < len(row['heads']) else ''
                if head:
                    fh = M.font(M.FONT_B, max(18, int(20 * sc))); items.append(('chip', fh, head, fh.size + 14)); h += fh.size + 14 + 10
                base = (34 if k == 2 else 29) if ci == 0 else (29 if k == 2 else 25); size = int(base * sc); mx = 2 if ci == 0 else 3
                f = M.font(M.FONT_B if ci == 0 else M.FONT_R, size); lines = M.wrap(d, cell, f, inner)
                if len(lines) > mx:
                    cut = True; lines = lines[:mx]
                    while lines[-1] and d.textlength(lines[-1] + '…', font=f) > inner: lines[-1] = lines[-1][:-1]
                    lines[-1] = lines[-1].rstrip() + '…'
                lh = int(size * 1.42); items.append(('t0' if ci == 0 else 't', f, lines, lh)); h += len(lines) * lh + (20 if ci < len(row['cells']) - 1 else 0)
            cards.append((items, h + 26))
        return cards, max(h_ for _i, h_ in cards), cut
    best = None
    for sc in (1.5, 1.4, 1.3, 1.2, 1.1, 1.0, 0.92, 0.85):   # 들어가는 한 가장 큰 글자. 잘림 없는 배율을 먼저, 없으면 잘리더라도 들어가는 가장 큰 배율
        cards, hh, cut = layout(sc)
        if hh > room: continue
        if not cut: best = (cards, hh); break
        if best is None: best = (cards, hh)
    if best is None: best = layout(0.85)[:2]
    cards, hh = best; hh = min(hh, room); top += max(0, (room - hh) // 2); bot = top + hh
    if person: _person(img, person, W - 70, top + 6, max(110, min(190, top - 30)))
    cfill = '#eef2f8' if panel else '#ffffff'
    for i, (items, _h) in enumerate(cards):
        x0 = 64 + i * (cw + gap); d.rounded_rectangle([x0, top, x0 + cw, bot], radius=26, fill=cfill); yy = top + 30
        for kind, f, val, lh in items:
            if kind == 'chip':
                wh = d.textlength(val, font=f); d.rounded_rectangle([x0 + 28, yy, x0 + 28 + wh + 24, yy + lh], radius=lh // 2, fill=pal[0] if not dark else '#eef1f6'); d.text((x0 + 40, yy + 5), val, font=f, fill='#ffffff' if not dark else pal[0]); yy += lh + 10
            else:
                for ln in val: d.text((x0 + 28, yy), ln, font=f, fill=pal[0] if kind == 't0' else '#2b3440'); yy += lh
                yy += 20
    return img

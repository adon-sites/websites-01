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

def choose(sections):
    """sections: layout_v5.parse_v5()['sections'] → [(틀, 자료, 이유)] (절 순서대로 5개)."""
    out = []; n_table = 0; last_plain = None
    for s in sections:
        ps = [b[1] for b in s['blocks'] if b[0] == 'p']; tb = next((b for b in s['blocks'] if b[0] == 'table'), None)
        sents = [x for p in ps for x in sentences(p)]
        if tb and len(tb[3]) >= 2 and len(tb[2]) >= 2:
            n_table += 1; hd = list(tb[2]); rows = [[r[0], r[1], r[2], hd[2]] if len(r) > 2 else [r[0], r[1]] for r in tb[3]]
            short = all(len(r[0]) <= 14 and len(r[1]) <= 40 and (len(r) < 3 or len(r[2]) <= 40) for r in rows[:3])
            if n_table % 2 == 0 and len(rows) >= 3 and short:
                out.append(('cards3', rows[:3], f'이 절에 표가 있고(글에서 두 번째 표) 앞 3줄의 칸 글자가 짧아 카드 3개에 들어감')); continue
            why = '이 절에 표가 있음(글에서 첫 번째 표)' if n_table % 2 == 1 else ('이 절에 표가 있으나 칸 글자가 길어 카드 3개에는 넘침' if len(rows) >= 3 else '이 절에 표가 있고 내용이 2줄')
            out.append(('cards2', rows[:2], why + ' → 표의 앞 2줄을 카드 2개로')); continue
        if len(ps) >= 3:
            out.append(('bullets', [sentences(p)[0] for p in ps[:3]], '표가 없고 문단이 3개 → 문단마다 첫 문장을 한 줄씩')); last_plain = 'bullets'; continue
        if len(sents) >= 3 and last_plain == 'para':
            out.append(('bullets', sents[:3], '표가 없고 문단이 2개 — 앞 절이 한 문단형이라 겹치지 않게 본문의 앞 문장 3개를 한 줄씩')); last_plain = 'bullets'; continue
        out.append(('para', sents[:3], '표가 없고 문단이 2개 → 첫 문단의 앞 문장들을 한 문단으로')); last_plain = 'para'
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

def draw(tpl, n, question, data, kw, site, pal):
    import make_images as M
    dark = tpl == 'cards3'; img, d = _bg(M, pal, dark)
    _head(M, d, n, kw, site, dark, pal)
    if tpl in ('para', 'bullets'):
        d.rounded_rectangle([44, 100, W - 44, H - 40], radius=30, fill='#ffffff')
        fq, ql = _fit(M, d, question, M.FONT_B, 46, 36, W - 200, 2); y = 140
        for ln in ql: d.text((84, y), ln, font=fq, fill=pal[0]); y += int(fq.size * 1.36)
        y += 26
        if tpl == 'para':
            text = ' '.join(data); room = (H - 76 - y); f, lines = _fit(M, d, text, M.FONT_R, 34, 26, W - 230, max(2, room // 50))
            while len(lines) * int(f.size * 1.55) > room and len(data) > 1: data = data[:-1]; f, lines = _fit(M, d, ' '.join(data), M.FONT_R, 34, 26, W - 230, max(2, room // 50))
            lh = int(f.size * 1.55); y += max(0, (room - len(lines) * lh) // 3); d.rounded_rectangle([84, y + 4, 91, y + len(lines) * lh - 6], radius=3, fill=pal[0])
            for ln in lines: d.text((114, y), ln, font=f, fill='#2b3440'); y += lh
        else:
            room = (H - 70 - y) // 3
            for s_ in data[:3]:
                f, lines = _fit(M, d, s_, M.FONT_R, 31, 24, W - 250, 2); lh = int(f.size * 1.42)
                d.ellipse([88, y + f.size // 2 - 5, 100, y + f.size // 2 + 7], fill=pal[0])
                yy = y
                for ln in lines: d.text((122, yy), ln, font=f, fill='#2b3440'); yy += lh
                y += max(room, len(lines) * lh + 8)
        return img
    # 카드형: 바탕 위에 질문, 그 아래 흰 카드 2~3개
    fg = '#ffffff' if dark else pal[0]
    fq, ql = _fit(M, d, question, M.FONT_B, 46, 36, W - 128, 2); y = 108
    for ln in ql: d.text((64, y), ln, font=fq, fill=fg); y += int(fq.size * 1.36)
    k = len(data); gap = 26; cw = (W - 128 - gap * (k - 1)) // k; top = y + 26; bot = H - 52
    for i, row in enumerate(data):
        t, b = row[0], row[1]; c3 = row[2] if len(row) > 3 else ''; h3 = row[3] if len(row) > 3 else ''
        x0 = 64 + i * (cw + gap); d.rounded_rectangle([x0, top, x0 + cw, bot], radius=26, fill='#ffffff')
        ft, tl = _fit(M, d, t, M.FONT_B, 36 if k == 2 else 31, 24, cw - 56, 2); yy = top + 34
        for ln in tl: d.text((x0 + 28, yy), ln, font=ft, fill=pal[0]); yy += int(ft.size * 1.35)
        d.line([x0 + 28, yy + 8, x0 + 28 + 56, yy + 8], fill=pal[2] if pal[2] != '#ffffff' else pal[1], width=4); yy += 30
        fb, bl = _fit(M, d, b, M.FONT_R, 30 if k == 2 else 26, 21, cw - 56, 3 if c3 else max(2, (bot - 24 - yy) // 40))
        for ln in bl: d.text((x0 + 28, yy), ln, font=fb, fill='#2b3440'); yy += int(fb.size * 1.5)
        if c3 and yy + 90 <= bot:   # 표의 셋째 칸: 머리글을 작은 꼬리표로, 그 아래 칸 내용
            yy += 14; fh = M.font(M.FONT_B, 20); wh = d.textlength(h3, font=fh)
            if h3: d.rounded_rectangle([x0 + 28, yy, x0 + 28 + wh + 24, yy + 32], radius=14, fill='#eef1f6'); d.text((x0 + 40, yy + 4), h3, font=fh, fill=pal[0]); yy += 44
            fc, cl = _fit(M, d, c3, M.FONT_R, 26 if k == 2 else 23, 20, cw - 56, max(1, (bot - 20 - yy) // 36))
            for ln in cl: d.text((x0 + 28, yy), ln, font=fc, fill='#4a5563'); yy += int(fc.size * 1.5)
    return img
